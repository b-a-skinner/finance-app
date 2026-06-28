"""
Unit tests for the tax calculator service.
All fixtures use types.SimpleNamespace so no database or SQLAlchemy is needed.
"""
from types import SimpleNamespace

import pytest

from app.services.tax_calculator import (
    TakeHomeBreakdown,
    calculate_income_tax,
    calculate_national_insurance,
    calculate_pension_contribution,
    calculate_student_loan_repayment,
    calculate_take_home_pay,
)


# ---------------------------------------------------------------------------
# Shared fixtures — 2026/27 UK figures
# ---------------------------------------------------------------------------

@pytest.fixture
def cfg():
    """2026/27 UK tax configuration."""
    return SimpleNamespace(
        personal_allowance=12_570,
        basic_rate_threshold=50_270,
        basic_rate_pct=20,
        higher_rate_threshold=125_140,
        higher_rate_pct=40,
        additional_rate_pct=45,
        ni_primary_threshold=12_584,
        ni_upper_threshold=50_284,
        ni_main_rate_pct=8,
        ni_upper_rate_pct=2,
        pension_qualifying_lower=6_240,
        pension_qualifying_upper=50_270,
    )


@pytest.fixture
def plan2():
    return SimpleNamespace(plan_name="Plan 2", threshold=29_385, repayment_rate_pct=9)


@pytest.fixture
def postgrad():
    return SimpleNamespace(plan_name="Postgraduate", threshold=21_000, repayment_rate_pct=6)


# ---------------------------------------------------------------------------
# calculate_income_tax
# ---------------------------------------------------------------------------

class TestIncomeTax:
    def test_below_personal_allowance(self, cfg):
        assert calculate_income_tax(10_000, cfg) == 0.0

    def test_at_personal_allowance_boundary(self, cfg):
        # Exactly at the PA — no taxable income
        assert calculate_income_tax(12_570, cfg) == 0.0

    def test_basic_rate_band(self, cfg):
        # (30_000 - 12_570) * 20% = 17_430 * 0.20 = 3_486.00
        assert calculate_income_tax(30_000, cfg) == 3_486.0

    def test_higher_rate_band(self, cfg):
        # basic:  (50_270 - 12_570) * 20% = 37_700 * 0.20 = 7_540.00
        # higher: (70_000 - 50_270) * 40% = 19_730 * 0.40 = 7_892.00
        assert calculate_income_tax(70_000, cfg) == 15_432.0

    def test_taper_zone_partial(self, cfg):
        # £110,000: effective_pa = 12_570 - (110_000 - 100_000) / 2 = 7_570
        # basic:  (50_270 - 7_570) * 20% = 42_700 * 0.20 = 8_540.00
        # higher: (110_000 - 50_270) * 40% = 59_730 * 0.40 = 23_892.00
        assert calculate_income_tax(110_000, cfg) == 32_432.0

    def test_taper_zone_fully_eliminates_allowance(self, cfg):
        # At £125,140 the PA is exactly zero: 12_570 - (125_140 - 100_000) / 2 = 0
        # basic:  50_270 * 20% = 10_054.00
        # higher: (125_140 - 50_270) * 40% = 74_870 * 0.40 = 29_948.00
        assert calculate_income_tax(125_140, cfg) == 40_002.0

    def test_additional_rate_band(self, cfg):
        # £150,000: PA = 0 (past taper)
        # basic:      50_270 * 20% = 10_054.00
        # higher:    (125_140 - 50_270) * 40% = 74_870 * 0.40 = 29_948.00
        # additional: (150_000 - 125_140) * 45% = 24_860 * 0.45 = 11_187.00
        assert calculate_income_tax(150_000, cfg) == 51_189.0

    def test_taper_starts_at_exactly_100k(self, cfg):
        # At exactly £100,000 no taper has occurred yet — full PA applies
        # basic:  (50_270 - 12_570) * 20% = 7_540.00
        # higher: (100_000 - 50_270) * 40% = 49_730 * 0.40 = 19_892.00
        assert calculate_income_tax(100_000, cfg) == 27_432.0


# ---------------------------------------------------------------------------
# calculate_national_insurance
# ---------------------------------------------------------------------------

class TestNationalInsurance:
    def test_below_primary_threshold(self, cfg):
        assert calculate_national_insurance(10_000, cfg) == 0.0

    def test_at_primary_threshold(self, cfg):
        assert calculate_national_insurance(12_584, cfg) == 0.0

    def test_basic_rate_band(self, cfg):
        # (30_000 - 12_584) * 8% = 17_416 * 0.08 = 1_393.28
        assert calculate_national_insurance(30_000, cfg) == 1_393.28

    def test_higher_rate_band(self, cfg):
        # main:  (50_284 - 12_584) * 8% = 37_700 * 0.08 = 3_016.00
        # upper: (70_000 - 50_284) * 2% = 19_716 * 0.02 = 394.32
        assert calculate_national_insurance(70_000, cfg) == 3_410.32

    def test_taper_zone_ni_unaffected_by_pa_taper(self, cfg):
        # NI ignores the income tax PA taper — same bands apply
        # main:  (50_284 - 12_584) * 8% = 3_016.00
        # upper: (110_000 - 50_284) * 2% = 59_716 * 0.02 = 1_194.32
        assert calculate_national_insurance(110_000, cfg) == 4_210.32


