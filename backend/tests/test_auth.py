"""
Auth endpoint tests.
All tests use an in-memory SQLite DB (wired in conftest.py) — no real DB needed.
"""
from app.models import TaxYearConfig

REGISTER = "/api/auth/register"
LOGIN = "/api/auth/login"
SUMMARY = "/api/finance/summary"

_ALICE = {"email": "alice@example.com", "password": "s3cur3!"}


def _register(client, credentials=_ALICE):
    return client.post(REGISTER, json=credentials)


def _login(client, credentials=_ALICE):
    return client.post(LOGIN, data={"username": credentials["email"], "password": credentials["password"]})


def _auth_header(client, credentials=_ALICE):
    token = _login(client, credentials).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _seed_tax_config(db):
    db.add(TaxYearConfig(
        tax_year="2026/27",
        personal_allowance=12570, basic_rate_threshold=50270, basic_rate_pct=20,
        higher_rate_threshold=125140, higher_rate_pct=40, additional_rate_pct=45,
        ni_primary_threshold=12584, ni_upper_threshold=50284,
        ni_main_rate_pct=8, ni_upper_rate_pct=2,
        pension_qualifying_lower=6240, pension_qualifying_upper=50270,
        pension_min_total_pct=8, pension_min_employer_pct=3,
    ))
    db.commit()


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class TestRegister:
    def test_success(self, client):
        r = _register(client)
        assert r.status_code == 201
        body = r.json()
        assert body["message"] == "User created successfully"
        assert "user_id" in body
        assert "password" not in body          # hash must never be exposed

    def test_duplicate_email_rejected(self, client):
        _register(client)
        r = _register(client)                  # same email again
        assert r.status_code == 400
        assert "already registered" in r.json()["detail"]


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

class TestLogin:
    def test_correct_credentials_return_token(self, client):
        _register(client)
        r = _login(client)
        assert r.status_code == 200
        body = r.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    def test_wrong_password_rejected(self, client):
        _register(client)
        r = client.post(LOGIN, data={"username": _ALICE["email"], "password": "wrong!"})
        assert r.status_code == 401

    def test_unknown_email_rejected(self, client):
        r = client.post(LOGIN, data={"username": "nobody@example.com", "password": "anything"})
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Finance summary — auth enforcement
# ---------------------------------------------------------------------------

class TestFinanceSummaryAuth:
    def test_no_token_rejected(self, client):
        r = client.get(SUMMARY)
        assert r.status_code == 401

    def test_valid_token_accepted(self, client, db):
        _seed_tax_config(db)
        _register(client)
        r = client.get(SUMMARY, headers=_auth_header(client))
        assert r.status_code == 200
        body = r.json()
        assert body["tax_year"] == "2026/27"
        assert body["take_home"]["gross_annual"] == 0.0   # no income sources added yet
        # New balance / net worth fields are present and zero for a fresh user
        assert body["total_savings_balance"] == 0.0
        assert body["pension_pot_balance"] == 0.0
        assert body["total_debt_balance"] == 0.0
        assert body["net_worth"] == 0.0


# ---------------------------------------------------------------------------
# Finance summary — net worth calculation
# ---------------------------------------------------------------------------

class TestNetWorthSummary:
    def test_new_user_net_worth_is_zero(self, client, db):
        _seed_tax_config(db)
        _register(client)
        body = client.get(SUMMARY, headers=_auth_header(client)).json()
        assert body["total_savings_balance"] == 0.0
        assert body["pension_pot_balance"] == 0.0
        assert body["total_debt_balance"] == 0.0
        assert body["net_worth"] == 0.0

    def test_net_worth_computed_from_balances(self, client, db):
        _seed_tax_config(db)
        _register(client)
        headers = _auth_header(client)

        # Savings: £5,000
        client.post("/api/savings", json={
            "name": "Emergency fund",
            "current_balance": 5000.0,
            "target_amount": 10000.0,
            "monthly_contribution": 200.0,
        }, headers=headers)

        # Pension: £15,000
        client.post("/api/pension", json={
            "current_balance": 15000.0,
            "employee_contribution_pct": 5.0,
            "employer_contribution_pct": 3.0,
        }, headers=headers)

        # Debt: £8,000 credit card (included in total_debt_balance)
        client.post("/api/debts", json={
            "debt_type": "credit_card",
            "balance": 8000.0,
            "interest_rate": 22.0,
            "min_payment": 150.0,
            "student_loan_plan_id": None,
        }, headers=headers)

        body = client.get(SUMMARY, headers=headers).json()
        assert body["total_savings_balance"] == 5000.0
        assert body["pension_pot_balance"] == 15000.0
        assert body["total_debt_balance"] == 8000.0
        assert body["net_worth"] == 12000.0   # 5000 + 15000 - 8000

    def test_student_loan_included_in_total_debt_balance(self, client, db):
        _seed_tax_config(db)
        # Need a student loan plan for the FK
        from app.models.config import StudentLoanPlanConfig
        db.add(StudentLoanPlanConfig(
            plan_name="Plan 2", tax_year="2026/27", threshold=29385, repayment_rate_pct=9
        ))
        db.commit()

        _register(client)
        headers = _auth_header(client)

        # Student loan debt — balance should count toward total_debt_balance
        plan_id = db.query(StudentLoanPlanConfig).first().id
        client.post("/api/debts", json={
            "debt_type": "student_loan",
            "balance": 45000.0,
            "interest_rate": 7.3,
            "min_payment": 0.0,
            "student_loan_plan_id": plan_id,
        }, headers=headers)

        body = client.get(SUMMARY, headers=headers).json()
        assert body["total_debt_balance"] == 45000.0
        assert body["net_worth"] == -45000.0  # no savings or pension to offset

    def test_multiple_pension_pots_summed(self, client, db):
        _seed_tax_config(db)
        _register(client)
        headers = _auth_header(client)

        client.post("/api/pension", json={
            "current_balance": 10000.0,
            "employee_contribution_pct": 5.0,
            "employer_contribution_pct": 3.0,
        }, headers=headers)
        client.post("/api/pension", json={
            "current_balance": 6000.0,
            "employee_contribution_pct": 0.0,
            "employer_contribution_pct": 0.0,
        }, headers=headers)

        body = client.get(SUMMARY, headers=headers).json()
        assert body["pension_pot_balance"] == 16000.0
        assert body["net_worth"] == 16000.0
