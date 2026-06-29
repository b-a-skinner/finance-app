"""
Age-based benchmark comparison service.
Pure function — no database access. Accepts pre-fetched benchmark rows so
it can be unit-tested with plain SimpleNamespace objects.
"""
from dataclasses import dataclass
from datetime import date
from typing import Protocol


class SalaryBand(Protocol):
    age_band: str
    min_age: int
    max_age: int | None
    median_monthly_salary: float
    source: str
    source_metric: str


class PensionBand(Protocol):
    age_band: str
    min_age: int
    max_age: int | None
    median_pension_pot: float | None
    source: str
    source_metric: str


@dataclass
class AgeComparisonResult:
    user_age: int | None
    # Salary
    salary_band_label: str | None
    median_monthly_salary: float | None
    salary_comparison_pct: float | None   # user salary as % of median
    salary_source: str | None
    salary_source_metric: str | None
    # Pension
    pension_band_label: str | None
    median_pension_pot: float | None       # None when band exists but data unavailable
    pension_comparison_pct: float | None
    pension_data_available: bool           # False when band found but median is null
    pension_source: str | None
    pension_source_metric: str | None


def _calculate_age(dob: date) -> int:
    today = date.today()
    age = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        age -= 1
    return age


def _find_band(age: int, benchmarks):
    """Return the first band whose [min_age, max_age] contains age."""
    for b in benchmarks:
        if b.min_age <= age and (b.max_age is None or age <= b.max_age):
            return b
    return None


def get_age_comparison(
    date_of_birth: date | None,
    current_monthly_salary: float,
    current_pension_pot: float,
    salary_benchmarks,   # iterable of SalaryBand-like objects
    pension_benchmarks,  # iterable of PensionBand-like objects
) -> AgeComparisonResult:
    """
    Compare a user's salary and pension pot against UK age-band medians.

    Returns nulls (not errors) when date_of_birth is missing or the age falls
    outside all defined bands. Pension bands may themselves have a null median
    (data not yet available) — pension_data_available distinguishes this from
    no band being found.
    """
    if date_of_birth is None:
        return AgeComparisonResult(
            user_age=None,
            salary_band_label=None, median_monthly_salary=None, salary_comparison_pct=None,
            salary_source=None, salary_source_metric=None,
            pension_band_label=None, median_pension_pot=None, pension_comparison_pct=None,
            pension_data_available=False, pension_source=None, pension_source_metric=None,
        )

    user_age = _calculate_age(date_of_birth)

    # ── Salary ──────────────────────────────────────────────────────────────
    salary_band = _find_band(user_age, salary_benchmarks)
    if salary_band:
        median_sal = salary_band.median_monthly_salary
        sal_pct = round(current_monthly_salary / median_sal * 100, 1) if median_sal > 0 else None
    else:
        median_sal = None
        sal_pct = None

    # ── Pension ─────────────────────────────────────────────────────────────
    pension_band = _find_band(user_age, pension_benchmarks)
    if pension_band:
        median_pen = pension_band.median_pension_pot  # may be None (data not available)
        pen_available = median_pen is not None
        if pen_available and median_pen > 0:
            pen_pct = round(current_pension_pot / median_pen * 100, 1)
        else:
            pen_pct = None
    else:
        median_pen = None
        pen_available = False
        pen_pct = None

    return AgeComparisonResult(
        user_age=user_age,
        salary_band_label=salary_band.age_band if salary_band else None,
        median_monthly_salary=median_sal,
        salary_comparison_pct=sal_pct,
        salary_source=salary_band.source if salary_band else None,
        salary_source_metric=salary_band.source_metric if salary_band else None,
        pension_band_label=pension_band.age_band if pension_band else None,
        median_pension_pot=median_pen,
        pension_comparison_pct=pen_pct,
        pension_data_available=pen_available,
        pension_source=pension_band.source if pension_band else None,
        pension_source_metric=pension_band.source_metric if pension_band else None,
    )
