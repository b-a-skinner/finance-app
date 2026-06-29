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
        assert body["total_assets_value"] == 0.0
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

    def test_assets_included_in_net_worth(self, client, db):
        _seed_tax_config(db)
        _register(client)
        headers = _auth_header(client)

        # Property asset: £300,000
        client.post("/api/assets", json={
            "name": "Family Home",
            "asset_type": "property",
            "current_value": 300_000.0,
        }, headers=headers)

        # Mortgage debt: £220,000 — behaves like "other" (no student loan plan)
        client.post("/api/debts", json={
            "debt_type": "mortgage",
            "balance": 220_000.0,
            "interest_rate": 4.5,
            "min_payment": 1_200.0,
        }, headers=headers)

        body = client.get(SUMMARY, headers=headers).json()
        assert body["total_assets_value"] == 300_000.0
        assert body["total_debt_balance"] == 220_000.0
        # Net equity from property alone: 300k - 220k = 80k
        assert body["net_worth"] == 80_000.0

    def test_net_worth_combines_all_balance_types(self, client, db):
        _seed_tax_config(db)
        _register(client)
        headers = _auth_header(client)

        client.post("/api/savings", json={
            "name": "ISA", "current_balance": 10_000.0,
            "target_amount": 20_000.0, "monthly_contribution": 0.0,
        }, headers=headers)
        client.post("/api/pension", json={
            "current_balance": 15_000.0,
            "employee_contribution_pct": 5.0, "employer_contribution_pct": 3.0,
        }, headers=headers)
        client.post("/api/assets", json={
            "name": "Car", "asset_type": "vehicle", "current_value": 8_000.0,
        }, headers=headers)
        client.post("/api/debts", json={
            "debt_type": "credit_card", "balance": 3_000.0,
            "interest_rate": 22.0, "min_payment": 100.0,
        }, headers=headers)

        body = client.get(SUMMARY, headers=headers).json()
        # 10,000 + 15,000 + 8,000 - 3,000 = 30,000
        assert body["net_worth"] == 30_000.0


# ---------------------------------------------------------------------------
# Finance summary — months of runway
# ---------------------------------------------------------------------------

