"""Test that pension contributions from all active pots are summed in the dashboard."""
import pytest
from app.models.config import TaxYearConfig
from app.services.finance_summary import CURRENT_TAX_YEAR


REGISTER = "/api/auth/register"
LOGIN = "/api/auth/login"


def auth(client, email="alice@test.com", password="testpass123!"):
    client.post(REGISTER, json={"email": email, "password": password})
    r = client.post(LOGIN, data={"username": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(autouse=True)
def seed_tax_config(db):
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


def test_dashboard_sums_contributions_across_all_pots(client):
    """Two pension pots with different rates → dashboard deduction equals combined total."""
    h = auth(client)

    # Add income so the tax calculation has something to work with
    client.post("/api/income", json={"label": "Salary", "gross_annual_salary": 60000, "pay_frequency": "annual"}, headers=h)

    # Pot 1: 5% employee, 3% employer
    client.post("/api/pension", json={"current_balance": 10000, "employee_contribution_pct": 5.0, "employer_contribution_pct": 3.0}, headers=h)
    # Pot 2: 3% employee, 2% employer
    client.post("/api/pension", json={"current_balance": 5000, "employee_contribution_pct": 3.0, "employer_contribution_pct": 2.0}, headers=h)

    r = client.get("/api/finance/summary", headers=h)
    assert r.status_code == 200
    summary = r.json()

    # Contributions apply to qualifying earnings only (between lower and upper band)
    qualifying = min(60000, 50270) - 6240   # = 44030
    expected_employee = qualifying * (5.0 + 3.0) / 100   # 3522.4
    expected_employer = qualifying * (3.0 + 2.0) / 100   # 2201.5

    assert summary["take_home"]["pension_employee"] == pytest.approx(expected_employee, rel=1e-4)
    assert summary["take_home"]["pension_employer"] == pytest.approx(expected_employer, rel=1e-4)
