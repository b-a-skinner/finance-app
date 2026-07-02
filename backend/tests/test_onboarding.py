"""Tests for onboarding endpoints and completion_status in summary."""
import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _register(client: TestClient, email: str = "user@example.com") -> dict:
    r = client.post("/api/auth/register", json={"email": email, "password": "pass123"})
    assert r.status_code == 201
    return r.json()


def _token(client: TestClient, email: str = "user@example.com") -> str:
    r = client.post(
        "/api/auth/login",
        data={"username": email, "password": "pass123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 200
    return r.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _setup_user(client: TestClient, email: str = "user@example.com") -> str:
    _register(client, email)
    return _token(client, email)


# ---------------------------------------------------------------------------
# GET /api/profile/onboarding — defaults
# ---------------------------------------------------------------------------

class TestGetOnboardingDefaults:
    def test_defaults_for_new_user(self, client):
        tok = _setup_user(client)
        r = client.get("/api/profile/onboarding", headers=_auth(tok))
        assert r.status_code == 200
        data = r.json()
        assert data["onboarding_completed"] is False
        assert data["onboarding_dismiss_count"] == 0
        assert data["financial_goals"] is None
        assert data["current_onboarding_step"] == 0

    def test_requires_auth(self, client):
        r = client.get("/api/profile/onboarding")
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /api/profile/onboarding — update fields
# ---------------------------------------------------------------------------

class TestPatchOnboarding:
    def test_set_completed(self, client):
        tok = _setup_user(client)
        r = client.patch(
            "/api/profile/onboarding",
            json={"onboarding_completed": True},
            headers=_auth(tok),
        )
        assert r.status_code == 200
        assert r.json()["onboarding_completed"] is True
        # Other fields unchanged
        assert r.json()["onboarding_dismiss_count"] == 0

    def test_increment_dismiss_count(self, client):
        tok = _setup_user(client)
        client.patch(
            "/api/profile/onboarding",
            json={"onboarding_dismiss_count": 1},
            headers=_auth(tok),
        )
        r = client.patch(
            "/api/profile/onboarding",
            json={"onboarding_dismiss_count": 2},
            headers=_auth(tok),
        )
        assert r.status_code == 200
        assert r.json()["onboarding_dismiss_count"] == 2

    def test_set_financial_goals(self, client):
        tok = _setup_user(client)
        r = client.patch(
            "/api/profile/onboarding",
            json={"financial_goals": "Save for a house deposit"},
            headers=_auth(tok),
        )
        assert r.status_code == 200
        assert r.json()["financial_goals"] == "Save for a house deposit"

    def test_set_current_step(self, client):
        tok = _setup_user(client)
        r = client.patch(
            "/api/profile/onboarding",
            json={"current_onboarding_step": 3},
            headers=_auth(tok),
        )
        assert r.status_code == 200
        assert r.json()["current_onboarding_step"] == 3

    def test_partial_update_does_not_null_other_fields(self, client):
        tok = _setup_user(client)
        # Set all fields
        client.patch(
            "/api/profile/onboarding",
            json={
                "financial_goals": "Buy a house",
                "current_onboarding_step": 2,
                "onboarding_dismiss_count": 1,
            },
            headers=_auth(tok),
        )
        # Partial update — only mark complete
        r = client.patch(
            "/api/profile/onboarding",
            json={"onboarding_completed": True},
            headers=_auth(tok),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["onboarding_completed"] is True
        assert data["financial_goals"] == "Buy a house"
        assert data["current_onboarding_step"] == 2
        assert data["onboarding_dismiss_count"] == 1

    def test_persists_across_requests(self, client):
        tok = _setup_user(client)
        client.patch(
            "/api/profile/onboarding",
            json={"financial_goals": "Retire early", "current_onboarding_step": 4},
            headers=_auth(tok),
        )
        r = client.get("/api/profile/onboarding", headers=_auth(tok))
        assert r.status_code == 200
        data = r.json()
        assert data["financial_goals"] == "Retire early"
        assert data["current_onboarding_step"] == 4

    def test_requires_auth(self, client):
        r = client.patch("/api/profile/onboarding", json={"onboarding_completed": True})
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Wizard reappearance logic (dismiss_count)
# ---------------------------------------------------------------------------

class TestDismissCountLogic:
    """
    Wizard shows when: !onboarding_completed && dismiss_count < 2
    Frontend enforces this; backend just stores the values accurately.
    """

    def test_dismiss_count_starts_at_zero(self, client):
        tok = _setup_user(client)
        r = client.get("/api/profile/onboarding", headers=_auth(tok))
        assert r.json()["onboarding_dismiss_count"] == 0

    def test_dismiss_count_can_reach_two(self, client):
        tok = _setup_user(client)
        client.patch("/api/profile/onboarding", json={"onboarding_dismiss_count": 2}, headers=_auth(tok))
        r = client.get("/api/profile/onboarding", headers=_auth(tok))
        assert r.json()["onboarding_dismiss_count"] == 2

    def test_completed_flag_independent_of_dismiss_count(self, client):
        tok = _setup_user(client)
        client.patch(
            "/api/profile/onboarding",
            json={"onboarding_dismiss_count": 2, "onboarding_completed": True},
            headers=_auth(tok),
        )
        r = client.get("/api/profile/onboarding", headers=_auth(tok))
        data = r.json()
        assert data["onboarding_completed"] is True
        assert data["onboarding_dismiss_count"] == 2


# ---------------------------------------------------------------------------
# User isolation
# ---------------------------------------------------------------------------

class TestOnboardingIsolation:
    def test_users_cannot_read_each_other_onboarding(self, client):
        tok_a = _setup_user(client, "a@example.com")
        tok_b = _setup_user(client, "b@example.com")
        client.patch(
            "/api/profile/onboarding",
            json={"financial_goals": "Secret goal", "onboarding_completed": True},
            headers=_auth(tok_a),
        )
        r = client.get("/api/profile/onboarding", headers=_auth(tok_b))
        data = r.json()
        assert data["financial_goals"] is None
        assert data["onboarding_completed"] is False


# ---------------------------------------------------------------------------
# completion_status in GET /api/finance/summary
# ---------------------------------------------------------------------------

@pytest.fixture
def seeded_client(client, db):
    """Client with a registered user and tax config seeded."""
    from app.models import TaxYearConfig
    from app.services.finance_summary import CURRENT_TAX_YEAR
    db.add(TaxYearConfig(
        tax_year=CURRENT_TAX_YEAR,
        personal_allowance=12570, basic_rate_threshold=50270, basic_rate_pct=20,
        higher_rate_threshold=125140, higher_rate_pct=40, additional_rate_pct=45,
        ni_primary_threshold=12584, ni_upper_threshold=50284,
        ni_main_rate_pct=8, ni_upper_rate_pct=2,
        pension_qualifying_lower=6240, pension_qualifying_upper=50270,
        pension_min_total_pct=8, pension_min_employer_pct=3,
    ))
    db.commit()
    return client


class TestCompletionStatus:
    def test_all_false_for_new_user(self, seeded_client):
        tok = _setup_user(seeded_client)
        # Seed income so summary doesn't 500 with no tax config issues
        seeded_client.post(
            "/api/income",
            json={"label": "Job", "gross_annual_salary": 40000, "pay_frequency": "annual"},
            headers=_auth(tok),
        )
        r = seeded_client.get("/api/finance/summary", headers=_auth(tok))
        assert r.status_code == 200
        cs = r.json()["completion_status"]
        assert cs["income"] is True   # we just added one
        assert cs["expenses"] is False
        assert cs["debts"] is False
        assert cs["savings"] is False
        assert cs["pension"] is False
        assert cs["assets"] is False

    def test_income_true_after_adding_source(self, seeded_client):
        tok = _setup_user(seeded_client)
        seeded_client.post(
            "/api/income",
            json={"label": "Job", "gross_annual_salary": 50000, "pay_frequency": "annual"},
            headers=_auth(tok),
        )
        r = seeded_client.get("/api/finance/summary", headers=_auth(tok))
        assert r.json()["completion_status"]["income"] is True

    def test_expenses_true_after_adding_expense(self, seeded_client):
        tok = _setup_user(seeded_client)
        seeded_client.post(
            "/api/income",
            json={"label": "Job", "gross_annual_salary": 40000, "pay_frequency": "annual"},
            headers=_auth(tok),
        )
        seeded_client.post(
            "/api/expenses",
            json={"category": "Rent", "amount": 1000, "frequency": "monthly", "is_fixed": True},
            headers=_auth(tok),
        )
        r = seeded_client.get("/api/finance/summary", headers=_auth(tok))
        assert r.json()["completion_status"]["expenses"] is True

    def test_savings_true_after_adding_goal(self, seeded_client):
        tok = _setup_user(seeded_client)
        seeded_client.post(
            "/api/income",
            json={"label": "Job", "gross_annual_salary": 40000, "pay_frequency": "annual"},
            headers=_auth(tok),
        )
        seeded_client.post(
            "/api/savings",
            json={"name": "Emergency fund", "current_balance": 2000, "target_amount": 10000, "monthly_contribution": 200},
            headers=_auth(tok),
        )
        r = seeded_client.get("/api/finance/summary", headers=_auth(tok))
        assert r.json()["completion_status"]["savings"] is True

    def test_completion_status_isolated_between_users(self, seeded_client):
        tok_a = _setup_user(seeded_client, "a@example.com")
        tok_b = _setup_user(seeded_client, "b@example.com")
        seeded_client.post(
            "/api/income",
            json={"label": "Job", "gross_annual_salary": 40000, "pay_frequency": "annual"},
            headers=_auth(tok_a),
        )
        # user B has no income
        seeded_client.post(
            "/api/income",
            json={"label": "Job", "gross_annual_salary": 30000, "pay_frequency": "annual"},
            headers=_auth(tok_b),
        )
        r_a = seeded_client.get("/api/finance/summary", headers=_auth(tok_a))
        r_b = seeded_client.get("/api/finance/summary", headers=_auth(tok_b))
        # Both have income; A shouldn't see B's expenses
        assert r_a.json()["completion_status"]["expenses"] is False
        assert r_b.json()["completion_status"]["expenses"] is False
