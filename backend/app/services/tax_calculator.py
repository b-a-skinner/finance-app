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


class BizTaxConfig(Protocol):
    """Sole trader NI config. Only called when all fields are confirmed non-None."""
    class4_lower_limit: float
    class4_upper_limit: float
    class4_main_rate: float
    class4_upper_rate: float
    class2_small_profits_threshold: float
    class2_weekly_rate: float


@dataclass
class SoleTraderTaxBreakdown:
    taxable_profit: float
    income_tax_on_profit: float
    class4_ni: float
    class2_status: str          # "covered" | "covered_no_class4" | "below_threshold"
    class2_due: float           # always 0 — Class 2 is auto-granted or voluntary only
    class2_voluntary_note: str | None
    total_set_aside: float
    effective_rate: float


@dataclass
class PoaBreakdown:
    poa_triggered: bool
    poa_instalment: float   # 50% of bill_lcy when triggered — both the January and July instalment amount
    balancing_payment: float
    january_total: float    # balancing_payment + poa_instalment
    july_total: float       # == poa_instalment


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


def calculate_sole_trader_tax(
    taxable_profit: float,
    tax_cfg: TaxConfig,
    biz_cfg: BizTaxConfig,
    starting_income: float = 0.0,
) -> SoleTraderTaxBreakdown:
    """
    Income tax + Class 4 NI + Class 2 position for a sole trader.

    Income tax is the marginal slice on [starting_income, starting_income + profit],
    computed as calculate_income_tax(starting_income + profit) − calculate_income_tax(starting_income).
    With the default starting_income=0 this equals income_tax(profit), but the difference
    form means passing a real starting_income later is a one-line change at the call site.

    All rates and thresholds come from config — none are hardcoded here.
    """
    income_tax_on_profit = round(
        calculate_income_tax(starting_income + taxable_profit, tax_cfg)
        - calculate_income_tax(starting_income, tax_cfg),
        2,
    )

    # Class 4 NI: slice calculation on profit
    class4 = 0.0
    if taxable_profit > biz_cfg.class4_lower_limit:
        main_slice = min(taxable_profit, biz_cfg.class4_upper_limit) - biz_cfg.class4_lower_limit
        class4 += main_slice * biz_cfg.class4_main_rate
    if taxable_profit > biz_cfg.class4_upper_limit:
        class4 += (taxable_profit - biz_cfg.class4_upper_limit) * biz_cfg.class4_upper_rate
    class4 = round(class4, 2)

    # Class 2 position
    class2_note: str | None = None
    if taxable_profit >= biz_cfg.class4_lower_limit:
        class2_status = "covered"
    elif taxable_profit >= biz_cfg.class2_small_profits_threshold:
        class2_status = "covered_no_class4"
    else:
        class2_status = "below_threshold"
        annual_voluntary = round(biz_cfg.class2_weekly_rate * 52, 2)
        class2_note = (
            f"Voluntary Class 2 contributions (£{biz_cfg.class2_weekly_rate:.2f}/week, "
            f"£{annual_voluntary:.2f}/year) could protect your State Pension record."
        )

    total_set_aside = round(income_tax_on_profit + class4, 2)
    effective_rate = round(total_set_aside / taxable_profit, 4) if taxable_profit > 0 else 0.0

    return SoleTraderTaxBreakdown(
        taxable_profit=taxable_profit,
        income_tax_on_profit=income_tax_on_profit,
        class4_ni=class4,
        class2_status=class2_status,
        class2_due=0.0,
        class2_voluntary_note=class2_note,
        total_set_aside=total_set_aside,
        effective_rate=effective_rate,
    )


def calculate_payments_on_account(
    bill_lcy: float,
    poa_threshold: float,
    bill_prior: float = 0.0,
    prior_poa_threshold: float | None = None,
) -> PoaBreakdown:
    """
    Payments on account (for the year after LCY) and balancing payment (for LCY),
    given LCY's finalised bill (income tax + Class 4 NI — Class 2 excluded by the
    caller before this is invoked).

    bill_prior defaults to 0.0, representing no prior year of trading — POAs
    derived from it are then £0 regardless of prior_poa_threshold. This derives
    POAs from the prior year's bill rather than tracking payments actually made,
    which is correct in the normal case (no payment tracking here).

    All thresholds are parameters — nothing is hardcoded, so a future change to
    HMRC's £1,000 de minimis is a config change, not a code change.
    """
    if prior_poa_threshold is None:
        prior_poa_threshold = poa_threshold

    poas_from_prior = bill_prior if bill_prior > prior_poa_threshold else 0.0
    balancing_payment = round(bill_lcy - poas_from_prior, 2)

    poa_triggered = bill_lcy > poa_threshold
    poa_instalment = round(bill_lcy * 0.5, 2) if poa_triggered else 0.0

    return PoaBreakdown(
        poa_triggered=poa_triggered,
        poa_instalment=poa_instalment,
        balancing_payment=balancing_payment,
        january_total=round(balancing_payment + poa_instalment, 2),
        july_total=poa_instalment,
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
