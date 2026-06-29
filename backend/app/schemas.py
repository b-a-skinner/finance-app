from datetime import date

from pydantic import BaseModel, ConfigDict, field_validator

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
    graduation_year: int | None = None


class DebtUpdate(BaseModel):
    debt_type: str | None = None
    balance: float | None = None
    interest_rate: float | None = None
    min_payment: float | None = None
    student_loan_plan_id: int | None = None
    graduation_year: int | None = None


class DebtOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    debt_type: str
    balance: float
    interest_rate: float
    min_payment: float
    student_loan_plan_id: int | None
    graduation_year: int | None
    is_active: bool


# ---------------------------------------------------------------------------
# LoanProjection
# ---------------------------------------------------------------------------

class LoanProjectionOut(BaseModel):
    outcome: str               # "paid_off" | "written_off"
    first_repay_date: date
    write_off_date: date
    payoff_date: date | None
    remaining_balance_at_writeoff: float
    years_simulated: float
    annual_salary_assumption: float


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


# ---------------------------------------------------------------------------
# Asset
# ---------------------------------------------------------------------------

class AssetCreate(BaseModel):
    name: str
    asset_type: str
    current_value: float


class AssetUpdate(BaseModel):
    name: str | None = None
    asset_type: str | None = None
    current_value: float | None = None


class AssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    asset_type: str
    current_value: float
    is_active: bool


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

class ProfileUpdate(BaseModel):
    date_of_birth: date | None = None
    occupation: str | None = None
    postcode_outward: str | None = None

    @field_validator("postcode_outward")
    @classmethod
    def validate_postcode_outward(cls, v: str | None) -> str | None:
        if v is None:
            return None
        from app.services.postcode_lookup import validate_postcode_outward
        normalised = v.strip().upper()
        if not validate_postcode_outward(normalised):
            raise ValueError(
                "Invalid UK outward code — use just the first part of your postcode, "
                "e.g. SW1A or M1 (1–2 letters followed by 1–2 alphanumeric characters)."
            )
        return normalised


class ProfileOut(BaseModel):
    date_of_birth: date | None
    occupation: str | None
    postcode_outward: str | None
    region: str | None
