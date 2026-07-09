"""Tests for business income/expense CRUD, ownership isolation, YTD summary, and HMRC simplified expenses."""
from datetime import date, timedelta

import pytest

from app.models.config import BusinessTaxConfig

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


def seed_biz_config(db):
    """Seed a BusinessTaxConfig for the current tax year into the test DB."""
    today = date.today()
    year  = today.year if today >= date(today.year, 4, 6) else today.year - 1
    label = f"{year}/{str(year + 1)[2:]}"
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
