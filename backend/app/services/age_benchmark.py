"""
Age-based, regional, and occupation salary benchmark comparison service.
Pure functions — no database access. Accept pre-fetched benchmark rows so
they can be unit-tested with plain SimpleNamespace objects.
"""
from dataclasses import dataclass
from datetime import date
from typing import Protocol

from app.services.postcode_lookup import get_region_from_postcode


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


# ── Regional benchmark types ─────────────────────────────────────────────────

class RegionalBenchmark(Protocol):
    region_name: str
    median_annual_salary: float
    source: str
    source_notes: str


@dataclass
class RegionalComparisonResult:
    region: str | None                         # matched region name, or None
    median_annual_salary_for_region: float | None
    salary_vs_region_pct: float | None
    region_source: str | None
    region_source_notes: str | None
    is_london: bool                            # drives the London caveat note


# ── Occupation benchmark types ────────────────────────────────────────────────

class OccupationBenchmark(Protocol):
    soc_code: str
    soc_level: int
    soc_group_description: str
    median_annual_salary: float
    source: str
    source_notes: str


@dataclass
class OccupationComparisonResult:
    occupation_soc_group_description: str | None
    occupation_median_annual_salary: float | None
    salary_vs_occupation_pct: float | None
    occupation_match_level: int | None          # 1 or 2, or None when no match
    occupation_source: str | None
    occupation_source_notes: str | None


# ── Age calculation helpers ───────────────────────────────────────────────────

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


def get_regional_comparison(
    postcode_outward: str | None,
    current_annual_salary: float,
    regional_benchmarks,   # iterable of RegionalBenchmark-like objects
) -> RegionalComparisonResult:
    """
    Compare a user's annual salary against the ONS regional median.

    When postcode_outward is None, returns all nulls — the caller should
    prompt the user to add a postcode rather than showing the comparison.
    When the postcode is set but unrecognised, falls back to the 'UK overall'
    row so the user still gets a meaningful comparison.
    """
    if postcode_outward is None:
        return RegionalComparisonResult(
            region=None, median_annual_salary_for_region=None,
            salary_vs_region_pct=None, region_source=None,
            region_source_notes=None, is_london=False,
        )

    region = get_region_from_postcode(postcode_outward)

    matched: RegionalBenchmark | None = None
    fallback: RegionalBenchmark | None = None
    for b in regional_benchmarks:
        if b.region_name == "UK overall":
            fallback = b
        if region and b.region_name == region:
            matched = b

    benchmark = matched or fallback

    if benchmark is None:
        return RegionalComparisonResult(
            region=region, median_annual_salary_for_region=None,
            salary_vs_region_pct=None, region_source=None,
            region_source_notes=None, is_london=region == "London",
        )

    median = benchmark.median_annual_salary
    pct = round(current_annual_salary / median * 100, 1) if median > 0 else None

    return RegionalComparisonResult(
        region=region,
        median_annual_salary_for_region=median,
        salary_vs_region_pct=pct,
        region_source=benchmark.source,
        region_source_notes=benchmark.source_notes,
        is_london=region == "London",
    )


def get_occupation_comparison(
    soc_code: str | None,
    current_annual_salary: float,
    occupation_benchmarks,   # iterable of OccupationBenchmark-like objects
) -> OccupationComparisonResult:
    """
    Compare a user's annual salary against the ONS occupation-group median.

    Matching strategy:
      1. Try 2-digit prefix of soc_code against soc_level=2 rows (preferred).
      2. Fall back to 1-digit prefix against soc_level=1 rows.
      3. If soc_code is None or no match found, return all nulls.
    """
    null_result = OccupationComparisonResult(
        occupation_soc_group_description=None,
        occupation_median_annual_salary=None,
        salary_vs_occupation_pct=None,
        occupation_match_level=None,
        occupation_source=None,
        occupation_source_notes=None,
    )

    if not soc_code:
        return null_result

    prefix2 = soc_code[:2] if len(soc_code) >= 2 else None
    prefix1 = soc_code[:1]

    level2_map: dict[str, OccupationBenchmark] = {}
    level1_map: dict[str, OccupationBenchmark] = {}
    for b in occupation_benchmarks:
        if b.soc_level == 2:
            level2_map[b.soc_code] = b
        elif b.soc_level == 1:
            level1_map[b.soc_code] = b

    matched = None
    match_level = None
    if prefix2 and prefix2 in level2_map:
        matched = level2_map[prefix2]
        match_level = 2
    elif prefix1 in level1_map:
        matched = level1_map[prefix1]
        match_level = 1

    if matched is None:
        return null_result

    median = matched.median_annual_salary
    pct = round(current_annual_salary / median * 100, 1) if median > 0 else None

    return OccupationComparisonResult(
        occupation_soc_group_description=matched.soc_group_description,
        occupation_median_annual_salary=median,
        salary_vs_occupation_pct=pct,
        occupation_match_level=match_level,
        occupation_source=matched.source,
        occupation_source_notes=matched.source_notes,
    )
