from datetime import date
from typing import Literal

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
# LoanProjection (student loan)
# ---------------------------------------------------------------------------

class LoanProjectionOut(BaseModel):
    outcome: str               # "paid_off" | "written_off"
    first_repay_date: date
    write_off_date: date
    payoff_date: date | None
    remaining_balance_at_writeoff: float
    years_simulated: float
    annual_salary_assumption: float


class DebtRepaymentProjectionOut(BaseModel):
    months_to_payoff: int | None
    projected_payoff_date: str | None
    total_interest_to_pay: float | None
    payment_covers_interest: bool
    is_student_loan: bool


# ---------------------------------------------------------------------------
# SavingsGoal
# ---------------------------------------------------------------------------

class SavingsCreate(BaseModel):
    name: str = ""
    current_balance: float
    target_amount: float | None = None
    monthly_contribution: float
    account_type: str | None = None


class SavingsUpdate(BaseModel):
    name: str | None = None
    current_balance: float | None = None
    target_amount: float | None = None
    monthly_contribution: float | None = None
    account_type: str | None = None


class SavingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    current_balance: float
    target_amount: float | None
    monthly_contribution: float
    account_type: str | None
    is_active: bool

    @field_validator('target_amount', mode='before')
    @classmethod
    def zero_target_to_none(cls, v):
        if v == 0.0:
            return None
        return v


class SavingsProjectionOut(BaseModel):
    months_to_goal: int
    projected_date: str


# ---------------------------------------------------------------------------
# PensionPot
# ---------------------------------------------------------------------------

class PensionCreate(BaseModel):
    name: str | None = None
    current_balance: float
    employee_contribution_pct: float
    employer_contribution_pct: float


class PensionUpdate(BaseModel):
    name: str | None = None
    current_balance: float | None = None
    employee_contribution_pct: float | None = None
    employer_contribution_pct: float | None = None


class PensionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str | None
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
    first_name: str | None = None
    date_of_birth: date | None = None
    occupation: str | None = None
    postcode_outward: str | None = None
    business_type: str | None = None

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
    first_name: str | None
    date_of_birth: date | None
    occupation: str | None
    postcode_outward: str | None
    region: str | None
    active_mode: str | None
    business_type: str | None


class ModeUpdate(BaseModel):
    active_mode: Literal['personal', 'business']


# ---------------------------------------------------------------------------
# OccupationCode
# ---------------------------------------------------------------------------

class OccupationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    soc_code: str
    soc_group: str


# ---------------------------------------------------------------------------
# Onboarding
# ---------------------------------------------------------------------------

class OnboardingUpdate(BaseModel):
    onboarding_completed: bool | None = None
    onboarding_dismiss_count: int | None = None
    financial_goals: str | None = None
    current_onboarding_step: int | None = None


class OnboardingOut(BaseModel):
    onboarding_completed: bool
    onboarding_dismiss_count: int
    financial_goals: str | None
    current_onboarding_step: int


# ---------------------------------------------------------------------------
# AgeComparison
# ---------------------------------------------------------------------------

class AgeComparisonOut(BaseModel):
    user_age: int | None
    current_monthly_salary: float
    current_annual_salary: float
    current_pension_pot: float
    # Age-based salary
    salary_band_label: str | None
    median_monthly_salary: float | None
    salary_comparison_pct: float | None
    salary_source: str | None
    salary_source_metric: str | None
    # Pension
    pension_band_label: str | None
    median_pension_pot: float | None
    pension_comparison_pct: float | None
    pension_data_available: bool
    pension_source: str | None
    pension_source_metric: str | None
    # Regional salary
    region: str | None
    median_annual_salary_for_region: float | None
    salary_vs_region_pct: float | None
    region_source: str | None
    region_source_notes: str | None
    is_london: bool
    # Occupation salary
    occupation_soc_group_description: str | None
    occupation_median_annual_salary: float | None
    salary_vs_occupation_pct: float | None
    occupation_match_level: int | None
    occupation_source: str | None
    occupation_source_notes: str | None


# ---------------------------------------------------------------------------
# Business
# ---------------------------------------------------------------------------

class BusinessIncomeCreate(BaseModel):
    amount: float
    date_received: date
    description: str | None = None


class BusinessIncomeUpdate(BaseModel):
    amount: float | None = None
    date_received: date | None = None
    description: str | None = None


class BusinessIncomeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    amount: float
    date_received: date
    description: str | None
    is_approved: bool


class BusinessExpenseCreate(BaseModel):
    amount: float
    date_incurred: date
    category: str
    description: str | None = None
    is_allowable: bool = True
    business_use_percent: int = 100
    expense_method: str | None = None
    home_office_hours_band: str | None = None
    business_miles: int | None = None
    vehicle_type: str | None = None


class BusinessExpenseUpdate(BaseModel):
    amount: float | None = None
    date_incurred: date | None = None
    category: str | None = None
    description: str | None = None
    is_allowable: bool | None = None
    business_use_percent: int | None = None
    expense_method: str | None = None
    home_office_hours_band: str | None = None
    business_miles: int | None = None
    vehicle_type: str | None = None


class BusinessExpenseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    amount: float
    date_incurred: date
    category: str
    description: str | None
    is_allowable: bool
    business_use_percent: int
    expense_method: str | None
    home_office_hours_band: str | None
    business_miles: int | None
    vehicle_type: str | None
    is_approved: bool


class ApproveIncomeBody(BaseModel):
    amount: float | None = None
    date_received: date | None = None


class ApproveExpenseBody(BaseModel):
    amount: float | None = None
    date_incurred: date | None = None


class BusinessUpcomingOut(BaseModel):
    income: list[BusinessIncomeOut]
    expenses: list[BusinessExpenseOut]


class BusinessTaxConfigOut(BaseModel):
    tax_year: str
    home_office_band_25_50: float
    home_office_band_51_100: float
    home_office_band_101_plus: float
    mileage_car_van_first: float
    mileage_car_van_over: float
    mileage_motorcycle: float
    mileage_bicycle: float
    mileage_threshold: int
    # Class 4 NI — nullable: rows seeded before these columns existed will return null
    class4_lower_limit: float | None = None
    class4_upper_limit: float | None = None
    class4_main_rate: float | None = None
    class4_upper_rate: float | None = None
    # Class 2 NI
    class2_small_profits_threshold: float | None = None
    class2_weekly_rate: float | None = None


class SoleTraderTaxOut(BaseModel):
    taxable_profit: float
    income_tax_on_profit: float
    class4_ni: float
    class2_status: str          # "covered" | "covered_no_class4" | "below_threshold"
    class2_due: float
    class2_voluntary_note: str | None
    total_set_aside: float
    effective_rate: float


class BusinessSummaryOut(BaseModel):
    revenue_ytd: float
    total_expenses_ytd: float
    allowable_expenses_ytd: float
    cash_profit: float
    taxable_profit: float
    has_business_data: bool
    total_business_miles: int
    total_mileage_allowance: float
    home_office_allowance: float = 0.0
    mileage_crossover_msg: str | None
    mileage_attribution: dict[int, float] = {}  # entry_id → attributed allowance
    tax_estimate: SoleTraderTaxOut | None = None
