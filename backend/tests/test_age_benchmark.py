"""
Unit and integration tests for the age benchmark comparison feature.
Pure unit tests use SimpleNamespace — no DB required.
"""
from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from app.services.age_benchmark import AgeComparisonResult, _calculate_age, get_age_comparison, get_regional_comparison

# ---------------------------------------------------------------------------
# Shared fixtures — mirrors the seeded benchmark data
# ---------------------------------------------------------------------------

SAL_SOURCE = "ONS, May 2026"
SAL_METRIC = "all employees, median monthly pay before tax"
PEN_SOURCE = "ONS Wealth and Assets Survey"
PEN_METRIC = "median pension wealth, individual"


def _sal(age_band, min_age, max_age, median):
    return SimpleNamespace(
        age_band=age_band, min_age=min_age, max_age=max_age,
        median_monthly_salary=median, source=SAL_SOURCE, source_metric=SAL_METRIC,
    )


def _pen(age_band, min_age, max_age, median):
    return SimpleNamespace(
        age_band=age_band, min_age=min_age, max_age=max_age,
        median_pension_pot=median, source=PEN_SOURCE, source_metric=PEN_METRIC,
    )


@pytest.fixture
def salary_bands():
    return [
        _sal("18-24", 18, 24, 1830),
        _sal("25-34", 25, 34, 2820),
        _sal("35-49", 35, 49, 3062),
        _sal("50-64", 50, 64, 2698),
        _sal("65+",   65, None, 1582),
    ]


@pytest.fixture
def pension_bands():
    return [
        _pen("Under 25", 0,  24, 5500),
        _pen("25-34",    25, 34, 18800),
        _pen("35-44",    35, 44, 39500),
        _pen("45-54",    45, 54, None),    # data not yet available
        _pen("55-64",    55, 64, None),    # data not yet available
        _pen("65-74",    65, 74, 145900),
    ]


# ---------------------------------------------------------------------------
# _calculate_age
# ---------------------------------------------------------------------------

class TestCalculateAge:
    def test_birthday_in_past_this_year(self):
        # Birthday was earlier this year → age is already incremented
        today = date.today()
        dob = date(today.year - 30, today.month, today.day) - timedelta(days=1)
        assert _calculate_age(dob) == 30

    def test_birthday_today(self):
        today = date.today()
        dob = date(today.year - 25, today.month, today.day)
        assert _calculate_age(dob) == 25

    def test_birthday_tomorrow_not_yet(self):
        # Birthday is tomorrow → haven't turned that age yet
        today = date.today()
        tomorrow_dob = date(today.year - 32, today.month, today.day) + timedelta(days=1)
        assert _calculate_age(tomorrow_dob) == 31

    def test_known_dob(self):
        # 1990-01-01; today is 2026-06-29 → 36
        assert _calculate_age(date(1990, 1, 1)) == 36

    def test_young_person(self):
        assert _calculate_age(date(2005, 1, 1)) == 21


# ---------------------------------------------------------------------------
# get_age_comparison — no date_of_birth
# ---------------------------------------------------------------------------

class TestNoDob:
    def test_all_fields_null_when_no_dob(self, salary_bands, pension_bands):
        result = get_age_comparison(None, 3000, 20000, salary_bands, pension_bands)
        assert result.user_age is None
        assert result.salary_band_label is None
        assert result.median_monthly_salary is None
        assert result.salary_comparison_pct is None
        assert result.pension_band_label is None
        assert result.median_pension_pot is None
        assert result.pension_comparison_pct is None
        assert result.pension_data_available is False


# ---------------------------------------------------------------------------
# Band matching — salary
# ---------------------------------------------------------------------------

