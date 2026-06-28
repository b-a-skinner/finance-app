from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Debt, Expense, IncomeSource, PensionPot, SavingsGoal, TaxYearConfig
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
    loan_plans = [
        debt.student_loan_plan
        for debt in db.query(Debt).filter_by(user_id=user_id, debt_type="student_loan", is_active=True).all()
        if debt.student_loan_plan is not None
    ]

    # ---- Pension ----
    # Use the first active pension pot. Multi-pot aggregation can be added later.
    pension = db.query(PensionPot).filter_by(user_id=user_id, is_active=True).first()
    employee_pct = pension.employee_contribution_pct if pension else 0.0
    employer_pct = pension.employer_contribution_pct if pension else 0.0

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
    )
