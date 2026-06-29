from typing import Optional

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TaxYearConfig(Base):
    """UK tax parameters for a given tax year. Seed with real HMRC figures."""

    __tablename__ = "tax_year_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    tax_year: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)  # e.g. "2026/27"

    # Income tax bands (all amounts in GBP, annual)
    personal_allowance: Mapped[float] = mapped_column(Float, nullable=False)
    basic_rate_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    basic_rate_pct: Mapped[float] = mapped_column(Float, nullable=False)
    higher_rate_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    higher_rate_pct: Mapped[float] = mapped_column(Float, nullable=False)
    additional_rate_pct: Mapped[float] = mapped_column(Float, nullable=False)

    # National Insurance
    ni_primary_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    ni_upper_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    ni_main_rate_pct: Mapped[float] = mapped_column(Float, nullable=False)
    ni_upper_rate_pct: Mapped[float] = mapped_column(Float, nullable=False)

    # Auto-enrolment pension qualifying earnings band
    pension_qualifying_lower: Mapped[float] = mapped_column(Float, nullable=False)
    pension_qualifying_upper: Mapped[float] = mapped_column(Float, nullable=False)
    pension_min_total_pct: Mapped[float] = mapped_column(Float, nullable=False)
    pension_min_employer_pct: Mapped[float] = mapped_column(Float, nullable=False)


class StudentLoanPlanConfig(Base):
    """Repayment thresholds and rates per student loan plan per tax year."""

    __tablename__ = "student_loan_plan_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_name: Mapped[str] = mapped_column(String(50), nullable=False)   # e.g. "Plan 2"
    tax_year: Mapped[str] = mapped_column(String(10), nullable=False)    # e.g. "2026/27"
    threshold: Mapped[float] = mapped_column(Float, nullable=False)      # annual repayment threshold (GBP)
    repayment_rate_pct: Mapped[float] = mapped_column(Float, nullable=False)
    write_off_years: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