class TestSalaryBandMatching:
    def _run(self, age, salary_bands, pension_bands):
        dob = date(date.today().year - age, 1, 1)
        return get_age_comparison(dob, 3000, 0, salary_bands, pension_bands)

    def test_age_18_matches_18_24(self, salary_bands, pension_bands):
        result = self._run(18, salary_bands, pension_bands)
        assert result.salary_band_label == "18-24"
        assert result.median_monthly_salary == 1830

    def test_age_24_still_in_18_24(self, salary_bands, pension_bands):
        result = self._run(24, salary_bands, pension_bands)
        assert result.salary_band_label == "18-24"

    def test_age_25_moves_to_25_34(self, salary_bands, pension_bands):
        result = self._run(25, salary_bands, pension_bands)
        assert result.salary_band_label == "25-34"
        assert result.median_monthly_salary == 2820

    def test_age_34_still_in_25_34(self, salary_bands, pension_bands):
        result = self._run(34, salary_bands, pension_bands)
        assert result.salary_band_label == "25-34"

    def test_age_35_moves_to_35_49(self, salary_bands, pension_bands):
        result = self._run(35, salary_bands, pension_bands)
        assert result.salary_band_label == "35-49"

    def test_age_65_open_ended_band(self, salary_bands, pension_bands):
        result = self._run(65, salary_bands, pension_bands)
        assert result.salary_band_label == "65+"
        assert result.median_monthly_salary == 1582

    def test_age_90_still_in_65_plus(self, salary_bands, pension_bands):
        result = self._run(90, salary_bands, pension_bands)
        assert result.salary_band_label == "65+"

    def test_age_below_all_bands_returns_null(self, salary_bands, pension_bands):
        # Under 18 — no salary band defined
        result = self._run(17, salary_bands, pension_bands)
        assert result.salary_band_label is None
        assert result.salary_comparison_pct is None


# ---------------------------------------------------------------------------
# Band matching — pension
# ---------------------------------------------------------------------------

class TestPensionBandMatching:
    def _run(self, age, salary_bands, pension_bands, pension_pot=10000):
        dob = date(date.today().year - age, 1, 1)
        return get_age_comparison(dob, 3000, pension_pot, salary_bands, pension_bands)

    def test_age_24_matches_under_25(self, salary_bands, pension_bands):
        result = self._run(24, salary_bands, pension_bands)
        assert result.pension_band_label == "Under 25"
        assert result.median_pension_pot == 5500
        assert result.pension_data_available is True

    def test_age_45_band_found_but_no_data(self, salary_bands, pension_bands):
        result = self._run(45, salary_bands, pension_bands)
        assert result.pension_band_label == "45-54"
        assert result.median_pension_pot is None
        assert result.pension_data_available is False
        assert result.pension_comparison_pct is None

    def test_age_55_band_found_but_no_data(self, salary_bands, pension_bands):
        result = self._run(55, salary_bands, pension_bands)
        assert result.pension_band_label == "55-64"
        assert result.pension_data_available is False

    def test_age_65_matches_65_74(self, salary_bands, pension_bands):
        result = self._run(65, salary_bands, pension_bands)
        assert result.pension_band_label == "65-74"
        assert result.median_pension_pot == 145900
        assert result.pension_data_available is True

    def test_age_75_above_all_pension_bands(self, salary_bands, pension_bands):
        # Age 75 is above the top pension band (65-74)
        result = self._run(75, salary_bands, pension_bands)
        assert result.pension_band_label is None
        assert result.pension_data_available is False


# ---------------------------------------------------------------------------
# Comparison percentage
# ---------------------------------------------------------------------------

class TestComparisonPct:
    def _result_for_age_30(self, salary, pension_pot, salary_bands, pension_bands):
        dob = date(date.today().year - 30, 1, 1)
        return get_age_comparison(dob, salary, pension_pot, salary_bands, pension_bands)

    def test_salary_above_median(self, salary_bands, pension_bands):
        # Age 30 → 25-34 band, median £2,820. Salary £5,640 = 200% of median
        result = self._result_for_age_30(5640, 0, salary_bands, pension_bands)
        assert result.salary_comparison_pct == 200.0

    def test_salary_at_median(self, salary_bands, pension_bands):
        result = self._result_for_age_30(2820, 0, salary_bands, pension_bands)
        assert result.salary_comparison_pct == 100.0

    def test_salary_below_median(self, salary_bands, pension_bands):
        # £1,410 = 50% of £2,820
        result = self._result_for_age_30(1410, 0, salary_bands, pension_bands)
        assert result.salary_comparison_pct == 50.0

    def test_pension_at_median(self, salary_bands, pension_bands):
        # Age 30 → 25-34 band, median £18,800
        result = self._result_for_age_30(3000, 18800, salary_bands, pension_bands)
        assert result.pension_comparison_pct == 100.0

    def test_pension_above_median(self, salary_bands, pension_bands):
        result = self._result_for_age_30(3000, 37600, salary_bands, pension_bands)
        assert result.pension_comparison_pct == 200.0

    def test_zero_salary_gives_zero_pct(self, salary_bands, pension_bands):
        result = self._result_for_age_30(0, 10000, salary_bands, pension_bands)
        assert result.salary_comparison_pct == 0.0

    def test_comparison_rounds_to_one_decimal(self, salary_bands, pension_bands):
        # £3000 / £2820 * 100 = 106.382... → 106.4
        result = self._result_for_age_30(3000, 0, salary_bands, pension_bands)
        assert result.salary_comparison_pct == 106.4

    def test_source_fields_populated(self, salary_bands, pension_bands):
        result = self._result_for_age_30(3000, 20000, salary_bands, pension_bands)
        assert result.salary_source == SAL_SOURCE
        assert result.salary_source_metric == SAL_METRIC
        assert result.pension_source == PEN_SOURCE
        assert result.pension_source_metric == PEN_METRIC


