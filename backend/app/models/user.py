from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    # Imported only for static analysis — avoids circular imports at runtime
    from app.models.finance import Asset, BusinessExpense, BusinessIncome, Debt, Expense, IncomeSource, PensionPot, SavingsGoal


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[str] = mapped_column(String(10), default="UK", nullable=False)

    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    occupation: Mapped[str | None] = mapped_column(String(255), nullable=True)
    postcode_outward: Mapped[str | None] = mapped_column(String(10), nullable=True)

    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    onboarding_dismiss_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    financial_goals: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_onboarding_step: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    income_sources: Mapped[list["IncomeSource"]] = relationship(back_populates="user")
    expenses: Mapped[list["Expense"]] = relationship(back_populates="user")
    debts: Mapped[list["Debt"]] = relationship(back_populates="user")
    savings_goals: Mapped[list["SavingsGoal"]] = relationship(back_populates="user")
    pension_pots: Mapped[list["PensionPot"]] = relationship(back_populates="user")
    assets: Mapped[list["Asset"]] = relationship(back_populates="user")
    business_income: Mapped[list["BusinessIncome"]] = relationship(back_populates="user")
    business_expenses: Mapped[list["BusinessExpense"]] = relationship(back_populates="user")