# ---------------------------------------------------------------------------
# calculate_student_loan_repayment
# ---------------------------------------------------------------------------

class TestStudentLoanRepayment:
    def test_below_threshold_no_repayment(self, plan2):
        assert calculate_student_loan_repayment(20_000, [plan2]) == 0.0

    def test_at_threshold_boundary(self, plan2):
        assert calculate_student_loan_repayment(29_385, [plan2]) == 0.0

    def test_single_plan(self, plan2):
        # (35_000 - 29_385) * 9% = 5_615 * 0.09 = 505.35
        assert calculate_student_loan_repayment(35_000, [plan2]) == 505.35

    def test_multiple_plans_calculated_independently(self, plan2, postgrad):
        # Plan 2:    (35_000 - 29_385) * 9% = 505.35
        # Postgrad:  (35_000 - 21_000) * 6% = 14_000 * 0.06 = 840.00
        assert calculate_student_loan_repayment(35_000, [plan2, postgrad]) == 1_345.35

    def test_no_plans(self):
        assert calculate_student_loan_repayment(80_000, []) == 0.0


# ---------------------------------------------------------------------------
# calculate_pension_contribution
# ---------------------------------------------------------------------------

class TestPensionContribution:
    def test_below_qualifying_lower_no_contribution(self, cfg):
        employee, employer = calculate_pension_contribution(5_000, 5, 3, cfg)
        assert employee == 0.0
        assert employer == 0.0

    def test_at_qualifying_lower_boundary(self, cfg):
        # Exactly at £6,240 — qualifying earnings = 0
        employee, employer = calculate_pension_contribution(6_240, 5, 3, cfg)
        assert employee == 0.0
        assert employer == 0.0

    def test_mid_qualifying_band(self, cfg):
        # qualifying = 30_000 - 6_240 = 23_760
        # employee (5%): 23_760 * 0.05 = 1_188.00
        # employer (3%): 23_760 * 0.03 = 712.80
        employee, employer = calculate_pension_contribution(30_000, 5, 3, cfg)
        assert employee == 1_188.0
        assert employer == 712.8

    def test_capped_at_qualifying_upper(self, cfg):
        # £80,000: qualifying = 50_270 - 6_240 = 44_030 (capped at qualifying_upper)
        # employee (5%): 44_030 * 0.05 = 2_201.50
        # employer (3%): 44_030 * 0.03 = 1_320.90
        employee, employer = calculate_pension_contribution(80_000, 5, 3, cfg)
        assert employee == 2_201.5
        assert employer == 1_320.9

    def test_zero_contribution_rates(self, cfg):
        employee, employer = calculate_pension_contribution(30_000, 0, 0, cfg)
        assert employee == 0.0
        assert employer == 0.0


# ---------------------------------------------------------------------------
# calculate_take_home_pay (integration)
# ---------------------------------------------------------------------------

class TestTakeHomePay:
    def test_basic_rate_no_loans(self, cfg):
        result = calculate_take_home_pay(30_000, cfg, [], 5.0, 3.0)
        assert isinstance(result, TakeHomeBreakdown)
        assert result.gross_annual == 30_000
        assert result.income_tax == 3_486.0
        assert result.national_insurance == 1_393.28
        assert result.student_loan == 0.0
        assert result.pension_employee == 1_188.0
        assert result.pension_employer == 712.8
        # net = 30_000 - 3_486 - 1_393.28 - 0 - 1_188 = 23_932.72
        assert result.net_annual == 23_932.72
        assert result.net_monthly == round(23_932.72 / 12, 2)

    def test_taper_zone_with_student_loan(self, cfg, plan2):
        # £110,000: complex case combining PA taper + higher NI + loan repayment
        result = calculate_take_home_pay(110_000, cfg, [plan2], 5.0, 3.0)
        assert result.income_tax == 32_432.0
        assert result.national_insurance == 4_210.32
        # (110_000 - 29_385) * 9% = 80_615 * 0.09 = 7_255.35
        assert result.student_loan == 7_255.35
        # pension: qualifying = 50_270 - 6_240 = 44_030 (capped); 44_030 * 5% = 2_201.50
        assert result.pension_employee == 2_201.5

    def test_below_all_thresholds_no_deductions(self, cfg):
        result = calculate_take_home_pay(10_000, cfg, [], 0.0, 0.0)
        assert result.income_tax == 0.0
        assert result.national_insurance == 0.0
        assert result.student_loan == 0.0
        assert result.pension_employee == 0.0
        assert result.net_annual == 10_000.0
        assert result.net_monthly == round(10_000 / 12, 2)

    def test_net_monthly_is_net_annual_divided_by_12(self, cfg, plan2):
        result = calculate_take_home_pay(55_000, cfg, [plan2], 4.0, 3.0)
        assert result.net_monthly == round(result.net_annual / 12, 2)
