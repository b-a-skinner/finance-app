from pydantic import BaseModel, ConfigDict

from app.models.finance import PayFrequency


# ---------------------------------------------------------------------------
# IncomeSource
# ---------------------------------------------------------------------------

class IncomeCreate(BaseModel):
    label: str
    gross_annual_salary: float
    pay_frequency: PayFrequency


class IncomeUpdate(BaseModel):
    label: str | None = None
    gross_annual_salary: float | None = None
    pay_frequency: PayFrequency | None = None


class IncomeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    label: str
    gross_annual_salary: float
    pay_frequency: PayFrequency
    is_active: bool


# ---------------------------------------------------------------------------
# Expense
# ---------------------------------------------------------------------------

class ExpenseCreate(BaseModel):
    category: str
    amount: float
    frequency: PayFrequency
    is_fixed: bool


class ExpenseUpdate(BaseModel):
    category: str | None = None
    amount: float | None = None
    frequency: PayFrequency | None = None
    is_fixed: bool | None = None


class ExpenseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    category: str
    amount: float
    frequency: PayFrequency
    is_fixed: bool
    is_active: bool


# ---------------------------------------------------------------------------
# Debt
# ---------------------------------------------------------------------------

class DebtCreate(BaseModel):
    debt_type: str
    balance: float
    interest_rate: float
    min_payment: float
    student_loan_plan_id: int | None = None


class DebtUpdate(BaseModel):
    debt_type: str | None = None
    balance: float | None = None
    interest_rate: float | None = None
    min_payment: float | None = None
    student_loan_plan_id: int | None = None


class DebtOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    debt_type: str
    balance: float
    interest_rate: float
    min_payment: float
    student_loan_plan_id: int | None
    is_active: bool


# ---------------------------------------------------------------------------
# SavingsGoal
# ---------------------------------------------------------------------------

class SavingsCreate(BaseModel):
    name: str
    current_balance: float
    target_amount: float
    monthly_contribution: float


class SavingsUpdate(BaseModel):
    name: str | None = None
    current_balance: float | None = None
    target_amount: float | None = None
    monthly_contribution: float | None = None


class SavingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    current_balance: float
    target_amount: float
    monthly_contribution: float
    is_active: bool


# ---------------------------------------------------------------------------
# PensionPot
# ---------------------------------------------------------------------------

class PensionCreate(BaseModel):
    current_balance: float
    employee_contribution_pct: float
    employer_contribution_pct: float


class PensionUpdate(BaseModel):
    current_balance: float | None = None
    employee_contribution_pct: float | None = None
    employer_contribution_pct: float | None = None


class PensionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    current_balance: float
    employee_contribution_pct: float
    employer_contribution_pct: float
    is_active: bool
