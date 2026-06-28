from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    # Imported only for static analysis — avoids circular imports at runtime
    from app.models.finance import Debt, Expense, IncomeSource, PensionPot, SavingsGoal


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[str] = mapped_column(String(10), default="UK", nullable=False)

    income_sources: Mapped[list["IncomeSource"]] = relationship(back_populates="user")
    expenses: Mapped[list["Expense"]] = relationship(back_populates="user")
    debts: Mapped[list["Debt"]] = relationship(back_populates="user")
    savings_goals: Mapped[list["SavingsGoal"]] = relationship(back_populates="user")
    pension_pots: Mapped[list["PensionPot"]] = relationship(back_populates="user")
