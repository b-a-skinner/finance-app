"""
Unit tests for the student loan projection service.
Pure Python — no database, no HTTP client needed.
"""
from datetime import date

import pytest

from app.services.student_loan_projection import (
    LoanProjectionResult,
    _add_months,
    calculate_loan_projection,
)

# ---------------------------------------------------------------------------
# Shared parameters — Plan 2, 2026/27 figures
# ---------------------------------------------------------------------------
PLAN2 = dict(
    plan_threshold=29_385.0,
    plan_repayment_rate_pct=9.0,
    plan_write_off_years=30,
)
GRADUATION_YEAR = 2020   # first_repay_date = 2021-04-06


# ---------------------------------------------------------------------------
# _add_months helper
# ---------------------------------------------------------------------------

class TestAddMonths:
    def test_same_year(self):
        assert _add_months(date(2021, 4, 6), 1) == date(2021, 5, 6)

    def test_year_rollover(self):
        assert _add_months(date(2021, 4, 6), 12) == date(2022, 4, 6)

    def test_thirty_years(self):
        assert _add_months(date(2021, 4, 6), 360) == date(2051, 4, 6)


# ---------------------------------------------------------------------------
# calculate_loan_projection
# ---------------------------------------------------------------------------

class TestHighEarnerPaidOff:
    """High salary, small balance → loan paid off well before write-off."""

    def setup_method(self):
        # £20k balance, 7.3% interest, £80k salary
        # Monthly repayment: (80000 - 29385) * 9% / 12 ≈ £379.61
        # Month-1 interest on £20k at 7.3%: ≈ £121.67 → net decrease ≈ £257.94/mo
        # Rough payoff: ~78 months (~6.5 years), well within the 30-year write-off
        self.result = calculate_loan_projection(
            balance=20_000.0,
            interest_rate=7.3,
            graduation_year=GRADUATION_YEAR,
            annual_salary=80_000.0,
            **PLAN2,
        )

    def test_outcome_is_paid_off(self):
        assert self.result.outcome == "paid_off"

    def test_payoff_date_is_set(self):
        assert self.result.payoff_date is not None

    def test_no_remaining_balance(self):
        assert self.result.remaining_balance_at_writeoff == 0.0

    def test_pays_off_in_under_ten_years(self):
        assert self.result.years_simulated < 10.0

    def test_first_repay_date(self):
        assert self.result.first_repay_date == date(2021, 4, 6)

    def test_write_off_date_is_thirty_years_later(self):
        assert self.result.write_off_date == date(2051, 4, 6)

    def test_payoff_date_before_writeoff(self):
        assert self.result.payoff_date < self.result.write_off_date

    def test_salary_assumption_recorded(self):
        assert self.result.annual_salary_assumption == 80_000.0


class TestTypicalPlan2WrittenOff:
    """
    Typical Plan 2 borrower on an average salary — the most common real-world
    outcome. Monthly repayments are dwarfed by accruing interest, so the loan
    grows throughout the 30-year period and is written off with a large balance.

    Context: the IFS estimates that around 70–80% of English graduates with Plan 2
    loans will not repay in full before write-off.
    """

    def setup_method(self):
        # £60k balance (typical post-2012 borrower total), 7.3% interest,
        # £30k salary (just above the £29,385 threshold).
        # Monthly repayment: (30000 - 29385) * 9% / 12 ≈ £4.61
        # Month-1 interest on £60k: ≈ £365  →  balance grows by ~£360/month
        self.result = calculate_loan_projection(
            balance=60_000.0,
            interest_rate=7.3,
            graduation_year=GRADUATION_YEAR,
            annual_salary=30_000.0,
            **PLAN2,
        )

    def test_outcome_is_written_off(self):
        assert self.result.outcome == "written_off"

    def test_payoff_date_is_none(self):
        assert self.result.payoff_date is None

    def test_balance_has_grown(self):
        # With near-zero repayments vs 7.3% interest, the balance grows substantially
        assert self.result.remaining_balance_at_writeoff > 60_000.0

    def test_years_simulated_equals_write_off_period(self):
        assert self.result.years_simulated == 30.0

    def test_write_off_date(self):
        assert self.result.write_off_date == date(2051, 4, 6)


class TestZeroSalaryBalanceOnlyGrows:
    """
    No income → no repayments → balance compounds purely on interest.
    Must result in written_off with a significantly larger remaining balance.
    """

    def setup_method(self):
        self.result = calculate_loan_projection(
            balance=10_000.0,
            interest_rate=5.0,
            graduation_year=GRADUATION_YEAR,
            annual_salary=0.0,
            **PLAN2,
        )

    def test_outcome_is_written_off(self):
        assert self.result.outcome == "written_off"

    def test_payoff_date_is_none(self):
        assert self.result.payoff_date is None

    def test_balance_grows_substantially(self):
        # 5% annual, 30 years, no repayments: ≈ £10k × (1.05/12)^360 ≈ £44.5k
        assert self.result.remaining_balance_at_writeoff > 40_000.0

    def test_salary_assumption_is_zero(self):
        assert self.result.annual_salary_assumption == 0.0


class TestDatesAndEdgeCases:
    def test_future_graduation_year(self):
        # Projection should still compute correctly for someone still studying
        result = calculate_loan_projection(
            balance=50_000.0,
            interest_rate=7.3,
            graduation_year=2027,
            annual_salary=35_000.0,
            **PLAN2,
        )
        assert result.first_repay_date == date(2028, 4, 6)
        assert result.write_off_date == date(2058, 4, 6)

    def test_plan5_40_year_writeoff(self):
        result = calculate_loan_projection(
            balance=50_000.0,
            interest_rate=7.3,
            graduation_year=GRADUATION_YEAR,
            plan_threshold=25_000.0,
            plan_repayment_rate_pct=9.0,
            plan_write_off_years=40,
            annual_salary=30_000.0,
        )
        assert result.write_off_date == date(2061, 4, 6)  # 2021 + 40
        assert result.years_simulated == 40.0

    def test_salary_below_threshold_means_no_repayments(self):
        # Salary < threshold → same as zero salary (no repayments)
        result_no_salary = calculate_loan_projection(
            balance=10_000.0, interest_rate=5.0, graduation_year=GRADUATION_YEAR,
            annual_salary=0.0, **PLAN2,
        )
        result_below_threshold = calculate_loan_projection(
            balance=10_000.0, interest_rate=5.0, graduation_year=GRADUATION_YEAR,
            annual_salary=20_000.0,  # below £29,385 threshold
            **PLAN2,
        )
        assert result_no_salary.remaining_balance_at_writeoff == result_below_threshold.remaining_balance_at_writeoff
