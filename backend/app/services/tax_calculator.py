"""
Pure financial calculation functions.
No database access — inputs are plain Python values, outputs are plain Python values.
SQLAlchemy model instances satisfy the Protocols below because Protocol matching is structural.
"""
from dataclasses import dataclass
from typing import Protocol


# ---------------------------------------------------------------------------
# Protocols — define only the attributes each function actually needs.
# Keeps tests simple: pass a types.SimpleNamespace, no SQLAlchemy required.
# ---------------------------------------------------------------------------

class TaxConfig(Protocol):
    personal_allowance: float
    basic_rate_threshold: float
    basic_rate_pct: float
    higher_rate_threshold: float
    higher_rate_pct: float
    additional_rate_pct: float
    ni_primary_threshold: float
    ni_upper_threshold: float
    ni_main_rate_pct: float
    ni_upper_rate_pct: float
    pension_qualifying_lower: float
    pension_qualifying_upper: float


class LoanPlan(Protocol):
    threshold: float
    repayment_rate_pct: float


@dataclass
class TakeHomeBreakdown:
    gross_annual: float
    income_tax: float
    national_insurance: float
    student_loan: float
    pension_employee: float
    pension_employer: float
    net_annual: float
    net_monthly: float


# ---------------------------------------------------------------------------
# PA taper constant — not in TaxYearConfig because it is fixed in statute
# ---------------------------------------------------------------------------
_TAPER_START = 100_000.0


def calculate_income_tax(gross: float, cfg: TaxConfig) -> float:
    """
    UK income tax with personal allowance taper.

    The personal allowance (PA) is reduced £1 for every £2 earned above £100,000.
    At £125,140 the PA reaches £0 and all income in bands becomes taxable.
    Only the slice of income within each band is taxed at that band's rate.
    """
    # Reduce personal allowance for high earners
    effective_pa = cfg.personal_allowance
    if gross > _TAPER_START:
        effective_pa = max(0.0, cfg.personal_allowance - (gross - _TAPER_START) / 2)

    tax = 0.0

    # Basic rate: effective_pa → basic_rate_threshold
    if gross > effective_pa:
        basic_taxable = min(gross, cfg.basic_rate_threshold) - effective_pa
        tax += max(0.0, basic_taxable) * (cfg.basic_rate_pct / 100)

    # Higher rate: basic_rate_threshold → higher_rate_threshold
    if gross > cfg.basic_rate_threshold:
        higher_taxable = min(gross, cfg.higher_rate_threshold) - cfg.basic_rate_threshold
        tax += higher_taxable * (cfg.higher_rate_pct / 100)

    # Additional rate: above higher_rate_threshold
    if gross > cfg.higher_rate_threshold:
        tax += (gross - cfg.higher_rate_threshold) * (cfg.additional_rate_pct / 100)

    return round(tax, 2)


def calculate_national_insurance(gross: float, cfg: TaxConfig) -> float:
    """
    Employee Class 1 NI contributions.
    Main rate applies between primary and upper earnings thresholds; upper rate above that.
    NI is not affected by the income tax personal allowance taper.
    """
    ni = 0.0

    # Main rate: primary_threshold → upper_threshold
    if gross > cfg.ni_primary_threshold:
        main_earnings = min(gross, cfg.ni_upper_threshold) - cfg.ni_primary_threshold
        ni += main_earnings * (cfg.ni_main_rate_pct / 100)

    # Upper rate: above upper_threshold
    if gross > cfg.ni_upper_threshold:
        ni += (gross - cfg.ni_upper_threshold) * (cfg.ni_upper_rate_pct / 100)

    return round(ni, 2)


def calculate_student_loan_repayment(gross: float, plans: list) -> float:
    """
    Each plan is calculated independently against its own threshold and rate, then summed.
    A borrower can hold multiple concurrent plans (e.g. Plan 2 + Postgraduate).
    """
    total = 0.0
    for plan in plans:
        if gross > plan.threshold:
            total += (gross - plan.threshold) * (plan.repayment_rate_pct / 100)
    return round(total, 2)


def calculate_pension_contribution(
    gross: float,
    employee_pct: float,
    employer_pct: float,
    cfg: TaxConfig,
) -> tuple[float, float]:
    """
    Auto-enrolment contributions apply only to qualifying earnings —
    the slice of salary between pension_qualifying_lower and pension_qualifying_upper.
    Returns (employee_contribution, employer_contribution).
    Employer contributions are not deducted from the employee's take-home pay.
    """
    qualifying = max(
        0.0,
        min(gross, cfg.pension_qualifying_upper) - cfg.pension_qualifying_lower,
    )
    return (
        round(qualifying * employee_pct / 100, 2),
        round(qualifying * employer_pct / 100, 2),
    )


def calculate_take_home_pay(
    gross: float,
    tax_config: TaxConfig,
    student_loan_plans: list,
    employee_pension_pct: float = 0.0,
    employer_pension_pct: float = 0.0,
) -> TakeHomeBreakdown:
    """Orchestrates all deductions and returns a full annual and monthly take-home breakdown."""
    income_tax = calculate_income_tax(gross, tax_config)
    ni = calculate_national_insurance(gross, tax_config)
    student_loan = calculate_student_loan_repayment(gross, student_loan_plans)
    pension_employee, pension_employer = calculate_pension_contribution(
        gross, employee_pension_pct, employer_pension_pct, tax_config
    )
    net_annual = round(gross - income_tax - ni - student_loan - pension_employee, 2)
    return TakeHomeBreakdown(
        gross_annual=gross,
        income_tax=income_tax,
        national_insurance=ni,
        student_loan=student_loan,
        pension_employee=pension_employee,
        pension_employer=pension_employer,
        net_annual=net_annual,
        net_monthly=round(net_annual / 12, 2),
    )
