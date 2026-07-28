import enum
from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Date, DateTime, Enum as SAEnum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.config import StudentLoanPlanConfig
    from app.models.user import User


class PayFrequency(str, enum.Enum):
    monthly = "monthly"
    weekly = "weekly"
    annual = "annual"


class AssetType(str, enum.Enum):
    property = "property"
    vehicle = "vehicle"
    other = "other"


class IncomeSource(TimestampMixin, Base):
    __tablename__ = "income_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    gross_annual_salary: Mapped[float] = mapped_column(Float, nullable=False)
    pay_frequency: Mapped[PayFrequency] = mapped_column(SAEnum(PayFrequency), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["User"] = relationship(back_populates="income_sources")


class Expense(TimestampMixin, Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    frequency: Mapped[PayFrequency] = mapped_column(SAEnum(PayFrequency), nullable=False)
    is_fixed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["User"] = relationship(back_populates="expenses")


class Debt(TimestampMixin, Base):
    __tablename__ = "debts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    debt_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "student_loan" | "credit_card" | "mortgage" | "other"
    balance: Mapped[float] = mapped_column(Float, nullable=False)
    interest_rate: Mapped[float] = mapped_column(Float, nullable=False)
    min_payment: Mapped[float] = mapped_column(Float, nullable=False)
    # Only set when debt_type == "student_loan"
    student_loan_plan_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("student_loan_plan_configs.id"), nullable=True
    )
    graduation_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["User"] = relationship(back_populates="debts")
    student_loan_plan: Mapped[Optional["StudentLoanPlanConfig"]] = relationship()


class SavingsGoal(TimestampMixin, Base):
    __tablename__ = "savings_goals"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    current_balance: Mapped[float] = mapped_column(Float, nullable=False)
    target_amount: Mapped[float] = mapped_column(Float, nullable=False)
    monthly_contribution: Mapped[float] = mapped_column(Float, nullable=False)
    account_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["User"] = relationship(back_populates="savings_goals")


class PensionPot(TimestampMixin, Base):
    __tablename__ = "pension_pots"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    current_balance: Mapped[float] = mapped_column(Float, nullable=False)
    employee_contribution_pct: Mapped[float] = mapped_column(Float, nullable=False)
    employer_contribution_pct: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["User"] = relationship(back_populates="pension_pots")


class Asset(TimestampMixin, Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_type: Mapped[AssetType] = mapped_column(SAEnum(AssetType), nullable=False)
    current_value: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["User"] = relationship(back_populates="assets")


class FinancialSnapshot(TimestampMixin, Base):
    """Point-in-time record of a user's key financial metrics. Captured lazily — no scheduler needed."""

    __tablename__ = "financial_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    net_worth: Mapped[float] = mapped_column(Float, nullable=False)
    monthly_disposable_income: Mapped[float] = mapped_column(Float, nullable=False)
    total_savings_balance: Mapped[float] = mapped_column(Float, nullable=False)
    total_debt_balance: Mapped[float] = mapped_column(Float, nullable=False)
    pension_pot_balance: Mapped[float] = mapped_column(Float, nullable=False)
    months_of_runway: Mapped[Optional[float]] = mapped_column(Float, nullable=True)


class BusinessExpenseCategory(str, enum.Enum):
    # Allowable by default
    equipment         = "equipment"
    software          = "software"
    office            = "office"
    travel            = "travel"
    professional_fees = "professional_fees"
    marketing         = "marketing"
    training          = "training"
    insurance         = "insurance"
    staff_costs       = "staff_costs"
    phone_internet    = "phone_internet"
    pension_employer  = "pension_employer"
    bank_charges      = "bank_charges"
    # Non-allowable by default
    client_entertainment = "client_entertainment"
    fines    = "fines"
    personal = "personal"
    political = "political"
    # Dual-purpose — user confirms
    home_office = "home_office"
    other       = "other"


class BusinessIncome(TimestampMixin, Base):
    __tablename__ = "business_income"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    date_received: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    recurrence_freq: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    recurrence_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Set when this income row was generated by an invoice being sent/paid — the
    # single source of truth for that invoice's income, so a paid invoice is
    # never double-counted alongside a separate manual income entry (see
    # app/routes/invoices.py: _get_or_create_invoice_income).
    invoice_id: Mapped[Optional[int]] = mapped_column(ForeignKey("invoices.id"), nullable=True, index=True)

    user: Mapped["User"] = relationship(back_populates="business_income")


class BusinessExpense(TimestampMixin, Base):
    __tablename__ = "business_expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    date_incurred: Mapped[date] = mapped_column(Date, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_allowable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Dual-purpose / HMRC simplified expenses fields
    business_use_percent: Mapped[int] = mapped_column(Integer, default=100, nullable=False, server_default='100')
    expense_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)       # null|mileage|home_office_flat|home_office_actual|percentage
    home_office_hours_band: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 25_50|51_100|101_plus
    business_miles: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    vehicle_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)          # car_van|motorcycle|bicycle
    recurrence_freq: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    recurrence_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    user: Mapped["User"] = relationship(back_populates="business_expenses")
