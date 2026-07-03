"""Tests for GET /api/debts/{id}/repayment-projection."""
import pytest
from fastapi.testclient import TestClient

REGISTER = "/api/auth/register"
LOGIN = "/api/auth/login"
DEBTS = "/api/debts"


def _auth(client: TestClient, email: str = "user@example.com") -> dict:
    client.post(REGISTER, json={"email": email, "password": "pass123!"})
    token = client.post(
        LOGIN,
        data={"username": email, "password": "pass123!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_debt(client, headers, **overrides) -> dict:
    defaults = {
        "debt_type": "credit_card",
        "balance": 5000.0,
        "interest_rate": 20.0,
        "min_payment": 150.0,
    }
    r = client.post(DEBTS, json={**defaults, **overrides}, headers=headers)
    assert r.status_code == 201
    return r.json()


def _projection(client, headers, debt_id: int):
    return client.get(f"{DEBTS}/{debt_id}/repayment-projection", headers=headers)


# ---------------------------------------------------------------------------
# Amortisation accuracy
# ---------------------------------------------------------------------------

class TestAmortisationAccuracy:
    def test_known_example_months(self, client):
        # £1,200 at 12% APR (1%/month), £100/month.
        # Simulation: 13 months to clear.
        h = _auth(client)
        d = _create_debt(client, h, balance=1200.0, interest_rate=12.0, min_payment=100.0)
        r = _projection(client, h, d["id"])
        assert r.status_code == 200
        assert r.json()["months_to_payoff"] == 13

    def test_known_example_interest(self, client):
        # Same example: total interest should be ~£84.78
        h = _auth(client)
        d = _create_debt(client, h, balance=1200.0, interest_rate=12.0, min_payment=100.0)
        r = _projection(client, h, d["id"])
        assert r.status_code == 200
        total = r.json()["total_interest_to_pay"]
        assert abs(total - 84.78) < 1.0  # within £1

    def test_payment_covers_interest_flag_true(self, client):
        h = _auth(client)
        d = _create_debt(client, h, balance=1200.0, interest_rate=12.0, min_payment=100.0)
        r = _projection(client, h, d["id"])
        assert r.json()["payment_covers_interest"] is True

    def test_projected_date_is_month_yyyy(self, client):
        h = _auth(client)
        d = _create_debt(client, h, balance=1200.0, interest_rate=12.0, min_payment=100.0)
        data = _projection(client, h, d["id"]).json()
        parts = data["projected_payoff_date"].split()
        assert len(parts) == 2
        assert parts[0].isalpha()
        assert parts[1].isdigit()


# ---------------------------------------------------------------------------
# Zero interest
# ---------------------------------------------------------------------------

class TestZeroInterest:
    def test_zero_interest_simple_division(self, client):
        # £1,000 at 0% APR, £200/month → exactly 5 months
        h = _auth(client)
        d = _create_debt(client, h, balance=1000.0, interest_rate=0.0, min_payment=200.0)
        r = _projection(client, h, d["id"])
        assert r.status_code == 200
        data = r.json()
        assert data["months_to_payoff"] == 5
        assert data["total_interest_to_pay"] == 0.0

    def test_zero_interest_rounds_up(self, client):
        # £1,000 at 0% APR, £300/month → ceil(1000/300) = 4 months
        h = _auth(client)
        d = _create_debt(client, h, balance=1000.0, interest_rate=0.0, min_payment=300.0)
        r = _projection(client, h, d["id"])
        assert r.json()["months_to_payoff"] == 4

    def test_zero_interest_no_interest_in_response(self, client):
        h = _auth(client)
        d = _create_debt(client, h, balance=500.0, interest_rate=0.0, min_payment=100.0)
        assert _projection(client, h, d["id"]).json()["total_interest_to_pay"] == 0.0


# ---------------------------------------------------------------------------
# Payment doesn't cover interest
# ---------------------------------------------------------------------------

class TestPaymentDoesNotCoverInterest:
    def test_warning_flag_set(self, client):
        # £10,000 at 24% APR → monthly interest = 200; payment = 100 < 200
        h = _auth(client)
        d = _create_debt(client, h, balance=10000.0, interest_rate=24.0, min_payment=100.0)
        r = _projection(client, h, d["id"])
        assert r.status_code == 200
        data = r.json()
        assert data["payment_covers_interest"] is False
        assert data["months_to_payoff"] is None
        assert data["total_interest_to_pay"] is None

    def test_exactly_covers_interest_is_not_flagged(self, client):
        # £12,000 at 12% APR → monthly interest = 120; payment = 121 (just above)
        h = _auth(client)
        d = _create_debt(client, h, balance=12000.0, interest_rate=12.0, min_payment=121.0)
        r = _projection(client, h, d["id"])
        assert r.json()["payment_covers_interest"] is True


# ---------------------------------------------------------------------------
# Balance already zero
# ---------------------------------------------------------------------------

class TestZeroBalance:
    def test_zero_balance_returns_zero_months(self, client):
        h = _auth(client)
        d = _create_debt(client, h, balance=0.0, interest_rate=15.0, min_payment=50.0)
        r = _projection(client, h, d["id"])
        assert r.status_code == 200
        data = r.json()
        assert data["months_to_payoff"] == 0
        assert data["total_interest_to_pay"] == 0.0


# ---------------------------------------------------------------------------
# No minimum payment
# ---------------------------------------------------------------------------

class TestNoMinPayment:
    def test_zero_payment_returns_null_months(self, client):
        h = _auth(client)
        d = _create_debt(client, h, balance=5000.0, interest_rate=10.0, min_payment=0.0)
        r = _projection(client, h, d["id"])
        assert r.status_code == 200
        data = r.json()
        assert data["months_to_payoff"] is None
        assert data["total_interest_to_pay"] is None


# ---------------------------------------------------------------------------
# Student loan excluded
# ---------------------------------------------------------------------------

class TestStudentLoanExcluded:
    def test_student_loan_returns_400(self, client, db):
        from app.models.config import StudentLoanPlanConfig
        plan = StudentLoanPlanConfig(
            plan_name="Plan 2", tax_year="2026/27", threshold=27295.0,
            repayment_rate_pct=9.0, write_off_years=30,
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)

        h = _auth(client)
        d = _create_debt(
            client, h,
            debt_type="student_loan",
            balance=30000.0, interest_rate=6.5, min_payment=0.0,
            student_loan_plan_id=plan.id, graduation_year=2019,
        )
        r = client.get(f"{DEBTS}/{d['id']}/repayment-projection", headers=h)
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# is_student_loan field
# ---------------------------------------------------------------------------

class TestIsStudentLoanField:
    def test_is_student_loan_false_for_non_loan(self, client):
        h = _auth(client)
        d = _create_debt(client, h)
        r = _projection(client, h, d["id"])
        assert r.json()["is_student_loan"] is False


# ---------------------------------------------------------------------------
# Auth and ownership
# ---------------------------------------------------------------------------

class TestAuth:
    def test_unauthenticated_returns_401(self, client):
        r = client.get(f"{DEBTS}/1/repayment-projection")
        assert r.status_code == 401

    def test_other_users_debt_returns_404(self, client):
        h_a = _auth(client, "a@example.com")
        h_b = _auth(client, "b@example.com")
        d = _create_debt(client, h_a)
        r = client.get(f"{DEBTS}/{d['id']}/repayment-projection", headers=h_b)
        assert r.status_code == 404

    def test_nonexistent_debt_returns_404(self, client):
        h = _auth(client)
        r = client.get(f"{DEBTS}/9999/repayment-projection", headers=h)
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Debt types (mortgage, other)
# ---------------------------------------------------------------------------

class TestDebtTypes:
    def test_mortgage_projection_works(self, client):
        h = _auth(client)
        d = _create_debt(client, h, debt_type="mortgage", balance=200000.0,
                         interest_rate=5.0, min_payment=1200.0)
        r = _projection(client, h, d["id"])
        assert r.status_code == 200
        assert r.json()["months_to_payoff"] is not None

    def test_other_debt_projection_works(self, client):
        h = _auth(client)
        d = _create_debt(client, h, debt_type="other", balance=3000.0,
                         interest_rate=8.0, min_payment=200.0)
        r = _projection(client, h, d["id"])
        assert r.status_code == 200
        assert r.json()["months_to_payoff"] is not None