# ---------------------------------------------------------------------------
# Integration test — /api/profile/comparison endpoint
# ---------------------------------------------------------------------------

REGISTER = "/api/auth/register"
LOGIN = "/api/auth/login"
_ALICE = {"email": "alice@example.com", "password": "s3cur3!"}


def _auth_header(client):
    token = client.post(LOGIN, data={"username": _ALICE["email"], "password": _ALICE["password"]}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _seed_benchmarks(db):
    from app.models import AgeBenchmarkSalary, AgeBenchmarkPension
    _s = "ONS, May 2026"
    _sm = "all employees, median monthly pay before tax"
    _p = "ONS Wealth and Assets Survey"
    _pm = "median pension wealth, individual"
    db.add_all([
        AgeBenchmarkSalary(age_band="18-24", min_age=18, max_age=24,  median_monthly_salary=1830, source=_s, source_metric=_sm),
        AgeBenchmarkSalary(age_band="25-34", min_age=25, max_age=34,  median_monthly_salary=2820, source=_s, source_metric=_sm),
        AgeBenchmarkSalary(age_band="35-49", min_age=35, max_age=49,  median_monthly_salary=3062, source=_s, source_metric=_sm),
        AgeBenchmarkSalary(age_band="50-64", min_age=50, max_age=64,  median_monthly_salary=2698, source=_s, source_metric=_sm),
        AgeBenchmarkSalary(age_band="65+",   min_age=65, max_age=None, median_monthly_salary=1582, source=_s, source_metric=_sm),
        AgeBenchmarkPension(age_band="Under 25", min_age=0,  max_age=24, median_pension_pot=5500,   source=_p, source_metric=_pm),
        AgeBenchmarkPension(age_band="25-34",    min_age=25, max_age=34, median_pension_pot=18800,  source=_p, source_metric=_pm),
        AgeBenchmarkPension(age_band="35-44",    min_age=35, max_age=44, median_pension_pot=39500,  source=_p, source_metric=_pm),
        AgeBenchmarkPension(age_band="45-54",    min_age=45, max_age=54, median_pension_pot=None,   source=_p, source_metric=_pm),
        AgeBenchmarkPension(age_band="55-64",    min_age=55, max_age=64, median_pension_pot=None,   source=_p, source_metric=_pm),
        AgeBenchmarkPension(age_band="65-74",    min_age=65, max_age=74, median_pension_pot=145900, source=_p, source_metric=_pm),
    ])
    db.commit()


class TestComparisonEndpoint:
    def test_no_dob_returns_nulls(self, client, db):
        _seed_benchmarks(db)
        client.post(REGISTER, json=_ALICE)
        body = client.get("/api/profile/comparison", headers=_auth_header(client)).json()
        assert body["user_age"] is None
        assert body["salary_band_label"] is None
        assert body["pension_band_label"] is None

    def test_with_dob_income_and_pension(self, client, db):
        _seed_benchmarks(db)
        client.post(REGISTER, json=_ALICE)
        headers = _auth_header(client)

        # Set date_of_birth to make user ~30 years old
        client.put("/api/profile", json={"date_of_birth": "1996-01-01"}, headers=headers)
        client.post("/api/income", json={
            "label": "Job", "gross_annual_salary": 36000.0, "pay_frequency": "monthly",
        }, headers=headers)
        client.post("/api/pension", json={
            "current_balance": 18800.0, "employee_contribution_pct": 5.0, "employer_contribution_pct": 3.0,
        }, headers=headers)

        body = client.get("/api/profile/comparison", headers=headers).json()
        assert body["user_age"] is not None
        assert body["salary_band_label"] == "25-34"
        # Monthly salary: 36000 / 12 = £3,000
        assert body["current_monthly_salary"] == 3000.0
        assert body["median_monthly_salary"] == 2820.0
        # Pension at median → 100%
        assert body["pension_comparison_pct"] == 100.0
        assert body["pension_data_available"] is True

    def test_no_income_sources_salary_is_zero(self, client, db):
        _seed_benchmarks(db)
        client.post(REGISTER, json=_ALICE)
        headers = _auth_header(client)
        client.put("/api/profile", json={"date_of_birth": "1990-01-01"}, headers=headers)
        body = client.get("/api/profile/comparison", headers=headers).json()
        assert body["current_monthly_salary"] == 0.0
        assert body["salary_comparison_pct"] == 0.0

    def test_requires_auth(self, client, db):
        resp = client.get("/api/profile/comparison")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Regional comparison — pure unit tests
# ---------------------------------------------------------------------------

REG_SOURCE = "ONS ASHE, April 2025, released October 2025"
REG_NOTES = "all employees except London which is full-time only — see note"


def _reg(region_name, median):
    return SimpleNamespace(
        region_name=region_name,
        median_annual_salary=median,
        source=REG_SOURCE,
        source_notes=REG_NOTES,
    )


@pytest.fixture
def regional_bands():
    return [
        _reg("London",                   49692),
        _reg("South East",               35215),
        _reg("East of England",          34104),
        _reg("Scotland",                 33061),
        _reg("South West",               31432),
        _reg("West Midlands",            31345),
        _reg("North West",               31330),
        _reg("Northern Ireland",         31232),
        _reg("Wales",                    30732),
        _reg("East Midlands",            30690),
        _reg("Yorkshire and the Humber", 30682),
        _reg("North East",               29584),
        _reg("UK overall",               32890),
    ]


class TestGetRegionalComparison:
    def test_no_postcode_returns_all_nulls(self, regional_bands):
        result = get_regional_comparison(None, 35000, regional_bands)
        assert result.region is None
        assert result.median_annual_salary_for_region is None
        assert result.salary_vs_region_pct is None
        assert result.is_london is False

    def test_london_postcode_matches_london(self, regional_bands):
        # SW1A → London
        result = get_regional_comparison("SW1A", 50000, regional_bands)
        assert result.region == "London"
        assert result.median_annual_salary_for_region == 49692
        assert result.is_london is True

    def test_non_london_postcode_not_flagged(self, regional_bands):
        # M1 → North West
        result = get_regional_comparison("M1", 30000, regional_bands)
        assert result.region == "North West"
        assert result.is_london is False

    def test_correct_region_matched_for_known_postcodes(self, regional_bands):
        cases = [
            ("EH1",  "Scotland"),
            ("CF10", "Wales"),
            ("BT1",  "Northern Ireland"),
            ("LS1",  "Yorkshire and the Humber"),
            ("NG1",  "East Midlands"),
            ("B1",   "West Midlands"),
            ("NE1",  "North East"),
        ]
        for postcode, expected_region in cases:
            result = get_regional_comparison(postcode, 30000, regional_bands)
            assert result.region == expected_region, f"{postcode} → expected {expected_region}, got {result.region}"

    def test_unrecognised_postcode_falls_back_to_uk_overall(self, regional_bands):
        # "ZZ9" is not a real postcode area
        result = get_regional_comparison("ZZ9", 30000, regional_bands)
        assert result.region is None
        assert result.median_annual_salary_for_region == 32890

    def test_percentage_above_median(self, regional_bands):
        # North West median 31330; salary 62660 = exactly 200%
        result = get_regional_comparison("M1", 62660, regional_bands)
        assert result.salary_vs_region_pct == 200.0

    def test_percentage_at_median(self, regional_bands):
        result = get_regional_comparison("M1", 31330, regional_bands)
        assert result.salary_vs_region_pct == 100.0

    def test_percentage_below_median(self, regional_bands):
        result = get_regional_comparison("M1", 15665, regional_bands)
        assert result.salary_vs_region_pct == 50.0

    def test_percentage_rounds_to_one_decimal(self, regional_bands):
        # 30000 / 35215 * 100 = 85.19... → 85.2
        result = get_regional_comparison("RH1", 30000, regional_bands)
        assert result.salary_vs_region_pct == 85.2

    def test_source_fields_populated(self, regional_bands):
        result = get_regional_comparison("EH1", 35000, regional_bands)
        assert result.region_source == REG_SOURCE
        assert result.region_source_notes == REG_NOTES

    def test_london_is_london_flag(self, regional_bands):
        london = get_regional_comparison("EC1A", 40000, regional_bands)
        not_london = get_regional_comparison("EH1", 40000, regional_bands)
        assert london.is_london is True
        assert not_london.is_london is False


# ---------------------------------------------------------------------------
# Integration test — /comparison endpoint includes regional fields
# ---------------------------------------------------------------------------

def _seed_regional_benchmarks(db):
    from app.models import RegionalSalaryBenchmark
    _r = "ONS ASHE, April 2025, released October 2025"
    _rn = "all employees except London which is full-time only — see note"
    db.add_all([
        RegionalSalaryBenchmark(region_name="London",                   median_annual_salary=49692, source=_r, source_notes=_rn),
        RegionalSalaryBenchmark(region_name="South East",               median_annual_salary=35215, source=_r, source_notes=_rn),
        RegionalSalaryBenchmark(region_name="Scotland",                 median_annual_salary=33061, source=_r, source_notes=_rn),
        RegionalSalaryBenchmark(region_name="North West",               median_annual_salary=31330, source=_r, source_notes=_rn),
        RegionalSalaryBenchmark(region_name="UK overall",               median_annual_salary=32890, source=_r, source_notes=_rn),
    ])
    db.commit()


class TestComparisonEndpointRegional:
    def test_postcode_set_returns_regional_data(self, client, db):
        _seed_benchmarks(db)
        _seed_regional_benchmarks(db)
        client.post(REGISTER, json=_ALICE)
        headers = _auth_header(client)

        client.put("/api/profile", json={
            "date_of_birth": "1990-01-01",
            "postcode_outward": "M1",
        }, headers=headers)
        client.post("/api/income", json={
            "label": "Job", "gross_annual_salary": 31330.0, "pay_frequency": "monthly",
        }, headers=headers)

        body = client.get("/api/profile/comparison", headers=headers).json()
        assert body["region"] == "North West"
        assert body["median_annual_salary_for_region"] == 31330.0
        assert body["salary_vs_region_pct"] == 100.0
        assert body["is_london"] is False
        assert body["current_annual_salary"] == 31330.0

    def test_no_postcode_returns_null_regional_fields(self, client, db):
        _seed_benchmarks(db)
        _seed_regional_benchmarks(db)
        client.post(REGISTER, json=_ALICE)
        body = client.get("/api/profile/comparison", headers=_auth_header(client)).json()
        assert body["region"] is None
        assert body["median_annual_salary_for_region"] is None
        assert body["salary_vs_region_pct"] is None
        assert body["is_london"] is False

    def test_london_postcode_sets_is_london(self, client, db):
        _seed_benchmarks(db)
        _seed_regional_benchmarks(db)
        client.post(REGISTER, json=_ALICE)
        headers = _auth_header(client)
        client.put("/api/profile", json={"postcode_outward": "EC1A"}, headers=headers)
        body = client.get("/api/profile/comparison", headers=headers).json()
        assert body["region"] == "London"
        assert body["is_london"] is True

    def test_unrecognised_postcode_uses_uk_overall(self, client, db):
        _seed_benchmarks(db)
        _seed_regional_benchmarks(db)
        client.post(REGISTER, json=_ALICE)
        headers = _auth_header(client)
        # Store a valid-format but unmapped outward code
        client.put("/api/profile", json={"postcode_outward": "ZZ9"}, headers=headers)
        body = client.get("/api/profile/comparison", headers=headers).json()
        assert body["region"] is None
        assert body["median_annual_salary_for_region"] == 32890.0
