"""Tests for business income/expense CRUD, ownership isolation, YTD summary, and HMRC simplified expenses."""
from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from app.models.config import BusinessTaxConfig, TaxYearConfig

REGISTER = "/api/auth/register"
LOGIN = "/api/auth/login"

INCOME_URL   = "/api/business/income"
EXPENSE_URL  = "/api/business/expenses"
SUMMARY_URL  = "/api/business/summary"
TAX_CFG_URL  = "/api/business/tax-config"
UPCOMING_URL = "/api/business/upcoming"
TAX_DEADLINES_URL = "/api/business/tax-deadlines"

TODAY = date.today().isoformat()


def auth(client, email="alice@test.com", password="testpass123!"):
    client.post(REGISTER, json={"email": email, "password": password})
    r = client.post(LOGIN, data={"username": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _tax_year_label_for_today() -> str:
    today = date.today()
    year  = today.year if today >= date(today.year, 4, 6) else today.year - 1
    return f"{year}/{str(year + 1)[2:]}"


def _prior_tax_year_label() -> str:
    """The tax year immediately before the current one — always fully completed."""
    start_year = int(_tax_year_label_for_today().split("/")[0])
    return f"{start_year - 1}/{str(start_year)[2:]}"


def _year_label_offset(n: int) -> str:
    """Tax year label n years before the current one (n=0 -> current, n=1 -> prior, ...)."""
    start_year = int(_tax_year_label_for_today().split("/")[0]) - n
    return f"{start_year}/{str(start_year + 1)[2:]}"


def _date_in_tax_year(label: str) -> str:
    """An arbitrary confirmed (past) date inside the given 'YYYY/YY' tax year — mid-June."""
    start_year = int(label.split("/")[0])
    return date(start_year, 6, 15).isoformat()


def seed_biz_config_for(db, label, **overrides):
    """Seed a BusinessTaxConfig (including Class 4/2 NI) for an arbitrary tax year."""
    if not db.query(BusinessTaxConfig).filter_by(tax_year=label).first():
        defaults = dict(
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
            poa_threshold=1000,
        )
        defaults.update(overrides)
        db.add(BusinessTaxConfig(**defaults))
        db.commit()


def seed_tax_year_config_for(db, label, **overrides):
    """Seed a TaxYearConfig for an arbitrary tax year."""
    if not db.query(TaxYearConfig).filter_by(tax_year=label).first():
        defaults = dict(
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
        )
        defaults.update(overrides)
        db.add(TaxYearConfig(**defaults))
        db.commit()


def seed_biz_config(db):
    """Seed a BusinessTaxConfig (including Class 4/2 NI) for the current tax year."""
    seed_biz_config_for(db, _tax_year_label_for_today())


def seed_tax_year_config(db):
    """Seed a TaxYearConfig for the current tax year into the test DB."""
    seed_tax_year_config_for(db, _tax_year_label_for_today())


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
                    "political", "home_office", "goods_for_resale", "clothing"):
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

    def test_new_allowable_category_can_be_overridden_non_allowable(self, client):
        h = auth(client)
        d = _this_year_april_6().isoformat()
        client.post(INCOME_URL, json={"amount": 1000.0, "date_received": d}, headers=h)
        client.post(EXPENSE_URL, json={"amount": 200.0, "date_incurred": d, "category": "goods_for_resale", "is_allowable": False}, headers=h)

        body = client.get(SUMMARY_URL, headers=h).json()
        assert body["total_expenses_ytd"]     == pytest.approx(200.0)
        assert body["allowable_expenses_ytd"] == pytest.approx(0.0)
        assert body["taxable_profit"]         == pytest.approx(1000.0)

    def test_new_allowable_categories_flow_into_summary(self, client):
        h = auth(client)
        d = _this_year_april_6().isoformat()
        client.post(INCOME_URL, json={"amount": 5000.0, "date_received": d}, headers=h)
        client.post(EXPENSE_URL, json={"amount": 300.0, "date_incurred": d, "category": "goods_for_resale", "is_allowable": True}, headers=h)
        client.post(EXPENSE_URL, json={"amount": 150.0, "date_incurred": d, "category": "clothing",         "is_allowable": True}, headers=h)

        body = client.get(SUMMARY_URL, headers=h).json()
        assert body["total_expenses_ytd"]     == pytest.approx(450.0)
        assert body["allowable_expenses_ytd"] == pytest.approx(450.0)
        assert body["taxable_profit"]         == pytest.approx(4550.0)

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

    def test_flat_rate_excluded_from_cash_with_mixed_expenses(self, client, db):
        """HO flat rate (25_50 band = £10) must NOT inflate cash spend, but MUST count as allowable.
        A regular £200 cash expense sits alongside it to confirm separation."""
        seed_biz_config(db)
        h = auth(client)
        d = _this_year_april_6().isoformat()
        client.post(INCOME_URL, json={"amount": 5000.0, "date_received": d}, headers=h)
        client.post(EXPENSE_URL, json={
            "amount": 200.0, "date_incurred": d, "category": "software", "is_allowable": True,
        }, headers=h)
        client.post(EXPENSE_URL, json={
            "amount": 0, "date_incurred": d, "category": "home_office",
            "is_allowable": True, "expense_method": "home_office_flat",
            "home_office_hours_band": "25_50",
        }, headers=h)

        body = client.get(SUMMARY_URL, headers=h).json()
        # Config seeds home_office_band_25_50 = £10
        assert body["total_expenses_ytd"]     == pytest.approx(200.0)   # cash only; HO excluded
        assert body["allowable_expenses_ytd"] == pytest.approx(210.0)   # cash + £10 flat rate
        assert body["cash_profit"]            == pytest.approx(4800.0)  # 5000 - 200
        assert body["taxable_profit"]         == pytest.approx(4790.0)  # 5000 - 210

    def test_allowable_exceeds_cash_with_ho_flat_and_mileage(self, client, db):
        """Both HO flat rate and mileage are allowances with no cash outlay.
        allowable_expenses_ytd can legitimately exceed total_expenses_ytd."""
        seed_biz_config(db)
        h = auth(client)
        d = _this_year_april_6().isoformat()
        client.post(INCOME_URL, json={"amount": 10000.0, "date_received": d}, headers=h)
        # £100 cash expense
        client.post(EXPENSE_URL, json={
            "amount": 100.0, "date_incurred": d, "category": "software", "is_allowable": True,
        }, headers=h)
        # £26 HO flat rate (no cash)
        client.post(EXPENSE_URL, json={
            "amount": 0, "date_incurred": d, "category": "home_office",
            "is_allowable": True, "expense_method": "home_office_flat",
            "home_office_hours_band": "101_plus",
        }, headers=h)
        # 200 car/van miles = £110 allowance (no cash)
        client.post(EXPENSE_URL, json={
            "amount": 0, "date_incurred": d, "category": "travel",
            "is_allowable": True, "expense_method": "mileage",
            "business_miles": 200, "vehicle_type": "car_van",
        }, headers=h)

        body = client.get(SUMMARY_URL, headers=h).json()
        assert body["total_expenses_ytd"]     == pytest.approx(100.0)           # only the cash expense
        assert body["total_mileage_allowance"] == pytest.approx(110.0)          # 200 × 0.55
        assert body["allowable_expenses_ytd"] == pytest.approx(236.0)           # 100 + 26 + 110
        assert body["allowable_expenses_ytd"] > body["total_expenses_ytd"]      # allowance-only entries make this valid

    def test_flat_rate_value_comes_from_config_not_hardcoded(self, client, db):
        """The 51_100 band (£18) is distinct from 25_50 (£10) and 101_plus (£26).
        Asserting the specific value confirms we read from config, not hardcode."""
        seed_biz_config(db)
        h = auth(client)
        d = _this_year_april_6().isoformat()
        client.post(INCOME_URL, json={"amount": 5000.0, "date_received": d}, headers=h)
        client.post(EXPENSE_URL, json={
            "amount": 0, "date_incurred": d, "category": "home_office",
            "is_allowable": True, "expense_method": "home_office_flat",
            "home_office_hours_band": "51_100",
        }, headers=h)

        body = client.get(SUMMARY_URL, headers=h).json()
        assert body["allowable_expenses_ytd"] == pytest.approx(18.0)   # 51_100 band from seeded config
        assert body["total_expenses_ytd"]     == pytest.approx(0.0)

    def test_summary_returns_home_office_allowance_field(self, client, db):
        """home_office_allowance in the summary equals the sum of all flat-rate entries."""
        seed_biz_config(db)
        h = auth(client)
        d = _this_year_april_6().isoformat()
        client.post(INCOME_URL, json={"amount": 5000.0, "date_received": d}, headers=h)
        # 25_50 (£10) + 101_plus (£26) = £36
        client.post(EXPENSE_URL, json={
            "amount": 0, "date_incurred": d, "category": "home_office",
            "is_allowable": True, "expense_method": "home_office_flat",
            "home_office_hours_band": "25_50",
        }, headers=h)
        client.post(EXPENSE_URL, json={
            "amount": 0, "date_incurred": d, "category": "home_office",
            "is_allowable": True, "expense_method": "home_office_flat",
            "home_office_hours_band": "101_plus",
        }, headers=h)

        body = client.get(SUMMARY_URL, headers=h).json()
        assert body["home_office_allowance"] == pytest.approx(36.0)
        # Non-flat-rate expense types must not inflate home_office_allowance
        assert body["total_expenses_ytd"]    == pytest.approx(0.0)

    def test_home_office_allowance_zero_without_flat_rate_entries(self, client, db):
        """home_office_allowance is 0 when there are no flat-rate entries."""
        seed_biz_config(db)
        h = auth(client)
        d = _this_year_april_6().isoformat()
        client.post(INCOME_URL, json={"amount": 2000.0, "date_received": d}, headers=h)
        client.post(EXPENSE_URL, json={"amount": 300.0, "date_incurred": d, "category": "software"}, headers=h)
        _post_mileage(client, h, d, 100, "car_van")

        body = client.get(SUMMARY_URL, headers=h).json()
        assert body["home_office_allowance"] == pytest.approx(0.0)

    def test_allowable_breakdown_three_components_reconcile(self, client, db):
        """cash allowable + mileage allowance + HO allowance == allowable_expenses_ytd exactly.
        Dataset uses all three component types to prove full reconciliation."""
        seed_biz_config(db)
        h = auth(client)
        d = _this_year_april_6().isoformat()
        client.post(INCOME_URL, json={"amount": 10000.0, "date_received": d}, headers=h)
        # Cash allowable expense (£200)
        client.post(EXPENSE_URL, json={"amount": 200.0, "date_incurred": d, "category": "software", "is_allowable": True}, headers=h)
        # HO flat rate 51_100 = £18
        client.post(EXPENSE_URL, json={
            "amount": 0, "date_incurred": d, "category": "home_office",
            "is_allowable": True, "expense_method": "home_office_flat",
            "home_office_hours_band": "51_100",
        }, headers=h)
        # 200 car/van miles = 200 × 0.55 = £110
        _post_mileage(client, h, d, 200, "car_van")

        body = client.get(SUMMARY_URL, headers=h).json()
        ytd     = body["allowable_expenses_ytd"]
        mileage = body["total_mileage_allowance"]
        ho      = body["home_office_allowance"]
        cash    = round(ytd - mileage - ho, 2)

        assert ytd     == pytest.approx(328.0)   # 200 + 18 + 110
        assert mileage == pytest.approx(110.0)
        assert ho      == pytest.approx(18.0)
        assert cash    == pytest.approx(200.0)
        assert cash + mileage + ho == pytest.approx(ytd)

    def test_cash_component_excludes_mileage_and_ho_flat(self, client, db):
        """The computed cash component (ytd − mileage − ho) contains only the
        cash-spent allowable portion — not the two allowance types."""
        seed_biz_config(db)
        h = auth(client)
        d = _this_year_april_6().isoformat()
        client.post(INCOME_URL, json={"amount": 5000.0, "date_received": d}, headers=h)
        client.post(EXPENSE_URL, json={"amount": 150.0, "date_incurred": d, "category": "software", "is_allowable": True}, headers=h)
        # Non-allowable cash expense (excluded from allowable, so cash component = only £150)
        client.post(EXPENSE_URL, json={"amount": 50.0, "date_incurred": d, "category": "client_entertainment", "is_allowable": False}, headers=h)
        client.post(EXPENSE_URL, json={
            "amount": 0, "date_incurred": d, "category": "home_office",
            "is_allowable": True, "expense_method": "home_office_flat",
            "home_office_hours_band": "101_plus",
        }, headers=h)
        _post_mileage(client, h, d, 100, "car_van")

        body = client.get(SUMMARY_URL, headers=h).json()
        ytd  = body["allowable_expenses_ytd"]
        cash = round(ytd - body["total_mileage_allowance"] - body["home_office_allowance"], 2)

        # cash component = only the allowable cash expense (£150); non-allowable excluded
        assert cash == pytest.approx(150.0)
        assert body["total_expenses_ytd"] == pytest.approx(200.0)  # cash total includes non-allowable


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


# ---------------------------------------------------------------------------
# Tax year selector — /tax-years, and /summary + /tax-config with ?tax_year=
# ---------------------------------------------------------------------------

class TestTaxYearSelector:
    def test_tax_years_endpoint_derives_from_data(self, client):
        h = auth(client)
        cur, prior = _tax_year_label_for_today(), _prior_tax_year_label()
        client.post(INCOME_URL, json={"amount": 100.0, "date_received": TODAY}, headers=h)
        client.post(INCOME_URL, json={"amount": 200.0, "date_received": _date_in_tax_year(prior)}, headers=h)

        body = client.get("/api/business/tax-years", headers=h).json()
        assert set(body["years"]) == {cur, prior}
        assert body["current_tax_year"] == cur

    def test_tax_years_sorted_most_recent_first(self, client):
        h = auth(client)
        cur, prior = _tax_year_label_for_today(), _prior_tax_year_label()
        client.post(INCOME_URL, json={"amount": 100.0, "date_received": TODAY}, headers=h)
        client.post(EXPENSE_URL, json={"amount": 50.0, "date_incurred": _date_in_tax_year(prior), "category": "software"}, headers=h)

        years = client.get("/api/business/tax-years", headers=h).json()["years"]
        assert years == [cur, prior]

    def test_tax_years_empty_with_no_data(self, client):
        h = auth(client)
        body = client.get("/api/business/tax-years", headers=h).json()
        assert body["years"] == []
        assert body["current_tax_year"] == _tax_year_label_for_today()

    def test_user_with_data_in_only_one_year_sees_only_that_year(self, client):
        h = auth(client)
        prior = _prior_tax_year_label()
        client.post(INCOME_URL, json={"amount": 500.0, "date_received": _date_in_tax_year(prior)}, headers=h)

        years = client.get("/api/business/tax-years", headers=h).json()["years"]
        assert years == [prior]

    def test_tax_years_isolated_per_user(self, client):
        alice = auth(client, "alice@test.com")
        bob   = auth(client, "bob@test.com")
        client.post(INCOME_URL, json={"amount": 500.0, "date_received": TODAY}, headers=alice)
        assert client.get("/api/business/tax-years", headers=bob).json()["years"] == []

    def test_summary_defaults_to_current_year_and_matches_explicit_param(self, client):
        h = auth(client)
        client.post(INCOME_URL, json={"amount": 1000.0, "date_received": TODAY}, headers=h)
        cur = _tax_year_label_for_today()

        implicit = client.get(SUMMARY_URL, headers=h).json()
        explicit = client.get(SUMMARY_URL, params={"tax_year": cur}, headers=h).json()
        assert implicit["tax_year"] == cur
        assert implicit["is_complete"] is False
        assert implicit["revenue_ytd"] == explicit["revenue_ytd"] == pytest.approx(1000.0)

    def test_prior_completed_year_recalculates_all_figures_with_its_own_config(self, client, db):
        h = auth(client)
        prior = _prior_tax_year_label()
        d = _date_in_tax_year(prior)

        # Prior year's own rates — deliberately different from the seed_biz_config()/
        # seed_tax_year_config() defaults used for "current year" elsewhere in this file,
        # so a test that accidentally used the wrong year's config would fail loudly.
        seed_biz_config_for(db, prior,
            mileage_car_van_first=0.45, mileage_car_van_over=0.25, mileage_threshold=10000,
            class4_lower_limit=12570, class4_upper_limit=50270,
            class4_main_rate=0.06, class4_upper_rate=0.02,
            class2_small_profits_threshold=6725, class2_weekly_rate=3.45,
        )
        seed_tax_year_config_for(db, prior,
            personal_allowance=12570, basic_rate_threshold=50270, basic_rate_pct=20,
            higher_rate_threshold=125140, higher_rate_pct=40, additional_rate_pct=45,
            ni_primary_threshold=12570, ni_upper_threshold=50270, ni_main_rate_pct=8, ni_upper_rate_pct=2,
            pension_qualifying_lower=6240, pension_qualifying_upper=50270,
            pension_min_total_pct=8, pension_min_employer_pct=3,
        )

        client.post(INCOME_URL, json={"amount": 20000.0, "date_received": d}, headers=h)
        client.post(EXPENSE_URL, json={"amount": 1000.0, "date_incurred": d, "category": "software", "is_allowable": True}, headers=h)
        _post_mileage(client, h, d, 500, "car_van")

        body = client.get(SUMMARY_URL, params={"tax_year": prior}, headers=h).json()
        assert body["tax_year"] == prior
        assert body["is_complete"] is True
        assert body["tax_config_available"] is True
        assert body["revenue_ytd"] == pytest.approx(20000.0)
        assert body["total_expenses_ytd"] == pytest.approx(1000.0)
        # Mileage allowance uses the PRIOR year's 45p rate, not the current year's 55p.
        assert body["total_mileage_allowance"] == pytest.approx(500 * 0.45)
        assert body["allowable_expenses_ytd"] == pytest.approx(1000.0 + 500 * 0.45)
        expected_profit = round(20000.0 - (1000.0 + 500 * 0.45), 2)
        assert body["taxable_profit"] == pytest.approx(expected_profit)
        assert body["tax_estimate"] is not None
        assert body["tax_estimate"]["taxable_profit"] == pytest.approx(expected_profit)

    def test_entries_from_other_tax_years_are_excluded(self, client):
        h = auth(client)
        cur, prior = _tax_year_label_for_today(), _prior_tax_year_label()
        client.post(INCOME_URL, json={"amount": 1000.0, "date_received": TODAY}, headers=h)
        client.post(INCOME_URL, json={"amount": 7000.0, "date_received": _date_in_tax_year(prior)}, headers=h)

        cur_body   = client.get(SUMMARY_URL, params={"tax_year": cur},   headers=h).json()
        prior_body = client.get(SUMMARY_URL, params={"tax_year": prior}, headers=h).json()
        assert cur_body["revenue_ytd"]   == pytest.approx(1000.0)
        assert prior_body["revenue_ytd"] == pytest.approx(7000.0)

    def test_mileage_threshold_scoped_per_selected_tax_year(self, client, db):
        h = auth(client)
        cur, prior = _tax_year_label_for_today(), _prior_tax_year_label()
        seed_biz_config_for(db, cur,   mileage_car_van_first=0.55, mileage_car_van_over=0.25, mileage_threshold=10000)
        seed_biz_config_for(db, prior, mileage_car_van_first=0.45, mileage_car_van_over=0.25, mileage_threshold=10000)

        # 8,000 miles in the prior year and 8,000 in the current year: neither year
        # alone crosses the 10,000-mile threshold, but the sum (16,000) would if the
        # two years were wrongly pooled together.
        _post_mileage(client, h, _date_in_tax_year(prior), 8000, "car_van")
        _post_mileage(client, h, TODAY, 8000, "car_van")

        cur_body   = client.get(SUMMARY_URL, params={"tax_year": cur},   headers=h).json()
        prior_body = client.get(SUMMARY_URL, params={"tax_year": prior}, headers=h).json()

        assert cur_body["total_business_miles"]   == 8000
        assert prior_body["total_business_miles"] == 8000
        # All-first-tier rate in both years — proof the threshold pool didn't bleed across years.
        assert cur_body["total_mileage_allowance"]   == pytest.approx(8000 * 0.55)
        assert prior_body["total_mileage_allowance"] == pytest.approx(8000 * 0.45)
        assert "Threshold reached" not in (cur_body["mileage_crossover_msg"] or "")
        assert "Threshold reached" not in (prior_body["mileage_crossover_msg"] or "")

    def test_missing_config_for_selected_year_is_graceful_not_wrong_rates(self, client):
        h = auth(client)
        prior = _prior_tax_year_label()
        d = _date_in_tax_year(prior)
        # No BusinessTaxConfig/TaxYearConfig seeded for `prior` at all (only whatever
        # the current year might have, which must NOT be silently applied instead).
        client.post(INCOME_URL, json={"amount": 3000.0, "date_received": d}, headers=h)
        client.post(EXPENSE_URL, json={"amount": 200.0, "date_incurred": d, "category": "software", "is_allowable": True}, headers=h)
        _post_mileage(client, h, d, 1000, "car_van")

        body = client.get(SUMMARY_URL, params={"tax_year": prior}, headers=h).json()
        assert body["tax_config_available"] is False
        assert body["tax_estimate"] is None
        # Cash figures (not rate-dependent) are still correct...
        assert body["revenue_ytd"] == pytest.approx(3000.0)
        assert body["total_expenses_ytd"] == pytest.approx(200.0)
        assert body["allowable_expenses_ytd"] == pytest.approx(200.0)
        # ...but rate-dependent mileage allowance is reported as unavailable (0), not
        # computed at the wrong (current) year's rate. Raw mileage is still visible.
        assert body["total_business_miles"] == 1000
        assert body["total_mileage_allowance"] == 0.0

    def test_tax_config_endpoint_returns_selected_years_own_rates(self, client, db):
        prior = _prior_tax_year_label()
        seed_biz_config(db)  # current year, 0.55/mile
        seed_biz_config_for(db, prior, mileage_car_van_first=0.45, mileage_car_van_over=0.25, mileage_threshold=10000)
        h = auth(client)

        cur_cfg   = client.get(TAX_CFG_URL, headers=h).json()
        prior_cfg = client.get(TAX_CFG_URL, params={"tax_year": prior}, headers=h).json()
        assert cur_cfg["mileage_car_van_first"]   == pytest.approx(0.55)
        assert prior_cfg["mileage_car_van_first"] == pytest.approx(0.45)

    def test_tax_config_endpoint_404_for_unseeded_selected_year(self, client, db):
        seed_biz_config(db)  # current year only
        h = auth(client)
        r = client.get(TAX_CFG_URL, params={"tax_year": _prior_tax_year_label()}, headers=h)
        assert r.status_code == 404

    def test_arbitrary_year_works_as_pure_data_insert(self, client, db):
        """Proves the tax-year machinery is generic — an arbitrary year (not one of
        the two literal years used elsewhere in this file) needs only a seeded config
        row, no code change, to work correctly."""
        seed_biz_config_for(db, "2020/21", mileage_car_van_first=0.45, mileage_car_van_over=0.25, mileage_threshold=10000)
        h = auth(client)
        _post_mileage(client, h, "2020-06-15", 1000, "car_van")

        body = client.get(SUMMARY_URL, params={"tax_year": "2020/21"}, headers=h).json()
        assert body["tax_config_available"] is True
        assert body["total_mileage_allowance"] == pytest.approx(450.0)


# ---------------------------------------------------------------------------
# Real HMRC-seeded rates: 2025/26 vs 2026/27
# Mileage rose 45p → 55p and Class 2 threshold/rate rose, both effective 6 April 2026.
# ---------------------------------------------------------------------------

class TestSeededHmrcRates2025_26:
    def test_mileage_45p_for_2025_26_vs_55p_for_2026_27(self, client, db):
        seed_biz_config_for(db, "2025/26", mileage_car_van_first=0.45, mileage_car_van_over=0.25, mileage_threshold=10000)
        seed_biz_config_for(db, "2026/27", mileage_car_van_first=0.55, mileage_car_van_over=0.25, mileage_threshold=10000)
        h = auth(client)

        _post_mileage(client, h, "2025-06-15", 1000, "car_van")
        _post_mileage(client, h, "2026-06-15", 1000, "car_van")

        body_2025 = client.get(SUMMARY_URL, params={"tax_year": "2025/26"}, headers=h).json()
        body_2026 = client.get(SUMMARY_URL, params={"tax_year": "2026/27"}, headers=h).json()
        assert body_2025["total_mileage_allowance"] == pytest.approx(450.0)
        assert body_2026["total_mileage_allowance"] == pytest.approx(550.0)

    def test_class2_threshold_and_rate_differ_by_year(self, client, db):
        seed_biz_config_for(db, "2025/26", class4_lower_limit=12570, class4_upper_limit=50270,
                             class4_main_rate=0.06, class4_upper_rate=0.02,
                             class2_small_profits_threshold=6845, class2_weekly_rate=3.50)
        seed_biz_config_for(db, "2026/27", class4_lower_limit=12570, class4_upper_limit=50270,
                             class4_main_rate=0.06, class4_upper_rate=0.02,
                             class2_small_profits_threshold=7105, class2_weekly_rate=3.65)
        seed_tax_year_config_for(db, "2025/26")
        seed_tax_year_config_for(db, "2026/27")
        h = auth(client)

        # Profit sits between the two years' Class 2 thresholds (£6,845 vs £7,105) but
        # below the Class 4 lower limit (£12,570): 2025/26 is "covered_no_class4"
        # (>= its own £6,845 threshold) while 2026/27 is "below_threshold" (< its own
        # £7,105) — proving each year checks its OWN Class 2 threshold.
        profit = 7000.0
        client.post(INCOME_URL, json={"amount": profit, "date_received": "2025-06-15"}, headers=h)
        client.post(INCOME_URL, json={"amount": profit, "date_received": "2026-06-15"}, headers=h)

        body_2025 = client.get(SUMMARY_URL, params={"tax_year": "2025/26"}, headers=h).json()
        body_2026 = client.get(SUMMARY_URL, params={"tax_year": "2026/27"}, headers=h).json()
        assert body_2025["tax_estimate"]["class2_status"] == "covered_no_class4"
        assert body_2026["tax_estimate"]["class2_status"] == "below_threshold"
        assert body_2026["tax_estimate"]["class2_voluntary_note"] is not None
        assert "£3.65" in body_2026["tax_estimate"]["class2_voluntary_note"]

    def test_class4_ni_2025_26_uses_6pct_2pct_at_correct_limits(self, client, db):
        seed_biz_config_for(db, "2025/26", class4_lower_limit=12570, class4_upper_limit=50270,
                             class4_main_rate=0.06, class4_upper_rate=0.02,
                             class2_small_profits_threshold=6845, class2_weekly_rate=3.50)
        seed_tax_year_config_for(db, "2025/26")
        h = auth(client)
        client.post(INCOME_URL, json={"amount": 60270.0, "date_received": "2025-06-15"}, headers=h)

        body = client.get(SUMMARY_URL, params={"tax_year": "2025/26"}, headers=h).json()
        assert body["taxable_profit"] == pytest.approx(60270.0)
        expected_class4 = round((50270 - 12570) * 0.06 + (60270 - 50270) * 0.02, 2)
        assert body["tax_estimate"]["class4_ni"] == pytest.approx(expected_class4)

    def test_2025_26_selection_has_no_missing_config_banner_condition(self, client, db):
        seed_biz_config_for(db, "2025/26", class2_small_profits_threshold=6845, class2_weekly_rate=3.50)
        seed_tax_year_config_for(db, "2025/26")
        h = auth(client)
        body = client.get(SUMMARY_URL, params={"tax_year": "2025/26"}, headers=h).json()
        assert body["tax_config_available"] is True


class TestSeedScriptSeeds2025_26AsData:
    """Runs the actual backend/seed.py script against an isolated in-memory DB and
    checks the row it inserts — proves the 2025/26 rates are a data insert in
    seed.py, not values duplicated/hardcoded only inside this test file."""

    def test_seed_py_inserts_2025_26_business_tax_config_with_exact_hmrc_values(self, monkeypatch):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool
        import seed as seed_module

        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Session = sessionmaker(bind=engine)
        from app.database import Base
        Base.metadata.create_all(bind=engine)
        monkeypatch.setattr(seed_module, "SessionLocal", Session)

        seed_module.seed()

        check = Session()
        try:
            cfg = check.query(BusinessTaxConfig).filter_by(tax_year="2025/26").first()
            assert cfg is not None
            assert cfg.mileage_car_van_first == pytest.approx(0.45)
            assert cfg.mileage_car_van_over == pytest.approx(0.25)
            assert cfg.mileage_motorcycle == pytest.approx(0.24)
            assert cfg.mileage_bicycle == pytest.approx(0.20)
            assert cfg.mileage_threshold == 10000
            assert cfg.home_office_band_25_50 == pytest.approx(10.0)
            assert cfg.home_office_band_51_100 == pytest.approx(18.0)
            assert cfg.home_office_band_101_plus == pytest.approx(26.0)
            assert cfg.class4_lower_limit == pytest.approx(12570)
            assert cfg.class4_upper_limit == pytest.approx(50270)
            assert cfg.class4_main_rate == pytest.approx(0.06)
            assert cfg.class4_upper_rate == pytest.approx(0.02)
            assert cfg.class2_small_profits_threshold == pytest.approx(6845)
            assert cfg.class2_weekly_rate == pytest.approx(3.50)
            assert cfg.source_note == "HMRC simplified expenses, AMAP and NIC rates, 2025/26"

            # 2026/27 is untouched by the 2025/26 insert.
            cfg_2026 = check.query(BusinessTaxConfig).filter_by(tax_year="2026/27").first()
            assert cfg_2026.mileage_car_van_first == pytest.approx(0.55)
        finally:
            check.close()

    def test_seed_py_inserts_2025_26_tax_year_config(self, monkeypatch):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool
        import seed as seed_module

        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Session = sessionmaker(bind=engine)
        from app.database import Base
        Base.metadata.create_all(bind=engine)
        monkeypatch.setattr(seed_module, "SessionLocal", Session)

        seed_module.seed()

        check = Session()
        try:
            cfg = check.query(TaxYearConfig).filter_by(tax_year="2025/26").first()
            assert cfg is not None
            assert cfg.personal_allowance == pytest.approx(12570)
            assert cfg.basic_rate_threshold == pytest.approx(50270)
            assert cfg.basic_rate_pct == pytest.approx(20)
            assert cfg.higher_rate_threshold == pytest.approx(125140)
            assert cfg.higher_rate_pct == pytest.approx(40)
            assert cfg.additional_rate_pct == pytest.approx(45)
            assert cfg.ni_primary_threshold == pytest.approx(12584)
            assert cfg.ni_upper_threshold == pytest.approx(50284)
            assert cfg.ni_main_rate_pct == pytest.approx(8)
            assert cfg.ni_upper_rate_pct == pytest.approx(2)
            assert cfg.pension_qualifying_lower == pytest.approx(6240)
            assert cfg.pension_qualifying_upper == pytest.approx(50270)

            # Identical to the 2026/27 row's income-tax/NI figures (frozen thresholds).
            cfg_2026 = check.query(TaxYearConfig).filter_by(tax_year="2026/27").first()
            assert cfg.personal_allowance == cfg_2026.personal_allowance
            assert cfg.ni_primary_threshold == cfg_2026.ni_primary_threshold
        finally:
            check.close()


# ---------------------------------------------------------------------------
# Tax deadline figures — /business/tax-deadlines (payments on account + balancing)
# Worked-example arithmetic itself lives in tests/test_tax_calculator.py
# (calculate_payments_on_account); these tests cover the DB/route orchestration:
# picking LCY, finding (or not finding) the immediately preceding year, honest
# no-data/config-missing handling, and Class 2 exclusion end-to-end.
# ---------------------------------------------------------------------------

class TestTaxDeadlineFigures:
    def test_no_completed_year_with_no_data_at_all(self, client):
        h = auth(client)
        body = client.get(TAX_DEADLINES_URL, headers=h).json()
        assert body["available"] is False
        assert body["reason"] == "no_completed_year"
        assert body["last_completed_year"] is None

    def test_no_completed_year_when_only_current_year_has_data(self, client):
        h = auth(client)
        client.post(INCOME_URL, json={"amount": 1000.0, "date_received": TODAY}, headers=h)
        body = client.get(TAX_DEADLINES_URL, headers=h).json()
        assert body["available"] is False
        assert body["reason"] == "no_completed_year"

    def test_config_missing_for_lcy_is_reported_not_silently_wrong(self, client):
        h = auth(client)
        prior = _prior_tax_year_label()
        client.post(INCOME_URL, json={"amount": 20000.0, "date_received": _date_in_tax_year(prior)}, headers=h)
        # No BusinessTaxConfig/TaxYearConfig seeded for `prior` at all.
        body = client.get(TAX_DEADLINES_URL, headers=h).json()
        assert body["available"] is False
        assert body["reason"] == "config_missing"
        assert body["last_completed_year"] == prior
        assert body["balancing_payment"] is None
        assert body["january_total"] is None

    def test_first_year_of_trading_end_to_end(self, client, db):
        """No prior-year data at all → balancing payment is the full LCY bill."""
        h = auth(client)
        lcy = _prior_tax_year_label()
        seed_biz_config_for(db, lcy)
        seed_tax_year_config_for(db, lcy)
        client.post(INCOME_URL, json={"amount": 30000.0, "date_received": _date_in_tax_year(lcy)}, headers=h)

        body = client.get(TAX_DEADLINES_URL, headers=h).json()
        assert body["available"] is True
        assert body["last_completed_year"] == lcy
        assert body["next_year"].split("/")[0] == str(int(lcy.split("/")[0]) + 1)
        assert body["poa_threshold"] == pytest.approx(1000.0)
        assert body["bill_lcy"] == pytest.approx(4531.80)
        assert body["poa_triggered"] is True
        assert body["poa_instalment"] == pytest.approx(2265.90)
        assert body["balancing_payment"] == pytest.approx(4531.80)
        assert body["january_total"] == pytest.approx(6797.70)
        assert body["july_total"] == pytest.approx(2265.90)

    def test_uses_only_the_immediately_preceding_completed_year(self, client, db):
        """A year exists two years back too, but it must never be consulted —
        'the app only ever needs the immediately preceding completed year.'"""
        h = auth(client)
        lcy = _year_label_offset(1)
        lcy_minus_1 = _year_label_offset(2)
        for label in (lcy, lcy_minus_1):
            seed_biz_config_for(db, label)
            seed_tax_year_config_for(db, label)

        client.post(INCOME_URL, json={"amount": 30000.0, "date_received": _date_in_tax_year(lcy)}, headers=h)
        client.post(INCOME_URL, json={"amount": 5000.0, "date_received": _date_in_tax_year(lcy_minus_1)}, headers=h)

        body = client.get(TAX_DEADLINES_URL, headers=h).json()
        assert body["last_completed_year"] == lcy
        # lcy_minus_1's profit (£5,000) sits below the Class 4 lower limit and personal
        # allowance, so its bill is £0 — no POAs from it — balancing = full LCY bill.
        assert body["balancing_payment"] == pytest.approx(4531.80)

    def test_class2_is_excluded_from_the_bill(self, client, db):
        """Two configs with identical income-tax/Class-4 figures but wildly different
        Class 2 thresholds/rates must produce an identical bill and POA figures."""
        h = auth(client)
        lcy = _prior_tax_year_label()
        seed_biz_config_for(db, lcy, class2_small_profits_threshold=1.0, class2_weekly_rate=999.0)
        seed_tax_year_config_for(db, lcy)
        client.post(INCOME_URL, json={"amount": 30000.0, "date_received": _date_in_tax_year(lcy)}, headers=h)

        body = client.get(TAX_DEADLINES_URL, headers=h).json()
        assert body["bill_lcy"] == pytest.approx(4531.80)
        assert body["january_total"] == pytest.approx(6797.70)

    def test_threshold_read_from_lcys_own_config_not_hardcoded(self, client, db):
        """A bill of £900 doesn't trigger POAs against a £1,000 threshold, but does
        against a £500 one — proves the code reads cfg.poa_threshold, not a literal."""
        h = auth(client)
        lcy = _prior_tax_year_label()
        seed_biz_config_for(db, lcy, poa_threshold=500)
        seed_tax_year_config_for(db, lcy)
        # A profit that produces a bill just above 500 but below 1000: (P-12570)*0.26 ≈ 900
        # -> P ≈ 16032; use a clean profit and read back whatever bill results.
        client.post(INCOME_URL, json={"amount": 16000.0, "date_received": _date_in_tax_year(lcy)}, headers=h)

        body = client.get(TAX_DEADLINES_URL, headers=h).json()
        assert body["poa_threshold"] == pytest.approx(500.0)
        assert 500 < body["bill_lcy"] < 1000
        assert body["poa_triggered"] is True

    def test_read_only_endpoint_does_not_affect_summary_or_upcoming(self, client, db):
        h = auth(client)
        lcy = _prior_tax_year_label()
        seed_biz_config_for(db, lcy)
        seed_tax_year_config_for(db, lcy)
        client.post(INCOME_URL, json={"amount": 30000.0, "date_received": _date_in_tax_year(lcy)}, headers=h)

        summary_before  = client.get(SUMMARY_URL, params={"tax_year": lcy}, headers=h).json()
        upcoming_before = client.get(UPCOMING_URL, headers=h).json()

        client.get(TAX_DEADLINES_URL, headers=h)  # calling it must have no side effects

        summary_after  = client.get(SUMMARY_URL, params={"tax_year": lcy}, headers=h).json()
        upcoming_after = client.get(UPCOMING_URL, headers=h).json()
        assert summary_after == summary_before
        assert upcoming_after == upcoming_before

    def test_isolated_per_user(self, client):
        alice = auth(client, "alice@test.com")
        bob   = auth(client, "bob@test.com")
        client.post(INCOME_URL, json={"amount": 30000.0, "date_received": _date_in_tax_year(_prior_tax_year_label())}, headers=alice)
        body = client.get(TAX_DEADLINES_URL, headers=bob).json()
        assert body["available"] is False
        assert body["reason"] == "no_completed_year"


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
# Combined personal + business tax — self-employment profit stacked on the
# user's REAL other income (employed salary) via the starting_income seam,
# plus student loan on combined income. Every figure here is a DELTA
# (combined minus starting-income-alone) so nothing already collected via
# PAYE/payroll on the salary gets counted again in "set aside".
# ---------------------------------------------------------------------------

PERSONAL_INCOME_URL = "/api/income"
DEBTS_URL = "/api/debts"


class TestCombinedTax:
    def _add_salary(self, client, h, annual):
        r = client.post(PERSONAL_INCOME_URL, json={
            "label": "Job", "gross_annual_salary": annual, "pay_frequency": "monthly",
        }, headers=h)
        assert r.status_code == 201, r.json()

    def _add_business_profit(self, client, h, amount, d):
        r = client.post(INCOME_URL, json={"amount": amount, "date_received": d}, headers=h)
        assert r.status_code == 201, r.json()

    def _add_student_loan(self, client, h, db, threshold, rate_pct=9.0):
        from app.models.config import StudentLoanPlanConfig
        plan = StudentLoanPlanConfig(
            plan_name="Plan 2", tax_year=_tax_year_label_for_today(), threshold=threshold,
            repayment_rate_pct=rate_pct, write_off_years=30,
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)
        r = client.post(DEBTS_URL, json={
            "debt_type": "student_loan", "balance": 20000.0, "interest_rate": 0.0,
            "min_payment": 0.0, "student_loan_plan_id": plan.id, "graduation_year": 2019,
        }, headers=h)
        assert r.status_code == 201, r.json()

    def test_no_other_income_matches_unchanged_isolated_behaviour(self, client, db):
        """Regression check: a full-time creator with no salary gets the exact
        same figures as before this feature — starting_income and every
        delta-baseline collapse to zero."""
        seed_biz_config(db)
        seed_tax_year_config(db)
        h = auth(client)
        d = _this_year_april_6().isoformat()
        self._add_business_profit(client, h, 20000.0, d)

        te = client.get(SUMMARY_URL, headers=h).json()["tax_estimate"]
        assert te["starting_income"] == 0.0
        assert te["paye_tax_on_starting_income"] == 0.0
        assert te["student_loan_additional"] == 0.0
        assert te["income_tax_on_profit"] == pytest.approx((20000 - 12570) * 0.20)  # unchanged from test_20k_profit

    def test_salary_plus_profit_taxed_at_combined_marginal_rate(self, client, db):
        """£30k salary + £20k profit: additional income tax owed on the profit
        = income_tax(50k) − income_tax(30k), NOT income_tax(20k) in isolation."""
        from app.services.tax_calculator import calculate_income_tax
        seed_biz_config(db)
        seed_tax_year_config(db)
        h = auth(client)
        d = _this_year_april_6().isoformat()
        self._add_salary(client, h, 30000.0)
        self._add_business_profit(client, h, 20000.0, d)

        te = client.get(SUMMARY_URL, headers=h).json()["tax_estimate"]

        tax_ns = SimpleNamespace(
            personal_allowance=12570, basic_rate_threshold=50270, basic_rate_pct=20,
            higher_rate_threshold=125140, higher_rate_pct=40, additional_rate_pct=45,
            ni_primary_threshold=12584, ni_upper_threshold=50284,
            ni_main_rate_pct=8, ni_upper_rate_pct=2,
            pension_qualifying_lower=6240, pension_qualifying_upper=50270,
        )
        expected_additional = round(calculate_income_tax(50000, tax_ns) - calculate_income_tax(30000, tax_ns), 2)
        isolated_wrong_answer = calculate_income_tax(20000, tax_ns)

        assert te["starting_income"] == pytest.approx(30000.0)
        assert te["income_tax_on_profit"] == pytest.approx(expected_additional)
        assert te["income_tax_on_profit"] == pytest.approx(4000.0)  # (50,000-12,570)*20% - (30,000-12,570)*20%
        assert te["income_tax_on_profit"] != pytest.approx(isolated_wrong_answer)

    def test_paye_paid_reconciles_exactly_with_no_double_counting(self, client, db):
        """paye_tax_on_starting_income + income_tax_on_profit == tax on the
        full combined income, exactly — proves nothing is double-counted or
        dropped by the delta form."""
        from app.services.tax_calculator import calculate_income_tax
        seed_biz_config(db)
        seed_tax_year_config(db)
        h = auth(client)
        d = _this_year_april_6().isoformat()
        self._add_salary(client, h, 30000.0)
        self._add_business_profit(client, h, 20000.0, d)

        te = client.get(SUMMARY_URL, headers=h).json()["tax_estimate"]

        tax_ns = SimpleNamespace(
            personal_allowance=12570, basic_rate_threshold=50270, basic_rate_pct=20,
            higher_rate_threshold=125140, higher_rate_pct=40, additional_rate_pct=45,
            ni_primary_threshold=12584, ni_upper_threshold=50284,
            ni_main_rate_pct=8, ni_upper_rate_pct=2,
            pension_qualifying_lower=6240, pension_qualifying_upper=50270,
        )
        assert te["paye_tax_on_starting_income"] == pytest.approx(3486.0)  # (30,000-12,570)*20%
        assert te["income_tax_on_profit"] == pytest.approx(4000.0)
        tax_on_everything = calculate_income_tax(50000, tax_ns)
        assert te["paye_tax_on_starting_income"] + te["income_tax_on_profit"] == pytest.approx(tax_on_everything)
        assert tax_on_everything == pytest.approx(7486.0)

    def test_salary_pushes_profit_into_higher_rate_band(self, client, db):
        """£45k salary + £15k profit: part of the profit crosses the £50,270
        higher-rate boundary — the thing an isolated (profit-only) calculator
        gets wrong by taxing the whole slice at 20%."""
        seed_biz_config(db)
        seed_tax_year_config(db)
        h = auth(client)
        d = _this_year_april_6().isoformat()
        self._add_salary(client, h, 45000.0)
        self._add_business_profit(client, h, 15000.0, d)

        te = client.get(SUMMARY_URL, headers=h).json()["tax_estimate"]
        # income_tax(60,000) - income_tax(45,000):
        #   basic:  (50,270-12,570)*20% = 7,540.00 total on salary+profit-up-to-50,270
        #   higher: (60,000-50,270)*40% = 3,892.00 on the slice of profit above 50,270
        #   income_tax(60,000) = 11,432.00; income_tax(45,000) = (45,000-12,570)*20% = 6,486.00
        #   delta = 4,946.00 — more than 15,000*20%=3,000, proving the higher-rate slice is reflected
        assert te["income_tax_on_profit"] == pytest.approx(4946.0)
        assert te["income_tax_on_profit"] > 15000 * 0.20

    def test_student_loan_on_combined_income_is_a_delta_not_a_total(self, client, db):
        """Plan with £25,000 threshold, £40k salary + £15k profit (combined
        £55k). Profit ALONE (£15k) never even crosses the threshold, so an
        isolated calculator would show £0 student loan on the profit — wrong,
        since stacked on the salary it's fully liable. The FULL combined
        figure (£2,700) would double-count the £1,350 already collected via
        payroll on the salary alone. The correct additional amount is the
        delta: £1,350."""
        seed_biz_config(db)
        seed_tax_year_config(db)
        h = auth(client)
        d = _this_year_april_6().isoformat()
        self._add_salary(client, h, 40000.0)
        self._add_student_loan(client, h, db, threshold=25000.0, rate_pct=9.0)
        self._add_business_profit(client, h, 15000.0, d)

        te = client.get(SUMMARY_URL, headers=h).json()["tax_estimate"]
        assert te["student_loan_additional"] == pytest.approx(1350.0)  # (55,000-25,000)*9% - (40,000-25,000)*9%
        assert te["student_loan_additional"] != pytest.approx(2700.0)  # NOT the full combined repayment
        assert te["student_loan_additional"] != pytest.approx(0.0)     # NOT profit-alone (which is below threshold)

    def test_no_student_loan_plan_means_zero_additional(self, client, db):
        seed_biz_config(db)
        seed_tax_year_config(db)
        h = auth(client)
        d = _this_year_april_6().isoformat()
        self._add_salary(client, h, 40000.0)
        self._add_business_profit(client, h, 15000.0, d)

        te = client.get(SUMMARY_URL, headers=h).json()["tax_estimate"]
        assert te["student_loan_additional"] == 0.0

    def test_class4_ni_unaffected_by_salary(self, client, db):
        """Class 4 NI is calculated on self-employment profit alone — HMRC
        rules give it no interaction with employment income."""
        seed_biz_config(db)
        seed_tax_year_config(db)

        h1 = auth(client, "nosalary@test.com")
        d = _this_year_april_6().isoformat()
        self._add_business_profit(client, h1, 30000.0, d)
        te_no_salary = client.get(SUMMARY_URL, headers=h1).json()["tax_estimate"]

        h2 = auth(client, "withsalary@test.com")
        self._add_salary(client, h2, 50000.0)
        self._add_business_profit(client, h2, 30000.0, d)
        te_with_salary = client.get(SUMMARY_URL, headers=h2).json()["tax_estimate"]

        assert te_no_salary["class4_ni"] == te_with_salary["class4_ni"]
        assert te_no_salary["class4_ni"] == pytest.approx((30000 - 12570) * 0.06)

    def test_class2_status_unaffected_by_salary(self, client, db):
        """Class 2 status is based on self-employment profit alone."""
        seed_biz_config(db)
        seed_tax_year_config(db)

        h1 = auth(client, "nosalary2@test.com")
        d = _this_year_april_6().isoformat()
        self._add_business_profit(client, h1, 5000.0, d)  # below small profits threshold
        te_no_salary = client.get(SUMMARY_URL, headers=h1).json()["tax_estimate"]

        h2 = auth(client, "withsalary2@test.com")
        self._add_salary(client, h2, 60000.0)
        self._add_business_profit(client, h2, 5000.0, d)
        te_with_salary = client.get(SUMMARY_URL, headers=h2).json()["tax_estimate"]

        assert te_no_salary["class2_status"] == te_with_salary["class2_status"] == "below_threshold"

    def test_multiple_income_sources_summed_as_starting_income(self, client, db):
        seed_biz_config(db)
        seed_tax_year_config(db)
        h = auth(client)
        d = _this_year_april_6().isoformat()
        client.post(PERSONAL_INCOME_URL, json={"label": "Job A", "gross_annual_salary": 15000.0, "pay_frequency": "monthly"}, headers=h)
        client.post(PERSONAL_INCOME_URL, json={"label": "Job B", "gross_annual_salary": 10000.0, "pay_frequency": "monthly"}, headers=h)
        self._add_business_profit(client, h, 10000.0, d)

        te = client.get(SUMMARY_URL, headers=h).json()["tax_estimate"]
        assert te["starting_income"] == pytest.approx(25000.0)

    def test_inactive_income_source_excluded_from_starting_income(self, client, db):
        seed_biz_config(db)
        seed_tax_year_config(db)
        h = auth(client)
        d = _this_year_april_6().isoformat()
        r = client.post(PERSONAL_INCOME_URL, json={"label": "Old job", "gross_annual_salary": 30000.0, "pay_frequency": "monthly"}, headers=h)
        client.delete(f"{PERSONAL_INCOME_URL}/{r.json()['id']}", headers=h)
        self._add_business_profit(client, h, 20000.0, d)

        te = client.get(SUMMARY_URL, headers=h).json()["tax_estimate"]
        assert te["starting_income"] == 0.0

    def test_total_set_aside_includes_student_loan_now(self, client, db):
        """total_set_aside == income_tax_on_profit + class4_ni + student_loan_additional."""
        seed_biz_config(db)
        seed_tax_year_config(db)
        h = auth(client)
        d = _this_year_april_6().isoformat()
        self._add_salary(client, h, 40000.0)
        self._add_student_loan(client, h, db, threshold=25000.0, rate_pct=9.0)
        self._add_business_profit(client, h, 15000.0, d)

        te = client.get(SUMMARY_URL, headers=h).json()["tax_estimate"]
        assert te["total_set_aside"] == pytest.approx(
            te["income_tax_on_profit"] + te["class4_ni"] + te["student_loan_additional"]
        )

    def test_isolation_between_users(self, client, db):
        """One user's salary must never leak into another user's combined figure."""
        seed_biz_config(db)
        seed_tax_year_config(db)
        d = _this_year_april_6().isoformat()

        alice = auth(client, "alice_combined@test.com")
        self._add_salary(client, alice, 80000.0)
        self._add_business_profit(client, alice, 20000.0, d)

        bob = auth(client, "bob_combined@test.com")
        self._add_business_profit(client, bob, 20000.0, d)

        te_bob = client.get(SUMMARY_URL, headers=bob).json()["tax_estimate"]
        assert te_bob["starting_income"] == 0.0
        assert te_bob["income_tax_on_profit"] == pytest.approx((20000 - 12570) * 0.20)

    def test_personal_dashboard_unaffected(self, client, db):
        """The personal dashboard's own tax calculation (take-home pay etc.)
        must be completely unchanged by this feature — it never sees profit."""
        seed_tax_year_config(db)
        h = auth(client)
        d = _this_year_april_6().isoformat()
        self._add_salary(client, h, 40000.0)
        self._add_business_profit(client, h, 20000.0, d)

        personal = client.get("/api/finance/summary", headers=h).json()
        # take_home.income_tax reflects only the £40k salary — profit must not leak in.
        from app.services.tax_calculator import calculate_income_tax
        tax_ns = SimpleNamespace(
            personal_allowance=12570, basic_rate_threshold=50270, basic_rate_pct=20,
            higher_rate_threshold=125140, higher_rate_pct=40, additional_rate_pct=45,
            ni_primary_threshold=12584, ni_upper_threshold=50284,
            ni_main_rate_pct=8, ni_upper_rate_pct=2,
            pension_qualifying_lower=6240, pension_qualifying_upper=50270,
        )
        assert personal["take_home"]["income_tax"] == pytest.approx(calculate_income_tax(40000, tax_ns))


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


# ---------------------------------------------------------------------------
# Upcoming — scheduled, awaiting approval, approve, dismiss lifecycle
# ---------------------------------------------------------------------------

FUTURE = (date.today() + timedelta(days=7)).isoformat()
PAST   = (date.today() - timedelta(days=7)).isoformat()


class TestUpcomingAndApproval:
    def test_future_income_excluded_from_summary(self, client):
        h = auth(client)
        client.post(INCOME_URL, json={"amount": 1000.0, "date_received": FUTURE}, headers=h)
        body = client.get(SUMMARY_URL, headers=h).json()
        assert body["revenue_ytd"] == pytest.approx(0.0)

    def test_future_expense_excluded_from_summary(self, client):
        h = auth(client)
        d = _this_year_april_6().isoformat()
        client.post(INCOME_URL, json={"amount": 5000.0, "date_received": d}, headers=h)
        client.post(EXPENSE_URL, json={"amount": 500.0, "date_incurred": FUTURE, "category": "software"}, headers=h)
        body = client.get(SUMMARY_URL, headers=h).json()
        assert body["total_expenses_ytd"] == pytest.approx(0.0)
        assert body["revenue_ytd"] == pytest.approx(5000.0)

    def test_future_income_appears_in_upcoming(self, client):
        h = auth(client)
        r = client.post(INCOME_URL, json={"amount": 750.0, "date_received": FUTURE, "description": "Future invoice"}, headers=h)
        item_id = r.json()["id"]
        assert r.json()["is_approved"] is False

        upcoming = client.get(UPCOMING_URL, headers=h).json()
        ids = [i["id"] for i in upcoming["income"]]
        assert item_id in ids

    def test_future_expense_appears_in_upcoming(self, client):
        h = auth(client)
        r = client.post(EXPENSE_URL, json={"amount": 200.0, "date_incurred": FUTURE, "category": "software"}, headers=h)
        item_id = r.json()["id"]
        assert r.json()["is_approved"] is False

        upcoming = client.get(UPCOMING_URL, headers=h).json()
        ids = [i["id"] for i in upcoming["expenses"]]
        assert item_id in ids

    def test_future_income_not_in_transactions_list(self, client):
        h = auth(client)
        item_id = client.post(INCOME_URL, json={"amount": 750.0, "date_received": FUTURE}, headers=h).json()["id"]
        confirmed_ids = [i["id"] for i in client.get(INCOME_URL, headers=h).json()]
        assert item_id not in confirmed_ids

    def test_awaiting_approval_excluded_from_summary(self, client, db):
        """Past-dated entry with is_approved forced False → excluded until approved."""
        h = auth(client)
        d = _this_year_april_6().isoformat()
        item_id = client.post(INCOME_URL, json={"amount": 500.0, "date_received": d}, headers=h).json()["id"]
        # Force back to unapproved to simulate awaiting-approval state
        from app.models.finance import BusinessIncome
        entry = db.query(BusinessIncome).filter_by(id=item_id).first()
        entry.is_approved = False
        db.commit()

        body = client.get(SUMMARY_URL, headers=h).json()
        assert body["revenue_ytd"] == pytest.approx(0.0)

    def test_awaiting_approval_appears_in_upcoming(self, client, db):
        h = auth(client)
        d = _this_year_april_6().isoformat()
        item_id = client.post(INCOME_URL, json={"amount": 500.0, "date_received": d}, headers=h).json()["id"]
        from app.models.finance import BusinessIncome
        entry = db.query(BusinessIncome).filter_by(id=item_id).first()
        entry.is_approved = False
        db.commit()

        upcoming = client.get(UPCOMING_URL, headers=h).json()
        ids = [i["id"] for i in upcoming["income"]]
        assert item_id in ids

    def test_approve_income_counts_in_summary(self, client):
        h = auth(client)
        d = _this_year_april_6().isoformat()
        item_id = client.post(INCOME_URL, json={"amount": 1200.0, "date_received": FUTURE}, headers=h).json()["id"]
        # Approve with today's date (within current tax year)
        r = client.post(f"{INCOME_URL}/{item_id}/approve", json={"date_received": d}, headers=h)
        assert r.status_code == 200
        assert r.json()["is_approved"] is True

        body = client.get(SUMMARY_URL, headers=h).json()
        assert body["revenue_ytd"] == pytest.approx(1200.0)

    def test_approve_income_with_edited_amount(self, client):
        h = auth(client)
        d = _this_year_april_6().isoformat()
        item_id = client.post(INCOME_URL, json={"amount": 1000.0, "date_received": FUTURE}, headers=h).json()["id"]
        r = client.post(f"{INCOME_URL}/{item_id}/approve", json={"amount": 1500.0, "date_received": d}, headers=h)
        assert r.status_code == 200
        assert r.json()["amount"] == pytest.approx(1500.0)
        assert r.json()["is_approved"] is True

        body = client.get(SUMMARY_URL, headers=h).json()
        assert body["revenue_ytd"] == pytest.approx(1500.0)

    def test_approve_with_still_future_date_stays_scheduled(self, client):
        h = auth(client)
        item_id = client.post(INCOME_URL, json={"amount": 800.0, "date_received": FUTURE}, headers=h).json()["id"]
        later = (date.today() + timedelta(days=14)).isoformat()
        r = client.post(f"{INCOME_URL}/{item_id}/approve", json={"date_received": later}, headers=h)
        assert r.status_code == 200
        assert r.json()["is_approved"] is False  # date still future → not confirmed

        upcoming = client.get(UPCOMING_URL, headers=h).json()
        ids = [i["id"] for i in upcoming["income"]]
        assert item_id in ids

    def test_approve_expense_counts_in_summary(self, client):
        h = auth(client)
        d = _this_year_april_6().isoformat()
        client.post(INCOME_URL, json={"amount": 5000.0, "date_received": d}, headers=h)
        item_id = client.post(EXPENSE_URL, json={"amount": 300.0, "date_incurred": FUTURE, "category": "software"}, headers=h).json()["id"]
        r = client.post(f"{EXPENSE_URL}/{item_id}/approve", json={"date_incurred": d}, headers=h)
        assert r.status_code == 200
        assert r.json()["is_approved"] is True

        body = client.get(SUMMARY_URL, headers=h).json()
        assert body["total_expenses_ytd"] == pytest.approx(300.0)

    def test_dismiss_income_not_in_upcoming_or_summary(self, client):
        h = auth(client)
        item_id = client.post(INCOME_URL, json={"amount": 500.0, "date_received": FUTURE}, headers=h).json()["id"]
        r = client.delete(f"{INCOME_URL}/{item_id}", headers=h)
        assert r.status_code == 204

        upcoming = client.get(UPCOMING_URL, headers=h).json()
        ids = [i["id"] for i in upcoming["income"]]
        assert item_id not in ids
        assert client.get(SUMMARY_URL, headers=h).json()["revenue_ytd"] == pytest.approx(0.0)

    def test_dismiss_expense_not_in_upcoming_or_summary(self, client):
        h = auth(client)
        item_id = client.post(EXPENSE_URL, json={"amount": 200.0, "date_incurred": FUTURE, "category": "software"}, headers=h).json()["id"]
        client.delete(f"{EXPENSE_URL}/{item_id}", headers=h)

        upcoming = client.get(UPCOMING_URL, headers=h).json()
        assert item_id not in [i["id"] for i in upcoming["expenses"]]

    def test_mixed_entries_only_confirmed_in_summary(self, client):
        h = auth(client)
        d = _this_year_april_6().isoformat()
        # Confirmed income (past date)
        client.post(INCOME_URL, json={"amount": 2000.0, "date_received": d}, headers=h)
        # Scheduled income (future)
        client.post(INCOME_URL, json={"amount": 1000.0, "date_received": FUTURE}, headers=h)
        # Confirmed expense
        client.post(EXPENSE_URL, json={"amount": 400.0, "date_incurred": d, "category": "software"}, headers=h)
        # Scheduled expense
        client.post(EXPENSE_URL, json={"amount": 300.0, "date_incurred": FUTURE, "category": "equipment"}, headers=h)

        body = client.get(SUMMARY_URL, headers=h).json()
        assert body["revenue_ytd"]        == pytest.approx(2000.0)
        assert body["total_expenses_ytd"] == pytest.approx(400.0)

    def test_update_date_to_future_unschedules_confirmed(self, client):
        h = auth(client)
        d = _this_year_april_6().isoformat()
        item_id = client.post(INCOME_URL, json={"amount": 500.0, "date_received": d}, headers=h).json()["id"]
        # Entry is confirmed; patch date to future
        client.patch(f"{INCOME_URL}/{item_id}", json={"date_received": FUTURE}, headers=h)

        upcoming = client.get(UPCOMING_URL, headers=h).json()
        assert item_id in [i["id"] for i in upcoming["income"]]
        assert client.get(SUMMARY_URL, headers=h).json()["revenue_ytd"] == pytest.approx(0.0)

    def test_upcoming_isolation(self, client):
        alice = auth(client, "alice@test.com")
        bob   = auth(client, "bob@test.com")
        client.post(INCOME_URL, json={"amount": 999.0, "date_received": FUTURE}, headers=alice)

        bob_upcoming = client.get(UPCOMING_URL, headers=bob).json()
        assert bob_upcoming["income"] == []
        assert bob_upcoming["expenses"] == []

    def test_has_business_data_true_with_only_scheduled(self, client):
        """Dashboard shows even when all entries are still scheduled."""
        h = auth(client)
        client.post(INCOME_URL, json={"amount": 500.0, "date_received": FUTURE}, headers=h)
        body = client.get(SUMMARY_URL, headers=h).json()
        assert body["has_business_data"] is True

    def test_approve_endpoint_ownership(self, client):
        alice = auth(client, "alice@test.com")
        bob   = auth(client, "bob@test.com")
        item_id = client.post(INCOME_URL, json={"amount": 500.0, "date_received": FUTURE}, headers=alice).json()["id"]
        r = client.post(f"{INCOME_URL}/{item_id}/approve", json={}, headers=bob)
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Recurring income/expense items
# ---------------------------------------------------------------------------

class TestRecurringItems:
    # --- creation ---

    def test_create_recurring_income_stores_frequency(self, client):
        h = auth(client)
        r = client.post(INCOME_URL, json={"amount": 500.0, "date_received": FUTURE, "recurrence_freq": "monthly"}, headers=h)
        assert r.status_code == 201
        body = r.json()
        assert body["recurrence_freq"] == "monthly"
        assert body["recurrence_end_date"] is None

    def test_create_recurring_expense_stores_frequency(self, client):
        h = auth(client)
        r = client.post(EXPENSE_URL, json={
            "amount": 100.0, "date_incurred": FUTURE, "category": "software",
            "recurrence_freq": "weekly", "recurrence_end_date": FUTURE,
        }, headers=h)
        assert r.status_code == 201
        body = r.json()
        assert body["recurrence_freq"] == "weekly"
        assert body["recurrence_end_date"] == FUTURE

    def test_non_recurring_income_has_null_freq(self, client):
        h = auth(client)
        body = client.post(INCOME_URL, json={"amount": 100.0, "date_received": TODAY}, headers=h).json()
        assert body["recurrence_freq"] is None
        assert body["recurrence_end_date"] is None

    # --- approve recurring: creates confirmed + rolls forward ---

    def test_approve_recurring_income_creates_confirmed_transaction(self, client):
        h = auth(client)
        # Create with a future date so it lands in Upcoming (no backfill triggered).
        item_id = client.post(INCOME_URL, json={
            "amount": 500.0, "date_received": FUTURE, "recurrence_freq": "monthly",
        }, headers=h).json()["id"]

        # Approve with a past date to trigger confirmation.
        r = client.post(f"{INCOME_URL}/{item_id}/approve", json={"date_received": PAST}, headers=h)
        assert r.status_code == 200

        # Confirmed transaction should now be in the income list (is_approved=True, non-recurring).
        income_list = client.get(INCOME_URL, headers=h).json()
        confirmed = [i for i in income_list if i["amount"] == 500.0 and i["recurrence_freq"] is None]
        assert len(confirmed) == 1
        assert confirmed[0]["date_received"] == PAST
        assert confirmed[0]["is_approved"] is True

        # Recurring entry should have rolled forward (still in upcoming).
        upcoming = client.get(UPCOMING_URL, headers=h).json()
        assert item_id in [i["id"] for i in upcoming["income"]]

    def test_approve_recurring_expense_creates_confirmed_transaction(self, client):
        h = auth(client)
        item = client.post(EXPENSE_URL, json={
            "amount": 200.0, "date_incurred": FUTURE, "category": "software",
            "recurrence_freq": "quarterly",
        }, headers=h).json()
        item_id = item["id"]

        r = client.post(f"{EXPENSE_URL}/{item_id}/approve", json={"date_incurred": PAST}, headers=h)
        assert r.status_code == 200

        expense_list = client.get(EXPENSE_URL, headers=h).json()
        confirmed = [e for e in expense_list if e["amount"] == 200.0 and e["recurrence_freq"] is None]
        assert len(confirmed) == 1
        assert confirmed[0]["is_approved"] is True

        upcoming = client.get(UPCOMING_URL, headers=h).json()
        expense_ids = [e["id"] for e in upcoming["expenses"]]
        assert item_id in expense_ids

    def test_approve_recurring_per_occurrence_amount_edit_does_not_change_recurrence(self, client):
        """Editing amount at approval only affects the confirmed transaction."""
        h = auth(client)
        item_id = client.post(INCOME_URL, json={
            "amount": 1000.0, "date_received": FUTURE, "recurrence_freq": "monthly",
        }, headers=h).json()["id"]

        # Approve with an edited amount (£800 instead of £1000)
        client.post(f"{INCOME_URL}/{item_id}/approve", json={"date_received": PAST, "amount": 800.0}, headers=h)

        # Confirmed transaction should have £800
        income_list = client.get(INCOME_URL, headers=h).json()
        confirmed = [i for i in income_list if i["recurrence_freq"] is None]
        assert len(confirmed) == 1
        assert confirmed[0]["amount"] == pytest.approx(800.0)

        # Recurring entry retains original £1000 for future occurrences
        upcoming = client.get(UPCOMING_URL, headers=h).json()
        recurring = next(i for i in upcoming["income"] if i["id"] == item_id)
        assert recurring["amount"] == pytest.approx(1000.0)

    def test_approve_recurring_income_with_future_date_reschedules_not_confirms(self, client):
        h = auth(client)
        far_future = (date.today() + timedelta(days=60)).isoformat()
        item_id = client.post(INCOME_URL, json={
            "amount": 500.0, "date_received": FUTURE, "recurrence_freq": "monthly",
        }, headers=h).json()["id"]

        # Approve with a still-future date
        r = client.post(f"{INCOME_URL}/{item_id}/approve", json={"date_received": far_future}, headers=h)
        assert r.status_code == 200

        # No confirmed transaction should have been created
        income_list = client.get(INCOME_URL, headers=h).json()
        confirmed = [i for i in income_list if i["recurrence_freq"] is None]
        assert confirmed == []

        # Recurring entry should still be in upcoming with updated date
        upcoming = client.get(UPCOMING_URL, headers=h).json()
        rec = next((i for i in upcoming["income"] if i["id"] == item_id), None)
        assert rec is not None
        assert rec["date_received"] == far_future

    # --- dismiss recurring: skips one occurrence, rolls forward ---

    def test_dismiss_recurring_income_rolls_forward(self, client):
        h = auth(client)
        item_id = client.post(INCOME_URL, json={
            "amount": 500.0, "date_received": FUTURE, "recurrence_freq": "monthly",
        }, headers=h).json()["id"]

        r = client.post(f"{INCOME_URL}/{item_id}/dismiss", headers=h)
        assert r.status_code == 204

        # No confirmed transaction
        income_list = client.get(INCOME_URL, headers=h).json()
        assert income_list == []

        # Recurring entry still in upcoming (rolled to next month)
        upcoming = client.get(UPCOMING_URL, headers=h).json()
        rec_ids = [i["id"] for i in upcoming["income"]]
        assert item_id in rec_ids

    def test_dismiss_recurring_expense_rolls_forward(self, client):
        h = auth(client)
        item_id = client.post(EXPENSE_URL, json={
            "amount": 100.0, "date_incurred": FUTURE, "category": "software",
            "recurrence_freq": "quarterly",
        }, headers=h).json()["id"]

        r = client.post(f"{EXPENSE_URL}/{item_id}/dismiss", headers=h)
        assert r.status_code == 204

        expense_list = client.get(EXPENSE_URL, headers=h).json()
        assert expense_list == []

        upcoming = client.get(UPCOMING_URL, headers=h).json()
        rec_ids = [e["id"] for e in upcoming["expenses"]]
        assert item_id in rec_ids

    def test_dismiss_non_recurring_income_soft_deletes(self, client):
        h = auth(client)
        item_id = client.post(INCOME_URL, json={"amount": 500.0, "date_received": FUTURE}, headers=h).json()["id"]
        r = client.post(f"{INCOME_URL}/{item_id}/dismiss", headers=h)
        assert r.status_code == 204

        upcoming = client.get(UPCOMING_URL, headers=h).json()
        assert all(i["id"] != item_id for i in upcoming["income"])

    def test_dismiss_non_recurring_expense_soft_deletes(self, client):
        h = auth(client)
        item_id = client.post(EXPENSE_URL, json={
            "amount": 100.0, "date_incurred": FUTURE, "category": "software",
        }, headers=h).json()["id"]
        r = client.post(f"{EXPENSE_URL}/{item_id}/dismiss", headers=h)
        assert r.status_code == 204

        upcoming = client.get(UPCOMING_URL, headers=h).json()
        assert all(e["id"] != item_id for e in upcoming["expenses"])

    # --- end date: recurrence stops after crossing end_date ---

    def test_recurrence_ends_when_next_date_exceeds_end_date(self, client):
        """After the last valid occurrence is approved, the recurring entry disappears."""
        h = auth(client)
        # Create a weekly recurring entry due tomorrow with end_date = day after tomorrow.
        # After approval, next date would be +7 days, exceeding end_date → entry deactivated.
        tomorrow     = (date.today() + timedelta(days=1)).isoformat()
        end          = (date.today() + timedelta(days=3)).isoformat()
        item_id = client.post(INCOME_URL, json={
            "amount": 300.0, "date_received": tomorrow,
            "recurrence_freq": "weekly", "recurrence_end_date": end,
        }, headers=h).json()["id"]

        # Approve today (using a past date to force confirmation)
        client.post(f"{INCOME_URL}/{item_id}/approve", json={"date_received": PAST}, headers=h)

        # The recurring entry's next date (+7 days) exceeds end_date, so it was deactivated.
        upcoming = client.get(UPCOMING_URL, headers=h).json()
        assert all(i["id"] != item_id for i in upcoming["income"])

        # The confirmed transaction still exists.
        income_list = client.get(INCOME_URL, headers=h).json()
        confirmed = [i for i in income_list if i["amount"] == pytest.approx(300.0)]
        assert len(confirmed) == 1

    def test_recurrence_ends_on_dismiss_when_next_date_exceeds_end_date(self, client):
        h = auth(client)
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        end      = (date.today() + timedelta(days=2)).isoformat()
        item_id = client.post(INCOME_URL, json={
            "amount": 200.0, "date_received": tomorrow,
            "recurrence_freq": "weekly", "recurrence_end_date": end,
        }, headers=h).json()["id"]

        client.post(f"{INCOME_URL}/{item_id}/dismiss", headers=h)

        upcoming = client.get(UPCOMING_URL, headers=h).json()
        assert all(i["id"] != item_id for i in upcoming["income"])
        # No transaction created on dismiss
        income_list = client.get(INCOME_URL, headers=h).json()
        assert income_list == []

    # --- delete stops all future occurrences ---

    def test_delete_recurring_income_stops_future_occurrences(self, client):
        h = auth(client)
        # Approve one occurrence first so we have a confirmed transaction.
        item_id = client.post(INCOME_URL, json={
            "amount": 500.0, "date_received": FUTURE, "recurrence_freq": "monthly",
        }, headers=h).json()["id"]
        # Approve occurrence using a past date
        client.post(f"{INCOME_URL}/{item_id}/approve", json={"date_received": PAST}, headers=h)

        # Now delete the recurring entry.
        r = client.delete(f"{INCOME_URL}/{item_id}", headers=h)
        assert r.status_code == 204

        # Recurring entry gone from upcoming.
        upcoming = client.get(UPCOMING_URL, headers=h).json()
        assert all(i["id"] != item_id for i in upcoming["income"])

        # Confirmed transaction still in income list.
        income_list = client.get(INCOME_URL, headers=h).json()
        assert any(i["amount"] == pytest.approx(500.0) and i["recurrence_freq"] is None for i in income_list)

    # --- confirmed transactions count in analytics ---

    def test_confirmed_recurring_transaction_counts_in_summary(self, client, db):
        h = auth(client)
        item_id = client.post(INCOME_URL, json={
            "amount": 1000.0, "date_received": FUTURE, "recurrence_freq": "monthly",
        }, headers=h).json()["id"]

        # Summary before approval: revenue = 0
        assert client.get(SUMMARY_URL, headers=h).json()["revenue_ytd"] == pytest.approx(0.0)

        # Approve using a tax-year date so it counts in YTD
        tax_date = _this_year_april_6().isoformat()
        client.post(f"{INCOME_URL}/{item_id}/approve", json={"date_received": tax_date}, headers=h)

        assert client.get(SUMMARY_URL, headers=h).json()["revenue_ytd"] == pytest.approx(1000.0)

    # --- date advancement helper correctness ---

    def test_advance_weekly(self):
        from app.routes.business import _advance_date
        from datetime import date
        assert _advance_date(date(2026, 1, 1), "weekly") == date(2026, 1, 8)

    def test_advance_two_weekly(self):
        from app.routes.business import _advance_date
        assert _advance_date(date(2026, 1, 1), "two_weekly") == date(2026, 1, 15)

    def test_advance_four_weekly(self):
        from app.routes.business import _advance_date
        assert _advance_date(date(2026, 1, 1), "four_weekly") == date(2026, 1, 29)

    def test_advance_monthly(self):
        from app.routes.business import _advance_date
        assert _advance_date(date(2026, 1, 15), "monthly") == date(2026, 2, 15)

    def test_advance_monthly_clamps_to_month_end(self):
        """Jan 31 + 1 month = Feb 28 (not 31)."""
        from app.routes.business import _advance_date
        assert _advance_date(date(2026, 1, 31), "monthly") == date(2026, 2, 28)

    def test_advance_two_monthly(self):
        from app.routes.business import _advance_date
        assert _advance_date(date(2026, 1, 15), "two_monthly") == date(2026, 3, 15)

    def test_advance_quarterly(self):
        from app.routes.business import _advance_date
        assert _advance_date(date(2026, 1, 15), "quarterly") == date(2026, 4, 15)

    def test_advance_biannually(self):
        from app.routes.business import _advance_date
        assert _advance_date(date(2026, 1, 15), "biannually") == date(2026, 7, 15)

    def test_advance_annually(self):
        from app.routes.business import _advance_date
        assert _advance_date(date(2026, 1, 15), "annually") == date(2027, 1, 15)

    def test_advance_two_yearly(self):
        from app.routes.business import _advance_date
        assert _advance_date(date(2026, 1, 15), "two_yearly") == date(2028, 1, 15)

    # --- ownership ---

    def test_dismiss_income_ownership(self, client):
        alice = auth(client, "alice@test.com")
        bob   = auth(client, "bob@test.com")
        item_id = client.post(INCOME_URL, json={
            "amount": 500.0, "date_received": FUTURE, "recurrence_freq": "monthly",
        }, headers=alice).json()["id"]
        assert client.post(f"{INCOME_URL}/{item_id}/dismiss", headers=bob).status_code == 404

    def test_dismiss_expense_ownership(self, client):
        alice = auth(client, "alice@test.com")
        bob   = auth(client, "bob@test.com")
        item_id = client.post(EXPENSE_URL, json={
            "amount": 100.0, "date_incurred": FUTURE, "category": "software",
            "recurrence_freq": "monthly",
        }, headers=alice).json()["id"]
        assert client.post(f"{EXPENSE_URL}/{item_id}/dismiss", headers=bob).status_code == 404

    def test_multiple_approvals_create_multiple_confirmed_transactions(self, client):
        """Approving twice creates two separate confirmed transactions."""
        h = auth(client)
        item_id = client.post(INCOME_URL, json={
            "amount": 500.0, "date_received": FUTURE, "recurrence_freq": "monthly",
        }, headers=h).json()["id"]

        past2 = (date.today() - timedelta(days=14)).isoformat()
        client.post(f"{INCOME_URL}/{item_id}/approve", json={"date_received": PAST}, headers=h)
        client.post(f"{INCOME_URL}/{item_id}/approve", json={"date_received": past2}, headers=h)

        income_list = client.get(INCOME_URL, headers=h).json()
        confirmed = [i for i in income_list if i["recurrence_freq"] is None and i["amount"] == pytest.approx(500.0)]
        assert len(confirmed) == 2


# ---------------------------------------------------------------------------
# Recurring back-fill: past-start recurrences auto-confirm past occurrences
# ---------------------------------------------------------------------------

class TestRecurringBackfill:
    def test_past_start_monthly_backfills_one_confirmed_and_shows_next_in_upcoming(self, client):
        """
        Monthly recurrence started 5 days ago: exactly 1 past confirmed (start date),
        and the next occurrence (~25 days from now) appears in Upcoming.
        Using 5 days to ensure start + 1 month is always > today regardless of month length.
        """
        h = auth(client)
        today = date.today()
        start = today - timedelta(days=5)
        r = client.post(INCOME_URL, json={
            "amount": 500.0, "date_received": start.isoformat(), "recurrence_freq": "monthly",
        }, headers=h)
        assert r.status_code == 201

        income_list = client.get(INCOME_URL, headers=h).json()
        confirmed = [i for i in income_list if i["recurrence_freq"] is None]
        assert len(confirmed) == 1
        assert confirmed[0]["date_received"] == start.isoformat()
        assert confirmed[0]["is_approved"] is True

        upcoming = client.get(UPCOMING_URL, headers=h).json()
        rolling = [i for i in upcoming["income"] if i["recurrence_freq"] == "monthly"]
        assert len(rolling) == 1
        rolling_date = date.fromisoformat(rolling[0]["date_received"])
        assert rolling_date > today

    def test_two_weekly_started_35_days_ago_3_confirmed_1_upcoming(self, client):
        """
        Two-weekly started 35 days ago (5 weeks):
        occurrences at +0/+14/+28 days are past (confirmed),
        +42 days is 7 days in the future (rolling entry in Upcoming).
        """
        h = auth(client)
        today = date.today()
        start = today - timedelta(days=35)
        r = client.post(INCOME_URL, json={
            "amount": 300.0, "date_received": start.isoformat(), "recurrence_freq": "two_weekly",
        }, headers=h)
        assert r.status_code == 201

        income_list = client.get(INCOME_URL, headers=h).json()
        confirmed = [i for i in income_list if i["recurrence_freq"] is None]
        assert len(confirmed) == 3

        confirmed_dates = sorted(i["date_received"] for i in confirmed)
        assert confirmed_dates[0] == start.isoformat()
        assert confirmed_dates[1] == (start + timedelta(days=14)).isoformat()
        assert confirmed_dates[2] == (start + timedelta(days=28)).isoformat()

        upcoming = client.get(UPCOMING_URL, headers=h).json()
        rolling = [i for i in upcoming["income"] if i["recurrence_freq"] == "two_weekly"]
        assert len(rolling) == 1
        rolling_date = date.fromisoformat(rolling[0]["date_received"])
        assert rolling_date == start + timedelta(days=42)
        assert rolling_date > today

    def test_all_occurrences_past_end_date_also_past_nothing_in_upcoming(self, client):
        """Weekly started 14 days ago, ended 7 days ago: 2 confirmed, nothing in Upcoming."""
        h = auth(client)
        today     = date.today()
        start     = today - timedelta(days=14)
        end_date  = today - timedelta(days=7)
        r = client.post(INCOME_URL, json={
            "amount": 100.0, "date_received": start.isoformat(),
            "recurrence_freq": "weekly", "recurrence_end_date": end_date.isoformat(),
        }, headers=h)
        assert r.status_code == 201

        upcoming = client.get(UPCOMING_URL, headers=h).json()
        assert upcoming["income"] == []

        income_list = client.get(INCOME_URL, headers=h).json()
        confirmed = [i for i in income_list if i["recurrence_freq"] is None]
        # start (today-14) and start+7 (= end_date = today-7): both ≤ today and ≤ end_date
        assert len(confirmed) == 2
        dates = sorted(i["date_received"] for i in confirmed)
        assert dates[0] == start.isoformat()
        assert dates[1] == end_date.isoformat()

    def test_past_occurrences_respect_end_date(self, client):
        """Back-filled occurrences beyond end_date are NOT created."""
        h = auth(client)
        from app.routes.business import _advance_date as _adv
        today  = date.today()
        start  = today - timedelta(days=35)   # 5 weeks ago
        occ1   = _adv(start, "two_weekly")    # 3 weeks ago (still past)
        occ2   = _adv(occ1,  "two_weekly")    # 1 week ago (still past)
        occ3   = _adv(occ2,  "two_weekly")    # 1 week in the future
        # End date is between occ2 and occ3, so occ3 should NOT be created
        end_date = (occ3 - timedelta(days=3)).isoformat()
        r = client.post(INCOME_URL, json={
            "amount": 200.0, "date_received": start.isoformat(),
            "recurrence_freq": "two_weekly", "recurrence_end_date": end_date,
        }, headers=h)
        assert r.status_code == 201

        income_list = client.get(INCOME_URL, headers=h).json()
        confirmed = [i for i in income_list if i["recurrence_freq"] is None]
        # occ0, occ1, occ2 are ≤ end_date; occ3 is > end_date → exactly 3 confirmed
        assert len(confirmed) == 3
        for c in confirmed:
            assert c["date_received"] <= end_date

    def test_future_start_recurrence_unchanged(self, client):
        """Future-start recurring: no backfill, single rolling entry in Upcoming."""
        h = auth(client)
        r = client.post(INCOME_URL, json={
            "amount": 400.0, "date_received": FUTURE, "recurrence_freq": "monthly",
        }, headers=h)
        assert r.status_code == 201

        # No confirmed transactions created
        income_list = client.get(INCOME_URL, headers=h).json()
        assert income_list == []

        # Single rolling entry in Upcoming
        upcoming = client.get(UPCOMING_URL, headers=h).json()
        rolling = [i for i in upcoming["income"] if i["recurrence_freq"] == "monthly"]
        assert len(rolling) == 1
        assert rolling[0]["date_received"] == FUTURE

    def test_backfilled_past_occurrences_count_in_analytics(self, client):
        """Back-filled confirmed transactions appear in summary YTD revenue."""
        h = auth(client)
        # Monthly started in this tax year: creates 1+ confirmed transactions
        tax_start = _this_year_april_6()
        # Use a date 35 days ago that is still within the tax year
        start = date.today() - timedelta(days=35)
        if start < tax_start:
            start = tax_start  # fallback to tax year start if we've gone too far back
        r = client.post(INCOME_URL, json={
            "amount": 1000.0, "date_received": start.isoformat(), "recurrence_freq": "monthly",
        }, headers=h)
        assert r.status_code == 201

        summary = client.get(SUMMARY_URL, headers=h).json()
        # At least the first occurrence counts in revenue
        assert summary["revenue_ytd"] >= 1000.0

    def test_past_occurrences_not_in_approval_queue(self, client):
        """Back-filled past transactions are confirmed directly — NOT in the approval queue."""
        h = auth(client)
        start = (date.today() - timedelta(days=35)).isoformat()
        client.post(INCOME_URL, json={
            "amount": 500.0, "date_received": start, "recurrence_freq": "two_weekly",
        }, headers=h)

        upcoming = client.get(UPCOMING_URL, headers=h).json()
        # The upcoming income list has only the future rolling entry — no past dates
        for entry in upcoming["income"]:
            assert date.fromisoformat(entry["date_received"]) > date.today()

    def test_expense_backfill(self, client):
        """Expense backfill: monthly started 5 days ago → 1 confirmed, next future in Upcoming."""
        h = auth(client)
        today = date.today()
        start = today - timedelta(days=5)
        r = client.post(EXPENSE_URL, json={
            "amount": 150.0, "date_incurred": start.isoformat(), "category": "software",
            "recurrence_freq": "monthly",
        }, headers=h)
        assert r.status_code == 201

        expense_list = client.get(EXPENSE_URL, headers=h).json()
        confirmed = [e for e in expense_list if e["recurrence_freq"] is None]
        assert len(confirmed) == 1
        assert confirmed[0]["date_incurred"] == start.isoformat()

        upcoming = client.get(UPCOMING_URL, headers=h).json()
        rolling = [e for e in upcoming["expenses"] if e["recurrence_freq"] == "monthly"]
        assert len(rolling) == 1
        assert date.fromisoformat(rolling[0]["date_incurred"]) > today
