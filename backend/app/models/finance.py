import enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Enum as SAEnum, Float, ForeignKey, Integer, String
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
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["User"] = relationship(back_populates="savings_goals")


class PensionPot(TimestampMixin, Base):
    __tablename__ = "pension_pots"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
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