class TestMonthsOfRunway:
    def test_no_expenses_returns_null(self, client, db):
        _seed_tax_config(db)
        _register(client)
        body = client.get(SUMMARY, headers=_auth_header(client)).json()
        assert body["months_of_runway"] is None

    def test_no_savings_returns_zero(self, client, db):
        _seed_tax_config(db)
        _register(client)
        headers = _auth_header(client)
        # £1,200/month expenses, no savings
        client.post("/api/expenses", json={
            "category": "Rent", "amount": 1200.0, "frequency": "monthly", "is_fixed": True,
        }, headers=headers)
        body = client.get(SUMMARY, headers=headers).json()
        assert body["months_of_runway"] == 0.0

    def test_runway_rounds_to_one_decimal(self, client, db):
        _seed_tax_config(db)
        _register(client)
        headers = _auth_header(client)
        # £5,000 savings / £1,200/month = 4.1667 → rounds to 4.2
        client.post("/api/savings", json={
            "name": "Emergency fund", "current_balance": 5000.0,
            "target_amount": 10000.0, "monthly_contribution": 0.0,
        }, headers=headers)
        client.post("/api/expenses", json={
            "category": "Rent", "amount": 1200.0, "frequency": "monthly", "is_fixed": True,
        }, headers=headers)
        body = client.get(SUMMARY, headers=headers).json()
        assert body["months_of_runway"] == 4.2

    def test_runway_exact_months(self, client, db):
        _seed_tax_config(db)
        _register(client)
        headers = _auth_header(client)
        # £3,000 savings / £1,000/month = exactly 3.0
        client.post("/api/savings", json={
            "name": "Emergency fund", "current_balance": 3000.0,
            "target_amount": 5000.0, "monthly_contribution": 0.0,
        }, headers=headers)
        client.post("/api/expenses", json={
            "category": "Expenses", "amount": 1000.0, "frequency": "monthly", "is_fixed": True,
        }, headers=headers)
        body = client.get(SUMMARY, headers=headers).json()
        assert body["months_of_runway"] == 3.0

    def test_runway_uses_monthly_equivalent_of_annual_expense(self, client, db):
        # Confirms _to_monthly() is applied before dividing
        _seed_tax_config(db)
        _register(client)
        headers = _auth_header(client)
        # £12,000 annual expense = £1,000/month; £6,000 savings → 6.0 months
        client.post("/api/savings", json={
            "name": "Fund", "current_balance": 6000.0,
            "target_amount": 10000.0, "monthly_contribution": 0.0,
        }, headers=headers)
        client.post("/api/expenses", json={
            "category": "Annual bills", "amount": 12000.0, "frequency": "annual", "is_fixed": True,
        }, headers=headers)
        body = client.get(SUMMARY, headers=headers).json()
        assert body["months_of_runway"] == 6.0

    def test_non_student_loan_debt_reduces_runway(self, client, db):
        # Credit card min payments persist with no income → must reduce runway
        _seed_tax_config(db)
        _register(client)
        headers = _auth_header(client)
        client.post("/api/savings", json={
            "name": "Emergency fund", "current_balance": 6000.0,
            "target_amount": 10000.0, "monthly_contribution": 0.0,
        }, headers=headers)
        client.post("/api/expenses", json={
            "category": "Rent", "amount": 800.0, "frequency": "monthly", "is_fixed": True,
        }, headers=headers)
        client.post("/api/debts", json={
            "debt_type": "credit_card", "balance": 2000.0,
            "interest_rate": 22.0, "min_payment": 200.0,
        }, headers=headers)
        body = client.get(SUMMARY, headers=headers).json()
        # £6,000 / (£800 expenses + £200 credit card) = £6,000 / £1,000 = 6.0 months
        assert body["months_of_runway"] == 6.0

    def test_student_loan_debt_does_not_reduce_runway(self, client, db):
        # Student loan repayments are income-contingent — they stop with no income,
        # so they must NOT be included in the runway denominator.
        _seed_tax_config(db)
        from app.models.config import StudentLoanPlanConfig
        db.add(StudentLoanPlanConfig(
            plan_name="Plan 2", tax_year="2026/27", threshold=29385, repayment_rate_pct=9
        ))
        db.commit()

        _register(client)
        headers = _auth_header(client)
        plan_id = db.query(StudentLoanPlanConfig).first().id

        client.post("/api/savings", json={
            "name": "Emergency fund", "current_balance": 6000.0,
            "target_amount": 10000.0, "monthly_contribution": 0.0,
        }, headers=headers)
        client.post("/api/expenses", json={
            "category": "Rent", "amount": 1000.0, "frequency": "monthly", "is_fixed": True,
        }, headers=headers)
        client.post("/api/debts", json={
            "debt_type": "student_loan",
            "balance": 40000.0,
            "interest_rate": 7.3,
            "min_payment": 0.0,
            "student_loan_plan_id": plan_id,
        }, headers=headers)
        body = client.get(SUMMARY, headers=headers).json()
        # Student loan doesn't affect runway denominator → still £6,000 / £1,000 = 6.0 months
        assert body["months_of_runway"] == 6.0


# ---------------------------------------------------------------------------
# Debt projection endpoint
# ---------------------------------------------------------------------------

