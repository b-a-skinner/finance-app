from typing import Optional

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BusinessTaxConfig(Base):
    """HMRC mileage and simplified expenses rates by tax year."""

    __tablename__ = "business_tax_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    tax_year: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)

    # Home office flat rates — £/month (HMRC simplified expenses)
    home_office_band_25_50: Mapped[float] = mapped_column(Float, nullable=False)    # 25–50 h/month
    home_office_band_51_100: Mapped[float] = mapped_column(Float, nullable=False)   # 51–100 h/month
    home_office_band_101_plus: Mapped[float] = mapped_column(Float, nullable=False) # 101+ h/month

    # Mileage rates — £/mile
    mileage_car_van_first: Mapped[float] = mapped_column(Float, nullable=False)   # first N miles
    mileage_car_van_over: Mapped[float] = mapped_column(Float, nullable=False)    # above threshold
    mileage_motorcycle: Mapped[float] = mapped_column(Float, nullable=False)
    mileage_bicycle: Mapped[float] = mapped_column(Float, nullable=False)
    mileage_threshold: Mapped[int] = mapped_column(Integer, nullable=False)

    # Class 4 NI rates — self-employed (added 2026/27)
    class4_lower_limit: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    class4_upper_limit: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    class4_main_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    class4_upper_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Class 2 NI position
    class2_small_profits_threshold: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    class2_weekly_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    source_note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


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


class AgeBenchmarkSalary(Base):
    """UK median monthly salary by age band (ONS)."""

    __tablename__ = "age_benchmark_salary"

    id: Mapped[int] = mapped_column(primary_key=True)
    age_band: Mapped[str] = mapped_column(String(20), nullable=False)     # e.g. "25-34"
    min_age: Mapped[int] = mapped_column(Integer, nullable=False)
    max_age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # null = open-ended top band
    median_monthly_salary: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    source_metric: Mapped[str] = mapped_column(String(255), nullable=False)


class AgeBenchmarkPension(Base):
    """UK median pension pot by age band (ONS Wealth and Assets Survey).
    median_pension_pot is nullable — some bands don't yet have confirmed figures.
    """

    __tablename__ = "age_benchmark_pension"

    id: Mapped[int] = mapped_column(primary_key=True)
    age_band: Mapped[str] = mapped_column(String(20), nullable=False)
    min_age: Mapped[int] = mapped_column(Integer, nullable=False)
    max_age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    median_pension_pot: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    source_metric: Mapped[str] = mapped_column(String(255), nullable=False)


class RegionalSalaryBenchmark(Base):
    """UK median annual salary by region (ONS ASHE).
    Includes a 'UK overall' row used as fallback when region is unrecognised.
    region_name values must match those returned by get_region_from_postcode().
    """

    __tablename__ = "regional_salary_benchmark"

    id: Mapped[int] = mapped_column(primary_key=True)
    region_name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "London", "UK overall"
    median_annual_salary: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    source_notes: Mapped[str] = mapped_column(String(255), nullable=False)


class OccupationCode(Base):
    """SOC 2020 occupation reference data for the occupation combobox."""

    __tablename__ = "occupation_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    soc_code: Mapped[str] = mapped_column(String(10), nullable=False)
    soc_group: Mapped[str] = mapped_column(String(100), nullable=False)


class OccupationSalaryBenchmark(Base):
    """UK median annual salary by SOC group (ONS ASHE 2025).

    soc_level=2 rows cover 2-digit SOC sub-major groups (preferred match).
    soc_level=1 rows cover 1-digit SOC major groups (fallback).
    soc_code stores the 1- or 2-digit code as a string.
    """

    __tablename__ = "occupation_salary_benchmark"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    soc_code: Mapped[str] = mapped_column(String(10), nullable=False)
    soc_level: Mapped[int] = mapped_column(Integer, nullable=False)   # 1 or 2
    soc_group_description: Mapped[str] = mapped_column(String(255), nullable=False)
    median_annual_salary: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    source_notes: Mapped[str] = mapped_column(String(255), nullable=False)
