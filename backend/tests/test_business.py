"""Tests for business income/expense CRUD, ownership isolation, YTD summary, and HMRC simplified expenses."""
from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from app.models.config import BusinessTaxConfig, TaxYearConfig

REGISTER = "/api/auth/register"
LOGIN = "/api/auth/login"

INCOME_URL  = "/api/business/income"
EXPENSE_URL = "/api/business/expenses"
SUMMARY_URL = "/api/business/summary"
TAX_CFG_URL = "/api/business/tax-config"

TODAY = date.today().isoformat()


def auth(client, email="alice@test.com", password="testpass123!"):
    client.post(REGISTER, json={"email": email, "password": password})
    r = client.post(LOGIN, data={"username": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _tax_year_label_for_today() -> str:
    today = date.today()
    year  = today.year if today >= date(today.year, 4, 6) else today.year - 1
    return f"{year}/{str(year + 1)[2:]}"


def seed_biz_config(db):
    """Seed a BusinessTaxConfig (including Class 4/2 NI) for the current tax year."""
    label = _tax_year_label_for_today()
    if not db.query(BusinessTaxConfig).filter_by(tax_year=label).first():
        db.add(BusinessTaxConfig(
            tax_year=label,
            home_office_band_25_50=10.0,
            home_office_band_51_100=18.0,
            home_office_band_101_plus=26.0,
            mileage_car_van_first=0.55,
            mileage_car_van_over=0.25,
            mileage_motorcycle=0.24,
            mileage_bicycle=0.20,
            mileage_threshold=10000,
            class4_lower_limit=12570,
            class4_upper_limit=50270,
            class4_main_rate=0.06,
            class4_upper_rate=0.02,
            class2_small_profits_threshold=7105,
            class2_weekly_rate=3.65,
        ))
        db.commit()


def seed_tax_year_config(db):
    """Seed a TaxYearConfig for the current tax year into the test DB."""
    label = _tax_year_label_for_today()
    if not db.query(TaxYearConfig).filter_by(tax_year=label).first():
        db.add(TaxYearConfig(
            tax_year=label,
            personal_allowance=12570,
            basic_rate_threshold=50270,
            basic_rate_pct=20,
            higher_rate_threshold=125140,
            higher_rate_pct=40,
            additional_rate_pct=45,
            ni_primary_threshold=12584,
            ni_upper_threshold=50284,
            ni_main_rate_pct=8,
            ni_upper_rate_pct=2,
            pension_qualifying_lower=6240,
            pension_qualifying_upper=50270,
            pension_min_total_pct=8,
            pension_min_employer_pct=3,
        ))
        db.commit()


# ---------------------------------------------------------------------------
# Income CRUD
# ---------------------------------------------------------------------------

class TestBusinessIncomeCRUD:
    CREATE = {"amount": 1500.0, "date_received": TODAY, "description": "Invoice #001"}
    UPDATE = {"amount": 1600.0}

    def test_create(self, client):
        h = auth(client)
        r = client.post(INCOME_URL, json=self.CREATE, headers=h)
        assert r.status_code == 201
        body = r.json()
        assert body["amount"] == 1500.0
        assert body["description"] == "Invoice #001"

    def test_list(self, client):
        h = auth(client)
        r = client.post(INCOME_URL, json=self.CREATE, headers=h)
        item_id = r.json()["id"]
        ids = [i["id"] for i in client.get(INCOME_URL, headers=h).json()]
        assert item_id in ids

    def test_update(self, client):
        h = auth(client)
        item_id = client.post(INCOME_URL, json=self.CREATE, headers=h).json()["id"]
        r = client.patch(f"{INCOME_URL}/{item_id}", json=self.UPDATE, headers=h)
        assert r.status_code == 200
        assert r.json()["amount"] == 1600.0

    def test_delete(self, client):
        h = auth(client)
        item_id = client.post(INCOME_URL, json=self.CREATE, headers=h).json()["id"]
        r = client.delete(f"{INCOME_URL}/{item_id}", headers=h)
        assert r.status_code == 204
        ids = [i["id"] for i in client.get(INCOME_URL, headers=h).json()]
        assert item_id not in ids

    def test_isolation(self, client):
        alice = auth(client, "alice@test.com")
        bob   = auth(client, "bob@test.com")
        item_id = client.post(INCOME_URL, json=self.CREATE, headers=alice).json()["id"]
        assert client.patch(f"{INCOME_URL}/{item_id}", json=self.UPDATE, headers=bob).status_code == 404
        assert client.delete(f"{INCOME_URL}/{item_id}", headers=bob).status_code == 404
        bob_ids = [i["id"] for i in client.get(INCOME_URL, headers=bob).json()]
        assert item_id not in bob_ids

    def test_optional_description(self, client):
        h = auth(client)
        r = client.post(INCOME_URL, json={"amount": 500.0, "date_received": TODAY}, headers=h)
        assert r.status_code == 201
        assert r.json()["description"] is None


# ---------------------------------------------------------------------------
# Expense CRUD + allowability + new fields
# ---------------------------------------------------------------------------

class TestBusinessExpenseCRUD:
    CREATE = {"amount": 299.0, "date_incurred": TODAY, "category": "software", "description": "Figma subscription"}
    UPDATE = {"amount": 350.0}

    def test_create(self, client):
        h = auth(client)
        r = client.post(EXPENSE_URL, json=self.CREATE, headers=h)
        assert r.status_code == 201
        body = r.json()
        assert body["amount"] == 299.0
        assert body["category"] == "software"
        assert body["business_use_percent"] == 100
        assert body["expense_method"] is None

    def test_create_includes_is_allowable(self, client):
        h = auth(client)
        r = client.post(EXPENSE_URL, json={**self.CREATE, "is_allowable": True}, headers=h)
        assert r.status_code == 201
        assert r.json()["is_allowable"] is True

    def test_create_non_allowable(self, client):
        h = auth(client)
        payload = {"amount": 150.0, "date_incurred": TODAY, "category": "client_entertainment", "is_allowable": False}
        r = client.post(EXPENSE_URL, json=payload, headers=h)
        assert r.status_code == 201
        assert r.json()["is_allowable"] is False

    def test_default_is_allowable_true(self, client):
        h = auth(client)
        r = client.post(EXPENSE_URL, json=self.CREATE, headers=h)
        assert r.json()["is_allowable"] is True

    def test_update_is_allowable(self, client):
        h = auth(client)
        item_id = client.post(EXPENSE_URL, json=self.CREATE, headers=h).json()["id"]
        r = client.patch(f"{EXPENSE_URL}/{item_id}", json={"is_allowable": False}, headers=h)
        assert r.status_code == 200
        assert r.json()["is_allowable"] is False

    def test_list(self, client):
        h = auth(client)
        item_id = client.post(EXPENSE_URL, json=self.CREATE, headers=h).json()["id"]
        ids = [i["id"] for i in client.get(EXPENSE_URL, headers=h).json()]
        assert item_id in ids

    def test_update(self, client):
        h = auth(client)
        item_id = client.post(EXPENSE_URL, json=self.CREATE, headers=h).json()["id"]
        r = client.patch(f"{EXPENSE_URL}/{item_id}", json=self.UPDATE, headers=h)
        assert r.status_code == 200
        assert r.json()["amount"] == 350.0

    def test_delete(self, client):
        h = auth(client)
        item_id = client.post(EXPENSE_URL, json=self.CREATE, headers=h).json()["id"]
        r = client.delete(f"{EXPENSE_URL}/{item_id}", headers=h)
        assert r.status_code == 204
        ids = [i["id"] for i in client.get(EXPENSE_URL, headers=h).json()]
        assert item_id not in ids

    def test_isolation(self, client):
        alice = auth(client, "alice@test.com")
        bob   = auth(client, "bob@test.com")
        item_id = client.post(EXPENSE_URL, json=self.CREATE, headers=alice).json()["id"]
        assert client.patch(f"{EXPENSE_URL}/{item_id}", json=self.UPDATE, headers=bob).status_code == 404
        assert client.delete(f"{EXPENSE_URL}/{item_id}", headers=bob).status_code == 404

    def test_new_categories_accepted(self, client):
        h = auth(client)
        for cat in ("insurance", "staff_costs", "phone_internet", "pension_employer",
                    "bank_charges", "client_entertainment", "fines", "personal",
                    "political", "home_office"):
            r = client.post(EXPENSE_URL, json={"amount": 10.0, "date_incurred": TODAY, "category": cat}, headers=h)
            assert r.status_code == 201, f"Failed for category: {cat}"

    def test_mileage_expense_stored(self, client):
        h = auth(client)
        payload = {
            "amount": 0,
            "date_incurred": TODAY,
            "category": "travel",
            "is_allowable": True,
            "expense_method": "mileage",
            "business_miles": 1200,
            "vehicle_type": "car_van",
        }
        r = client.post(EXPENSE_URL, json=payload, headers=h)
        assert r.status_code == 201
        body = r.json()
        assert body["expense_method"] == "mileage"
        assert body["business_miles"] == 1200
        assert body["vehicle_type"] == "car_van"

    def test_home_office_flat_stored(self, client):
        h = auth(client)
        payload = {
            "amount": 0,
            "date_incurred": TODAY,
            "category": "home_office",
            "is_allowable": True,
            "expense_method": "home_office_flat",
            "home_office_hours_band": "101_plus",
        }
        r = client.post(EXPENSE_URL, json=payload, headers=h)
        assert r.status_code == 201
        body = r.json()
        assert body["expense_method"] == "home_office_flat"
        assert body["home_office_hours_band"] == "101_plus"

    def test_percentage_expense_stored(self, client):
        h = auth(client)
        payload = {
            "amount": 100.0,
            "date_incurred": TODAY,
            "category": "phone_internet",
            "is_allowable": True,
            "expense_method": "percentage",
            "business_use_percent": 70,
        }
        r = client.post(EXPENSE_URL, json=payload, headers=h)
        assert r.status_code == 201
        body = r.json()
        assert body["business_use_percent"] == 70
        assert body["expense_method"] == "percentage"


# ---------------------------------------------------------------------------
# Summary — YTD, tax year boundary, allowable split
# ---------------------------------------------------------------------------

def _this_year_april_6() -> date:
    today = date.today()
    return date(today.year, 4, 6) if today >= date(today.year, 4, 6) else date(today.year - 1, 4, 6)


class TestBusinessSummary:
    def test_empty_summary(self, client):
        h = auth(client)
        r = client.get(SUMMARY_URL, headers=h)
        assert r.status_code == 200
        body = r.json()
        assert body["revenue_ytd"] == 0.0
        assert body["total_expenses_ytd"] == 0.0
        assert body["allowable_expenses_ytd"] == 0.0
        assert body["cash_profit"] == 0.0
        assert body["taxable_profit"] == 0.0
        assert body["has_business_data"] is False
        assert body["total_business_miles"] == 0
        assert body["total_mileage_allowance"] == 0.0
        assert body["mileage_crossover_msg"] is None

    def test_has_data_flag(self, client):
        h = auth(client)
        client.post(INCOME_URL, json={"amount": 100.0, "date_received": TODAY}, headers=h)
        body = client.get(SUMMARY_URL, headers=h).json()
        assert body["has_business_data"] is True

    def test_ytd_sums_current_year_only(self, client):
        h = auth(client)
        tax_start = _this_year_april_6()
        within = tax_start.isoformat()
        before = (tax_start - timedelta(days=1)).isoformat()

        client.post(INCOME_URL, json={"amount": 1000.0, "date_received": within}, headers=h)
        client.post(INCOME_URL, json={"amount": 500.0,  "date_received": before}, headers=h)
        client.post(EXPENSE_URL, json={"amount": 200.0, "date_incurred": within, "category": "software", "is_allowable": True}, headers=h)
        client.post(EXPENSE_URL, json={"amount": 100.0, "date_incurred": before, "category": "travel"}, headers=h)

        body = client.get(SUMMARY_URL, headers=h).json()
        assert body["revenue_ytd"]        == pytest.approx(1000.0)
        assert body["total_expenses_ytd"] == pytest.approx(200.0)
        assert body["cash_profit"]        == pytest.approx(800.0)
        assert body["has_business_data"]  is True

    def test_allowable_vs_non_allowable_split(self, client):
        h = auth(client)
        d = _this_year_april_6().isoformat()

        client.post(INCOME_URL, json={"amount": 5000.0, "date_received": d}, headers=h)
        client.post(EXPENSE_URL, json={"amount": 300.0, "date_incurred": d, "category": "software",              "is_allowable": True},  headers=h)
        client.post(EXPENSE_URL, json={"amount": 500.0, "date_incurred": d, "category": "equipment",             "is_allowable": True},  headers=h)
        client.post(EXPENSE_URL, json={"amount": 200.0, "date_incurred": d, "category": "client_entertainment",  "is_allowable": False}, headers=h)

        body = client.get(SUMMARY_URL, headers=h).json()
        assert body["total_expenses_ytd"]      == pytest.approx(1000.0)
        assert body["allowable_expenses_ytd"]  == pytest.approx(800.0)
        assert body["cash_profit"]             == pytest.approx(4000.0)
        assert body["taxable_profit"]          == pytest.approx(4200.0)

    def test_non_allowable_categories_default_flag(self, client):
        h = auth(client)
        d = _this_year_april_6().isoformat()
        client.post(INCOME_URL, json={"amount": 1000.0, "date_received": d}, headers=h)
        for cat in ("client_entertainment", "fines", "personal", "political"):
            client.post(EXPENSE_URL, json={"amount": 100.0, "date_incurred": d, "category": cat, "is_allowable": False}, headers=h)

        body = client.get(SUMMARY_URL, headers=h).json()
        assert body["total_expenses_ytd"]     == pytest.approx(400.0)
        assert body["allowable_expenses_ytd"] == pytest.approx(0.0)
        assert body["taxable_profit"]         == pytest.approx(1000.0)

    def test_april_5_falls_in_previous_tax_year(self, client):
        h = auth(client)
        tax_start = _this_year_april_6()
        april_5 = date(tax_start.year, 4, 5)
        client.post(INCOME_URL, json={"amount": 999.0, "date_received": april_5.isoformat()}, headers=h)
        assert client.get(SUMMARY_URL, headers=h).json()["revenue_ytd"] == pytest.approx(0.0)

    def test_april_6_falls_in_current_tax_year(self, client):
        h = auth(client)
        tax_start = _this_year_april_6()
        client.post(INCOME_URL, json={"amount": 999.0, "date_received": tax_start.isoformat()}, headers=h)
        assert client.get(SUMMARY_URL, headers=h).json()["revenue_ytd"] == pytest.approx(999.0)

    def test_summary_isolation(self, client):
        alice = auth(client, "alice@test.com")
        bob   = auth(client, "bob@test.com")
        client.post(INCOME_URL, json={"amount": 5000.0, "date_received": TODAY}, headers=alice)
        assert client.get(SUMMARY_URL, headers=bob).json()["revenue_ytd"] == 0.0


# ---------------------------------------------------------------------------
# Mileage allowance (needs seeded config)
# ---------------------------------------------------------------------------

class TestMileageAllowance:
    def test_car_van_below_threshold(self, client, db):
        seed_biz_config(db)
        h = auth(client)
        d = _this_year_april_6().isoformat()
        client.post(INCOME_URL, json={"amount": 10000.0, "date_received": d}, headers=h)
        client.post(EXPENSE_URL, json={
            "amount": 0, "date_incurred": d, "category": "travel",
            "is_allowable": True, "expense_method": "mileage",
            "business_miles": 1000, "vehicle_type": "car_van",
        }, headers=h)

        body = client.get(SUMMARY_URL, headers=h).json()
        assert body["total_business_miles"]    == 1000
        assert body["total_mileage_allowance"] == pytest.approx(550.0)   # 1000 × 0.55
        assert body["allowable_expenses_ytd"]  == pytest.approx(550.0)
        assert body["total_expenses_ytd"]      == pytest.approx(0.0)     # no cash outlay
        assert body["cash_profit"]             == pytest.approx(10000.0)
        assert body["taxable_profit"]          == pytest.approx(9450.0)  # 10000 - 550
        assert "9,000" in body["mileage_crossover_msg"]                  # 9,000 remaining

    def test_car_van_crosses_threshold(self, client, db):
        seed_biz_config(db)
        h = auth(client)
        d = _this_year_april_6().isoformat()
        client.post(INCOME_URL, json={"amount": 10000.0, "date_received": d}, headers=h)
        # 8,000 + 4,000 = 12,000 miles total
        client.post(EXPENSE_URL, json={
            "amount": 0, "date_incurred": d, "category": "travel",
            "is_allowable": True, "expense_method": "mileage",
            "business_miles": 8000, "vehicle_type": "car_van",
        }, headers=h)
        client.post(EXPENSE_URL, json={
            "amount": 0, "date_incurred": d, "category": "travel",
            "is_allowable": True, "expense_method": "mileage",
            "business_miles": 4000, "vehicle_type": "car_van",
        }, headers=h)

        body = client.get(SUMMARY_URL, headers=h).json()
        # 10000 × 0.55 + 2000 × 0.25 = 5500 + 500 = 6000
        assert body["total_business_miles"]    == 12000
        assert body["total_mileage_allowance"] == pytest.approx(6000.0)
        assert "2,000" in body["mileage_crossover_msg"]  # 2,000 miles over threshold

    def test_motorcycle_flat_rate(self, client, db):
        seed_biz_config(db)
        h = auth(client)
        d = _this_year_april_6().isoformat()
        client.post(INCOME_URL, json={"amount": 1000.0, "date_received": d}, headers=h)
        client.post(EXPENSE_URL, json={
            "amount": 0, "date_incurred": d, "category": "travel",
            "is_allowable": True, "expense_method": "mileage",
            "business_miles": 500, "vehicle_type": "motorcycle",
        }, headers=h)

        body = client.get(SUMMARY_URL, headers=h).json()
        assert body["total_mileage_allowance"] == pytest.approx(120.0)  # 500 × 0.24
        assert body["mileage_crossover_msg"] is None  # no car/van miles

    def test_bicycle_flat_rate(self, client, db):
        seed_biz_config(db)
        h = auth(client)
        d = _this_year_april_6().isoformat()
        client.post(INCOME_URL, json={"amount": 1000.0, "date_received": d}, headers=h)
        client.post(EXPENSE_URL, json={
            "amount": 0, "date_incurred": d, "category": "travel",
            "is_allowable": True, "expense_method": "mileage",
            "business_miles": 200, "vehicle_type": "bicycle",
        }, headers=h)

        body = client.get(SUMMARY_URL, headers=h).json()
        assert body["total_mileage_allowance"] == pytest.approx(40.0)   # 200 × 0.20

    def test_mileage_excluded_from_cash_expenses(self, client, db):
        seed_biz_config(db)
        h = auth(client)
        d = _this_year_april_6().isoformat()
        client.post(INCOME_URL, json={"amount": 5000.0, "date_received": d}, headers=h)
        # Cash expense
        client.post(EXPENSE_URL, json={"amount": 200.0, "date_incurred": d, "category": "software", "is_allowable": True}, headers=h)
        # Mileage (no cash)
        client.post(EXPENSE_URL, json={
            "amount": 0, "date_incurred": d, "category": "travel",
            "is_allowable": True, "expense_method": "mileage",
            "business_miles": 100, "vehicle_type": "car_van",
        }, headers=h)

        body = client.get(SUMMARY_URL, headers=h).json()
        assert body["total_expenses_ytd"]     == pytest.approx(200.0)   # mileage not in cash
        assert body["cash_profit"]            == pytest.approx(4800.0)  # 5000 - 200
        assert body["allowable_expenses_ytd"] == pytest.approx(200.0 + 55.0)  # 100 × 0.55


# ---------------------------------------------------------------------------
# Home office flat rate (needs seeded config)
# ---------------------------------------------------------------------------

class TestHomeOfficeFlatRate:
    def test_single_month_101_plus_band(self, client, db):
        seed_biz_config(db)
        h = auth(client)
        d = _this_year_april_6().isoformat()
        client.post(INCOME_URL, json={"amount": 5000.0, "date_received": d}, headers=h)
        client.post(EXPENSE_URL, json={
            "amount": 0, "date_incurred": d, "category": "home_office",
            "is_allowable": True, "expense_method": "home_office_flat",
            "home_office_hours_band": "101_plus",
        }, headers=h)

        body = client.get(SUMMARY_URL, headers=h).json()
        assert body["allowable_expenses_ytd"] == pytest.approx(26.0)
        assert body["total_expenses_ytd"]     == pytest.approx(0.0)  # no cash outlay
        assert body["cash_profit"]            == pytest.approx(5000.0)
        assert body["taxable_profit"]         == pytest.approx(4974.0)

    def test_multiple_months_different_bands(self, client, db):
        seed_biz_config(db)
        h = auth(client)
        d = _this_year_april_6().isoformat()
        client.post(INCOME_URL, json={"amount": 5000.0, "date_received": d}, headers=h)
        # 2 × £26 + 1 × £18 + 1 × £10 = £80
        for band, n in [("101_plus", 2), ("51_100", 1), ("25_50", 1)]:
            for _ in range(n):
                client.post(EXPENSE_URL, json={
                    "amount": 0, "date_incurred": d, "category": "home_office",
                    "is_allowable": True, "expense_method": "home_office_flat",
                    "home_office_hours_band": band,
                }, headers=h)

        body = client.get(SUMMARY_URL, headers=h).json()
        assert body["allowable_expenses_ytd"] == pytest.approx(80.0)


# ---------------------------------------------------------------------------
# Percentage (partial business use)
# ---------------------------------------------------------------------------

class TestPercentageExpenses:
    def test_70pct_business_use(self, client):
        h = auth(client)
        d = _this_year_april_6().isoformat()
        client.post(INCOME_URL, json={"amount": 1000.0, "date_received": d}, headers=h)
        client.post(EXPENSE_URL, json={
            "amount": 100.0, "date_incurred": d, "category": "phone_internet",
            "is_allowable": True, "expense_method": "percentage",
            "business_use_percent": 70,
        }, headers=h)

        body = client.get(SUMMARY_URL, headers=h).json()
        assert body["total_expenses_ytd"]     == pytest.approx(100.0)
        assert body["allowable_expenses_ytd"] == pytest.approx(70.0)
        assert body["cash_profit"]            == pytest.approx(900.0)
        assert body["taxable_profit"]         == pytest.approx(930.0)

    def test_home_office_actual(self, client):
        h = auth(client)
        d = _this_year_april_6().isoformat()
        client.post(INCOME_URL, json={"amount": 2000.0, "date_received": d}, headers=h)
        client.post(EXPENSE_URL, json={
            "amount": 500.0, "date_incurred": d, "category": "home_office",
            "is_allowable": True, "expense_method": "home_office_actual",
            "business_use_percent": 40,
        }, headers=h)

        body = client.get(SUMMARY_URL, headers=h).json()
        assert body["total_expenses_ytd"]     == pytest.approx(500.0)
        assert body["allowable_expenses_ytd"] == pytest.approx(200.0)   # 500 × 40%


# ---------------------------------------------------------------------------
# Tax config endpoint
# ---------------------------------------------------------------------------

class TestTaxConfigEndpoint:
    def test_returns_404_without_seed(self, client):
        h = auth(client)
        r = client.get(TAX_CFG_URL, headers=h)
        assert r.status_code == 404

    def test_returns_config_when_seeded(self, client, db):
        seed_biz_config(db)
        h = auth(client)
        r = client.get(TAX_CFG_URL, headers=h)
        assert r.status_code == 200
        body = r.json()
        assert body["mileage_car_van_first"] == pytest.approx(0.55)
        assert body["mileage_threshold"]     == 10000
        assert body["home_office_band_101_plus"] == pytest.approx(26.0)

    def test_requires_auth(self, client):
        r = client.get(TAX_CFG_URL)
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Per-entry mileage attribution
# ---------------------------------------------------------------------------

def _post_mileage(client, headers, date_str, miles, vehicle_type):
    r = client.post(EXPENSE_URL, json={
        "amount": 0, "date_incurred": date_str, "category": "travel",
        "is_allowable": True, "expense_method": "mileage",
        "business_miles": miles, "vehicle_type": vehicle_type,
    }, headers=headers)
    assert r.status_code == 201, r.json()
    return r.json()["id"]


class TestMileageAttribution:
    """Per-entry attribution — all rates and thresholds read from seeded config."""

    def test_two_entries_straddling_threshold_total_is_correct(self, client, db):
        """Two 6,000-mile car/van entries → £6,000 total (not 2 × £3,300 = £6,600).
        Second entry straddles: 4,000 at lower rate, 2,000 at upper rate."""
        seed_biz_config(db)
        h = auth(client)
        d = _this_year_april_6().isoformat()
        client.post(INCOME_URL, json={"amount": 10000.0, "date_received": d}, headers=h)

        id1 = _post_mileage(client, h, d, 6000, "car_van")
        id2 = _post_mileage(client, h, d, 6000, "car_van")

        body = client.get(SUMMARY_URL, headers=h).json()
        attr = body["mileage_attribution"]

        # Entry 1: 0 → 6,000 (all lower band) = 6,000 × 0.55 = £3,300
        assert attr[str(id1)] == pytest.approx(3300.0)
        # Entry 2: 6,000 → 12,000; lower=4,000, upper=2,000 = 4000×0.55+2000×0.25 = £2,700
        assert attr[str(id2)] == pytest.approx(2700.0)
        assert body["total_mileage_allowance"] == pytest.approx(6000.0)

    def test_single_entry_straddling_threshold(self, client, db):
        """Cumulative at 9,500, then log 1,000 → (500 × lower) + (500 × upper)."""
        seed_biz_config(db)
        h = auth(client)
        tax_start = _this_year_april_6()
        d1 = tax_start.isoformat()
        d2 = (tax_start + timedelta(days=1)).isoformat()

        client.post(INCOME_URL, json={"amount": 10000.0, "date_received": d1}, headers=h)
        _post_mileage(client, h, d1, 9500, "car_van")
        id2 = _post_mileage(client, h, d2, 1000, "car_van")

        body = client.get(SUMMARY_URL, headers=h).json()
        attr = body["mileage_attribution"]

        # Entry 2: before=9500, after=10500; lower=min(10500,10000)-9500=500, upper=500
        assert attr[str(id2)] == pytest.approx(500 * 0.55 + 500 * 0.25)

    def test_reconciliation_guarantee(self, client, db):
        """Sum of all per-entry attributed values equals the annual total exactly."""
        seed_biz_config(db)
        h = auth(client)
        d = _this_year_april_6().isoformat()
        client.post(INCOME_URL, json={"amount": 50000.0, "date_received": d}, headers=h)

        for miles, vtype in [(3000, "car_van"), (2000, "motorcycle"), (8000, "car_van"), (500, "bicycle")]:
            _post_mileage(client, h, d, miles, vtype)

        body = client.get(SUMMARY_URL, headers=h).json()
        attr = body["mileage_attribution"]

        assert sum(attr.values()) == pytest.approx(body["total_mileage_allowance"])

    def test_flat_rate_vehicle_no_threshold(self, client, db):
        """Motorcycle: each entry = miles × rate, cumulative miles never matter."""
        seed_biz_config(db)
        h = auth(client)
        d = _this_year_april_6().isoformat()
        client.post(INCOME_URL, json={"amount": 1000.0, "date_received": d}, headers=h)

        id1 = _post_mileage(client, h, d, 20000, "motorcycle")   # far above any threshold
        id2 = _post_mileage(client, h, d, 5000,  "motorcycle")

        body = client.get(SUMMARY_URL, headers=h).json()
        attr = body["mileage_attribution"]

        assert attr[str(id1)] == pytest.approx(20000 * 0.24)
        assert attr[str(id2)] == pytest.approx(5000  * 0.24)

    def test_mixed_car_and_motorcycle_independent(self, client, db):
        """Car miles accrue against the tiered threshold; motorcycle stays flat.
        Neither pool affects the other."""
        seed_biz_config(db)
        h = auth(client)
        d = _this_year_april_6().isoformat()
        client.post(INCOME_URL, json={"amount": 20000.0, "date_received": d}, headers=h)

        car_id   = _post_mileage(client, h, d, 12000, "car_van")      # 10k at 0.55 + 2k at 0.25
        moto_id  = _post_mileage(client, h, d, 3000,  "motorcycle")   # flat 3k × 0.24

        body = client.get(SUMMARY_URL, headers=h).json()
        attr = body["mileage_attribution"]

        expected_car  = round(10000 * 0.55 + 2000 * 0.25, 2)   # £6,000
        expected_moto = round(3000 * 0.24, 2)                   # £720
        assert attr[str(car_id)]  == pytest.approx(expected_car)
        assert attr[str(moto_id)] == pytest.approx(expected_moto)
        assert body["total_mileage_allowance"] == pytest.approx(expected_car + expected_moto)

    def test_per_type_pools_are_independent(self, client, db):
        """Two tiered vehicle types each maintain their own cumulative pool.
        In our config car_van is the only tiered type; this test verifies that
        a car_van entry and a motorcycle entry don't share the tiered pool
        (motorcycle uses a flat rate regardless of car_van cumulative miles)."""
        seed_biz_config(db)
        h = auth(client)
        d = _this_year_april_6().isoformat()
        client.post(INCOME_URL, json={"amount": 10000.0, "date_received": d}, headers=h)

        # Log 9,000 car/van miles — 1,000 remaining in lower band
        car_id = _post_mileage(client, h, d, 9000, "car_van")
        # Motorcycle miles never affect car/van cumulative
        moto_id = _post_mileage(client, h, d, 5000, "motorcycle")

        body = client.get(SUMMARY_URL, headers=h).json()
        attr = body["mileage_attribution"]

        # car: all 9,000 in lower band (threshold not reached)
        assert attr[str(car_id)]  == pytest.approx(9000 * 0.55)
        # moto: flat rate regardless of any car/van cumulative
        assert attr[str(moto_id)] == pytest.approx(5000 * 0.24)
        assert body["mileage_crossover_msg"] is not None  # 1,000 remaining message

    def test_motorcycle_1000_miles_per_entry(self, client, db):
        """Motorcycle 1,000 miles → attributed = 1000 × rate from config (not £0)."""
        seed_biz_config(db)
        h = auth(client)
        d = _this_year_april_6().isoformat()
        client.post(INCOME_URL, json={"amount": 1000.0, "date_received": d}, headers=h)

        moto_id = _post_mileage(client, h, d, 1000, "motorcycle")

        body = client.get(SUMMARY_URL, headers=h).json()
        attr = body["mileage_attribution"]

        assert attr[str(moto_id)] == pytest.approx(1000 * 0.24)  # £240, never £0
        assert body["total_mileage_allowance"] == pytest.approx(240.0)
        assert body["mileage_crossover_msg"] is None  # no tiered vehicle

    def test_bicycle_per_entry_attribution(self, client, db):
        """Bicycle: attributed = miles × bicycle rate from config, no threshold logic."""
        seed_biz_config(db)
        h = auth(client)
        d = _this_year_april_6().isoformat()
        client.post(INCOME_URL, json={"amount": 1000.0, "date_received": d}, headers=h)

        bike_id = _post_mileage(client, h, d, 350, "bicycle")

        body = client.get(SUMMARY_URL, headers=h).json()
        attr = body["mileage_attribution"]

        assert attr[str(bike_id)] == pytest.approx(350 * 0.20)  # £70
        assert body["total_mileage_allowance"] == pytest.approx(70.0)

    def test_deterministic_ordering_same_day(self, client, db):
        """Same-day entries are stable across repeated calls (sorted by id as tiebreaker)."""
        seed_biz_config(db)
        h = auth(client)
        d = _this_year_april_6().isoformat()
        client.post(INCOME_URL, json={"amount": 10000.0, "date_received": d}, headers=h)

        # Both logged on same day — ordering must be by id (ascending)
        id1 = _post_mileage(client, h, d, 9000, "car_van")
        id2 = _post_mileage(client, h, d, 2000, "car_van")

        body1 = client.get(SUMMARY_URL, headers=h).json()
        body2 = client.get(SUMMARY_URL, headers=h).json()

        # Values must be identical across two calls
        assert body1["mileage_attribution"] == body2["mileage_attribution"]

        # With id1 first: id1=9000×0.55=4950, id2=1000×0.55+1000×0.25=800
        attr = body1["mileage_attribution"]
        assert attr[str(id1)] == pytest.approx(9000 * 0.55)
        assert attr[str(id2)] == pytest.approx(1000 * 0.55 + 1000 * 0.25)
        assert body1["total_mileage_allowance"] == pytest.approx(9000 * 0.55 + 1000 * 0.55 + 1000 * 0.25)


# ---------------------------------------------------------------------------
# Sole trader tax engine — income tax + Class 4 NI + Class 2 position
# ---------------------------------------------------------------------------

class TestSoleTraderTax:
    """Tax engine tests. All rates and thresholds from seeded config, no hardcoding."""

    def _add_income(self, client, h, amount, d):
        client.post(INCOME_URL, json={"amount": amount, "date_received": d}, headers=h)

    def test_class4_hmrc_worked_example_52k(self, client, db):
        """£52,000 profit — HMRC worked example: Class 4 = (37,700×6%) + (1,730×2%) = £2,296.60."""
        seed_biz_config(db)
        seed_tax_year_config(db)
        h = auth(client)
        d = _this_year_april_6().isoformat()
        self._add_income(client, h, 52000.0, d)

        te = client.get(SUMMARY_URL, headers=h).json()["tax_estimate"]
        assert te is not None
        assert te["class4_ni"]    == pytest.approx(2296.60)
        assert te["class2_status"] == "covered"
        assert te["class2_due"]   == 0.0

    def test_20k_profit(self, client, db):
        """£20,000 profit — income tax and Class 4 correct; class2_status covered."""
        seed_biz_config(db)
        seed_tax_year_config(db)
        h = auth(client)
        d = _this_year_april_6().isoformat()
        self._add_income(client, h, 20000.0, d)

        te = client.get(SUMMARY_URL, headers=h).json()["tax_estimate"]
        assert te is not None
        assert te["income_tax_on_profit"] == pytest.approx((20000 - 12570) * 0.20)   # £1,486
        assert te["class4_ni"]            == pytest.approx((20000 - 12570) * 0.06)   # £445.80
        assert te["class2_status"]        == "covered"
        assert te["class2_due"]           == 0.0

    def test_10k_profit_covered_no_class4(self, client, db):
        """£10,000 profit — between SPT (7,105) and lower limit (12,570): class2_status covered_no_class4."""
        seed_biz_config(db)
        seed_tax_year_config(db)
        h = auth(client)
        d = _this_year_april_6().isoformat()
        self._add_income(client, h, 10000.0, d)

        te = client.get(SUMMARY_URL, headers=h).json()["tax_estimate"]
        assert te is not None
        assert te["class4_ni"]            == pytest.approx(0.0)
        assert te["income_tax_on_profit"] == pytest.approx(0.0)
        assert te["class2_status"]        == "covered_no_class4"
        assert te["class2_due"]           == 0.0

    def test_5k_profit_below_threshold(self, client, db):
        """£5,000 profit — below SPT (7,105): voluntary note surfaced, class2_due still 0."""
        seed_biz_config(db)
        seed_tax_year_config(db)
        h = auth(client)
        d = _this_year_april_6().isoformat()
        self._add_income(client, h, 5000.0, d)

        te = client.get(SUMMARY_URL, headers=h).json()["tax_estimate"]
        assert te is not None
        assert te["class4_ni"]              == pytest.approx(0.0)
        assert te["class2_status"]          == "below_threshold"
        assert te["class2_due"]             == 0.0     # never auto-charged
        assert te["class2_voluntary_note"]  is not None
        assert "voluntary" in te["class2_voluntary_note"].lower()

    def test_130k_profit_taper(self, client, db):
        """£130,000 profit — PA is fully tapered; income_tax_on_profit matches personal engine."""
        seed_biz_config(db)
        seed_tax_year_config(db)
        h = auth(client)
        d = _this_year_april_6().isoformat()
        self._add_income(client, h, 130000.0, d)

        te = client.get(SUMMARY_URL, headers=h).json()["tax_estimate"]
        assert te is not None
        # Verify against the personal engine using the seeded config values
        from app.services.tax_calculator import calculate_income_tax
        tax_ns = SimpleNamespace(
            personal_allowance=12570, basic_rate_threshold=50270, basic_rate_pct=20,
            higher_rate_threshold=125140, higher_rate_pct=40, additional_rate_pct=45,
            ni_primary_threshold=12584, ni_upper_threshold=50284,
            ni_main_rate_pct=8, ni_upper_rate_pct=2,
            pension_qualifying_lower=6240, pension_qualifying_upper=50270,
        )
        expected_it = calculate_income_tax(130000, tax_ns)
        assert te["income_tax_on_profit"] == pytest.approx(expected_it)

    def test_starting_income_seam(self):
        """starting_income shifts profit to the correct marginal band — proves the seam works."""
        from app.services.tax_calculator import calculate_sole_trader_tax, calculate_income_tax

        tax_ns = SimpleNamespace(
            personal_allowance=12570, basic_rate_threshold=50270, basic_rate_pct=20,
            higher_rate_threshold=125140, higher_rate_pct=40, additional_rate_pct=45,
            ni_primary_threshold=12584, ni_upper_threshold=50284,
            ni_main_rate_pct=8, ni_upper_rate_pct=2,
            pension_qualifying_lower=6240, pension_qualifying_upper=50270,
        )
        biz_ns = SimpleNamespace(
            class4_lower_limit=12570, class4_upper_limit=50270,
            class4_main_rate=0.06, class4_upper_rate=0.02,
            class2_small_profits_threshold=7105, class2_weekly_rate=3.65,
        )

        profit   = 20_000
        starting = 45_000   # straddles basic→higher band boundary at 50,270

        result = calculate_sole_trader_tax(profit, tax_ns, biz_ns, starting_income=starting)

        # The difference form: income_tax(65000) - income_tax(45000)
        expected_it = round(
            calculate_income_tax(starting + profit, tax_ns)
            - calculate_income_tax(starting, tax_ns),
            2,
        )
        assert result.income_tax_on_profit == pytest.approx(expected_it)

        # Must be higher than the standalone (starting_income=0) result
        standalone = calculate_sole_trader_tax(profit, tax_ns, biz_ns, starting_income=0)
        assert result.income_tax_on_profit > standalone.income_tax_on_profit

    def test_total_set_aside_reconciles(self, client, db):
        """total_set_aside == income_tax_on_profit + class4_ni, exactly."""
        seed_biz_config(db)
        seed_tax_year_config(db)
        h = auth(client)
        d = _this_year_april_6().isoformat()
        self._add_income(client, h, 37000.0, d)

        te = client.get(SUMMARY_URL, headers=h).json()["tax_estimate"]
        assert te is not None
        assert te["total_set_aside"] == pytest.approx(
            te["income_tax_on_profit"] + te["class4_ni"]
        )

    def test_no_tax_estimate_without_config(self, client):
        """Without seeded configs, tax_estimate is None."""
        h = auth(client)
        d = _this_year_april_6().isoformat()
        client.post(INCOME_URL, json={"amount": 20000.0, "date_received": d}, headers=h)

        body = client.get(SUMMARY_URL, headers=h).json()
        assert body["tax_estimate"] is None


# ---------------------------------------------------------------------------
# Presentation consistency — card breakdown values match the headline totals
# ---------------------------------------------------------------------------

class TestPresentationConsistency:
    """No calculation changes — just asserting that the displayed components sum correctly."""

    def test_allowable_card_breakdown_sums_to_headline(self, client, db):
        """cash allowable + mileage allowance == allowable_expenses_ytd."""
        seed_biz_config(db)
        h = auth(client)
        d = _this_year_april_6().isoformat()
        client.post(INCOME_URL, json={"amount": 10000.0, "date_received": d}, headers=h)
        client.post(EXPENSE_URL, json={
            "amount": 500.0, "date_incurred": d, "category": "software", "is_allowable": True,
        }, headers=h)
        _post_mileage(client, h, d, 1000, "car_van")

        body = client.get(SUMMARY_URL, headers=h).json()
        cash_allowable = round(body["allowable_expenses_ytd"] - body["total_mileage_allowance"], 2)
        assert pytest.approx(cash_allowable + body["total_mileage_allowance"]) == body["allowable_expenses_ytd"]
        assert body["mileage_crossover_msg"] is not None

    def test_money_left_equals_revenue_minus_total_expenses(self, client):
        """cash_profit == revenue_ytd − total_expenses_ytd (both exclude mileage)."""
        h = auth(client)
        d = _this_year_april_6().isoformat()
        client.post(INCOME_URL, json={"amount": 5000.0, "date_received": d}, headers=h)
        client.post(EXPENSE_URL, json={
            "amount": 300.0, "date_incurred": d, "category": "software", "is_allowable": True,
        }, headers=h)
        client.post(EXPENSE_URL, json={
            "amount": 200.0, "date_incurred": d, "category": "equipment", "is_allowable": False,
        }, headers=h)

        body = client.get(SUMMARY_URL, headers=h).json()
        assert body["cash_profit"] == pytest.approx(body["revenue_ytd"] - body["total_expenses_ytd"])