class TestDebtProjectionEndpoint:
    def _seed_plan(self, db, write_off_years=30):
        from app.models.config import StudentLoanPlanConfig
        plan = StudentLoanPlanConfig(
            plan_name="Plan 2", tax_year="2026/27",
            threshold=29385, repayment_rate_pct=9, write_off_years=write_off_years,
        )
        db.add(plan)
        db.commit()
        return db.query(StudentLoanPlanConfig).first().id

    def test_projection_paid_off_for_high_earner(self, client, db):
        _seed_tax_config(db)
        plan_id = self._seed_plan(db)
        _register(client)
        headers = _auth_header(client)

        client.post("/api/income", json={
            "label": "Salary", "gross_annual_salary": 80_000.0, "pay_frequency": "monthly",
        }, headers=headers)
        debt_resp = client.post("/api/debts", json={
            "debt_type": "student_loan", "balance": 20_000.0, "interest_rate": 7.3,
            "min_payment": 0.0, "student_loan_plan_id": plan_id, "graduation_year": 2020,
        }, headers=headers)
        debt_id = debt_resp.json()["id"]

        body = client.get(f"/api/debts/{debt_id}/projection", headers=headers).json()
        assert body["outcome"] == "paid_off"
        assert body["payoff_date"] is not None
        assert body["remaining_balance_at_writeoff"] == 0.0
        assert body["annual_salary_assumption"] == 80_000.0

    def test_projection_written_off_for_average_earner(self, client, db):
        _seed_tax_config(db)
        plan_id = self._seed_plan(db)
        _register(client)
        headers = _auth_header(client)

        client.post("/api/income", json={
            "label": "Salary", "gross_annual_salary": 30_000.0, "pay_frequency": "monthly",
        }, headers=headers)
        debt_resp = client.post("/api/debts", json={
            "debt_type": "student_loan", "balance": 60_000.0, "interest_rate": 7.3,
            "min_payment": 0.0, "student_loan_plan_id": plan_id, "graduation_year": 2020,
        }, headers=headers)
        debt_id = debt_resp.json()["id"]

        body = client.get(f"/api/debts/{debt_id}/projection", headers=headers).json()
        assert body["outcome"] == "written_off"
        assert body["payoff_date"] is None
        assert body["remaining_balance_at_writeoff"] > 60_000.0

    def test_projection_requires_graduation_year(self, client, db):
        _seed_tax_config(db)
        plan_id = self._seed_plan(db)
        _register(client)
        headers = _auth_header(client)
        debt_resp = client.post("/api/debts", json={
            "debt_type": "student_loan", "balance": 30_000.0, "interest_rate": 7.3,
            "min_payment": 0.0, "student_loan_plan_id": plan_id,
        }, headers=headers)
        debt_id = debt_resp.json()["id"]
        resp = client.get(f"/api/debts/{debt_id}/projection", headers=headers)
        assert resp.status_code == 400

    def test_projection_rejects_non_student_loan(self, client, db):
        _seed_tax_config(db)
        _register(client)
        headers = _auth_header(client)
        debt_resp = client.post("/api/debts", json={
            "debt_type": "credit_card", "balance": 5_000.0,
            "interest_rate": 22.0, "min_payment": 150.0,
        }, headers=headers)
        debt_id = debt_resp.json()["id"]
        resp = client.get(f"/api/debts/{debt_id}/projection", headers=headers)
        assert resp.status_code == 400

    def test_projection_uses_sum_of_all_income_sources(self, client, db):
        _seed_tax_config(db)
        plan_id = self._seed_plan(db)
        _register(client)
        headers = _auth_header(client)

        # Two income sources that together push past the threshold enough to pay off
        client.post("/api/income", json={
            "label": "Job 1", "gross_annual_salary": 40_000.0, "pay_frequency": "monthly",
        }, headers=headers)
        client.post("/api/income", json={
            "label": "Job 2", "gross_annual_salary": 40_000.0, "pay_frequency": "monthly",
        }, headers=headers)
        debt_resp = client.post("/api/debts", json={
            "debt_type": "student_loan", "balance": 20_000.0, "interest_rate": 7.3,
            "min_payment": 0.0, "student_loan_plan_id": plan_id, "graduation_year": 2020,
        }, headers=headers)
        debt_id = debt_resp.json()["id"]

        body = client.get(f"/api/debts/{debt_id}/projection", headers=headers).json()
        assert body["annual_salary_assumption"] == 80_000.0
        assert body["outcome"] == "paid_off"

    def test_projection_isolated_between_users(self, client, db):
        _seed_tax_config(db)
        plan_id = self._seed_plan(db)
        bob = {"email": "bob@example.com", "password": "bobpass1"}
        _register(client)
        client.post("/api/auth/register", json=bob)
        alice_headers = _auth_header(client)
        bob_headers = _auth_header(client, bob)

        debt_resp = client.post("/api/debts", json={
            "debt_type": "student_loan", "balance": 20_000.0, "interest_rate": 7.3,
            "min_payment": 0.0, "student_loan_plan_id": plan_id, "graduation_year": 2020,
        }, headers=alice_headers)
        alice_debt_id = debt_resp.json()["id"]

        # Bob cannot access Alice's debt projection (404, not 403, to prevent data leakage)
        resp = client.get(f"/api/debts/{alice_debt_id}/projection", headers=bob_headers)
        assert resp.status_code == 404
