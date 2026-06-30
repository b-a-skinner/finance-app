"""
Shared financial summary computation — called by both the finance route and the
snapshot service so the two never diverge in their figures.
"""
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import Asset, Debt, Expense, IncomeSource, PensionPot, SavingsGoal, TaxYearConfig
from app.services.tax_calculator import calculate_take_home_pay

CURRENT_TAX_YEAR = "2026/27"


def _to_monthly(amount: float, frequency: str) -> float:
    if frequency == "weekly":
        return amount * 52 / 12
    if frequency == "annual":
        return amount / 12
    return amount  # monthly


@dataclass
class SnapshotValues:
    net_worth: float
    monthly_disposable_income: float
    total_savings_balance: float
    total_debt_balance: float
    pension_pot_balance: float
    months_of_runway: float | None


def compute_snapshot_values(user_id: int, db: Session) -> SnapshotValues | None:
    """
    Compute the six metrics stored in FinancialSnapshot.
    Returns None when the required tax config is not yet seeded — callers should
    silently skip snapshot insertion rather than recording a row of zeros.
    """
    tax_config = db.query(TaxYearConfig).filter_by(tax_year=CURRENT_TAX_YEAR).first()
    if not tax_config:
        return None

    # ── Income ──────────────────────────────────────────────────────────────
    income_sources = db.query(IncomeSource).filter_by(user_id=user_id, is_active=True).all()
    gross = sum(s.gross_annual_salary for s in income_sources)

    # ── Student loans (income-contingent, already in take-home calc) ────────
    student_loan_debts = db.query(Debt).filter_by(
        user_id=user_id, debt_type="student_loan", is_active=True
    ).all()
    loan_plans = [d.student_loan_plan for d in student_loan_debts if d.student_loan_plan is not None]

    # ── Pension ─────────────────────────────────────────────────────────────
    all_pension_pots = db.query(PensionPot).filter_by(user_id=user_id, is_active=True).all()
    first_pension = all_pension_pots[0] if all_pension_pots else None
    employee_pct = first_pension.employee_contribution_pct if first_pension else 0.0
    employer_pct = first_pension.employer_contribution_pct if first_pension else 0.0

    breakdown = calculate_take_home_pay(gross, tax_config, loan_plans, employee_pct, employer_pct)

    # ── Monthly outgoings ────────────────────────────────────────────────────
    expenses = db.query(Expense).filter_by(user_id=user_id, is_active=True).all()
    monthly_expenses = sum(_to_monthly(e.amount, e.frequency) for e in expenses)

    other_debts = db.query(Debt).filter(
        Debt.user_id == user_id, Debt.is_active == True, Debt.debt_type != "student_loan"
    ).all()
    monthly_debt_payments = sum(d.min_payment for d in other_debts)

    savings_goals = db.query(SavingsGoal).filter_by(user_id=user_id, is_active=True).all()
    monthly_savings = sum(s.monthly_contribution for s in savings_goals)

    monthly_disposable = round(
        breakdown.net_monthly - monthly_expenses - monthly_debt_payments - monthly_savings, 2
    )

    # ── Balances ─────────────────────────────────────────────────────────────
    all_debts = db.query(Debt).filter_by(user_id=user_id, is_active=True).all()
    all_assets = db.query(Asset).filter_by(user_id=user_id, is_active=True).all()

    total_savings_balance = round(sum(s.current_balance for s in savings_goals), 2)
    pension_pot_balance = round(sum(p.current_balance for p in all_pension_pots), 2)
    total_assets_value = round(sum(a.current_value for a in all_assets), 2)
    total_debt_balance = round(sum(d.balance for d in all_debts), 2)
    net_worth = round(
        total_savings_balance + pension_pot_balance + total_assets_value - total_debt_balance, 2
    )

    _runway_denom = monthly_expenses + monthly_debt_payments
    months_of_runway = (
        round(total_savings_balance / _runway_denom, 1) if _runway_denom > 0 else None
    )

    return SnapshotValues(
        net_worth=net_worth,
        monthly_disposable_income=monthly_disposable,
        total_savings_balance=total_savings_balance,
        total_debt_balance=total_debt_balance,
        pension_pot_balance=pension_pot_balance,
        months_of_runway=months_of_runway,
    )
