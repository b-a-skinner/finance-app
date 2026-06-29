from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Asset, Debt, Expense, IncomeSource, PensionPot, SavingsGoal, TaxYearConfig
from app.routes.auth import get_current_user
from app.models.user import User
from app.services.tax_calculator import calculate_take_home_pay

router = APIRouter(prefix="/finance", tags=["finance"])

CURRENT_TAX_YEAR = "2026/27"


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class TakeHomeOut(BaseModel):
    gross_annual: float
    income_tax: float
    national_insurance: float
    student_loan: float
    pension_employee: float
    pension_employer: float
    net_annual: float
    net_monthly: float


class FinancialSummaryOut(BaseModel):
    user_id: int
    tax_year: str
    take_home: TakeHomeOut
    monthly_expenses: float
    monthly_debt_payments: float
    monthly_savings_contributions: float
    monthly_disposable: float
    total_savings_balance: float
    pension_pot_balance: float
    total_assets_value: float
    total_debt_balance: float
    net_worth: float
    months_of_runway: float | None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_monthly(amount: float, frequency: str) -> float:
    """Convert an amount in any pay frequency to a monthly equivalent."""
    if frequency == "weekly":
        return amount * 52 / 12
    if frequency == "annual":
        return amount / 12
    return amount  # monthly


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/summary", response_model=FinancialSummaryOut)
def get_financial_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_id = current_user.id

    tax_config = db.query(TaxYearConfig).filter_by(tax_year=CURRENT_TAX_YEAR).first()
    if not tax_config:
        raise HTTPException(
            status_code=500,
            detail=f"Tax config for {CURRENT_TAX_YEAR} not found — run seed.py",
        )

    # ---- Income ----
    # Returns 0 gross for new users who haven't added income sources yet
    income_sources = db.query(IncomeSource).filter_by(user_id=user_id, is_active=True).all()
    gross = sum(src.gross_annual_salary for src in income_sources)

    # ---- Student loans ----
    # Income-contingent repayments are part of take-home; min_payment on these debts
    # is excluded from monthly_debt_payments below to avoid double-counting.
    student_loan_debts = (
        db.query(Debt)
        .filter_by(user_id=user_id, debt_type="student_loan", is_active=True)
        .all()
    )
    loan_plans = [d.student_loan_plan for d in student_loan_debts if d.student_loan_plan is not None]

    # ---- Pension ----
    # First active pot drives contribution percentages for the take-home calculation.
    # All active pots are summed for the balance / net worth figures.
    all_pension_pots = db.query(PensionPot).filter_by(user_id=user_id, is_active=True).all()
    first_pension = all_pension_pots[0] if all_pension_pots else None
    employee_pct = first_pension.employee_contribution_pct if first_pension else 0.0
    employer_pct = first_pension.employer_contribution_pct if first_pension else 0.0

    breakdown = calculate_take_home_pay(gross, tax_config, loan_plans, employee_pct, employer_pct)

    # ---- Monthly outgoings ----
    expenses = db.query(Expense).filter_by(user_id=user_id, is_active=True).all()
    monthly_expenses = sum(_to_monthly(e.amount, e.frequency) for e in expenses)

    # Student loan debts excluded — their repayment is already in take_home.student_loan
    other_debts = (
        db.query(Debt)
        .filter(Debt.user_id == user_id, Debt.is_active == True, Debt.debt_type != "student_loan")
        .all()
    )
    monthly_debt_payments = sum(d.min_payment for d in other_debts)

    savings_goals = db.query(SavingsGoal).filter_by(user_id=user_id, is_active=True).all()
    monthly_savings = sum(s.monthly_contribution for s in savings_goals)

    monthly_disposable = round(
        breakdown.net_monthly - monthly_expenses - monthly_debt_payments - monthly_savings, 2
    )

    # ---- Balance / net worth ----
    all_debts = db.query(Debt).filter_by(user_id=user_id, is_active=True).all()
    all_assets = db.query(Asset).filter_by(user_id=user_id, is_active=True).all()

    total_savings_balance = round(sum(s.current_balance for s in savings_goals), 2)
    pension_pot_balance = round(sum(p.current_balance for p in all_pension_pots), 2)
    total_assets_value = round(sum(a.current_value for a in all_assets), 2)
    total_debt_balance = round(sum(d.balance for d in all_debts), 2)
    net_worth = round(
        total_savings_balance + pension_pot_balance + total_assets_value - total_debt_balance, 2
    )

    # Runway denominator includes mandatory debt payments (credit card, mortgage, etc.)
    # that persist with no income. monthly_debt_payments already excludes student loans,
    # which are income-contingent and would stop with no income — reuse it directly.
    _runway_denom = monthly_expenses + monthly_debt_payments
    months_of_runway = (
        round(total_savings_balance / _runway_denom, 1)
        if _runway_denom > 0
        else None
    )

    return FinancialSummaryOut(
        user_id=user_id,
        tax_year=CURRENT_TAX_YEAR,
        take_home=TakeHomeOut(
            gross_annual=breakdown.gross_annual,
            income_tax=breakdown.income_tax,
            national_insurance=breakdown.national_insurance,
            student_loan=breakdown.student_loan,
            pension_employee=breakdown.pension_employee,
            pension_employer=breakdown.pension_employer,
            net_annual=breakdown.net_annual,
            net_monthly=breakdown.net_monthly,
        ),
        monthly_expenses=round(monthly_expenses, 2),
        monthly_debt_payments=round(monthly_debt_payments, 2),
        monthly_savings_contributions=round(monthly_savings, 2),
        monthly_disposable=monthly_disposable,
        total_savings_balance=total_savings_balance,
        pension_pot_balance=pension_pot_balance,
        total_assets_value=total_assets_value,
        total_debt_balance=total_debt_balance,
        net_worth=net_worth,
        months_of_runway=months_of_runway,
    )
