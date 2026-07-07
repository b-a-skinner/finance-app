"""Tests for business income/expense CRUD, ownership isolation, and YTD summary."""
from datetime import date, timedelta

import pytest

REGISTER = "/api/auth/register"
LOGIN = "/api/auth/login"

INCOME_URL = "/api/business/income"
EXPENSE_URL = "/api/business/expenses"
SUMMARY_URL = "/api/business/summary"

TODAY = date.today().isoformat()


def auth(client, email="alice@test.com", password="testpass123!"):
    client.post(REGISTER, json={"email": email, "password": password})
    r = client.post(LOGIN, data={"username": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


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
        bob = auth(client, "bob@test.com")
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
# Expense CRUD
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
        bob = auth(client, "bob@test.com")
        item_id = client.post(EXPENSE_URL, json=self.CREATE, headers=alice).json()["id"]
        assert client.patch(f"{EXPENSE_URL}/{item_id}", json=self.UPDATE, headers=bob).status_code == 404
        assert client.delete(f"{EXPENSE_URL}/{item_id}", headers=bob).status_code == 404


# ---------------------------------------------------------------------------
# Summary — YTD and tax year boundary
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
        assert body["expenses_ytd"] == 0.0
        assert body["estimated_profit"] == 0.0
        assert body["has_business_data"] is False

    def test_has_data_flag(self, client):
        h = auth(client)
        client.post(INCOME_URL, json={"amount": 100.0, "date_received": TODAY}, headers=h)
        body = client.get(SUMMARY_URL, headers=h).json()
        assert body["has_business_data"] is True

    def test_ytd_sums_current_year_only(self, client):
        h = auth(client)
        tax_start = _this_year_april_6()

        # In current tax year
        within = tax_start.isoformat()
        # Before current tax year (previous tax year)
        before = (tax_start - timedelta(days=1)).isoformat()

        client.post(INCOME_URL, json={"amount": 1000.0, "date_received": within}, headers=h)
        client.post(INCOME_URL, json={"amount": 500.0, "date_received": before}, headers=h)
        client.post(EXPENSE_URL, json={"amount": 200.0, "date_incurred": within, "category": "software"}, headers=h)
        client.post(EXPENSE_URL, json={"amount": 100.0, "date_incurred": before, "category": "travel"}, headers=h)

        body = client.get(SUMMARY_URL, headers=h).json()
        assert body["revenue_ytd"] == pytest.approx(1000.0)
        assert body["expenses_ytd"] == pytest.approx(200.0)
        assert body["estimated_profit"] == pytest.approx(800.0)
        assert body["has_business_data"] is True

    def test_april_5_falls_in_previous_tax_year(self, client):
        """5 April is the last day of the PREVIOUS tax year — must not appear in YTD."""
        h = auth(client)
        tax_start = _this_year_april_6()
        april_5_this_year = date(tax_start.year, 4, 5)

        client.post(INCOME_URL, json={"amount": 999.0, "date_received": april_5_this_year.isoformat()}, headers=h)

        body = client.get(SUMMARY_URL, headers=h).json()
        # april_5 is before the tax year start, so it should not be counted
        assert body["revenue_ytd"] == pytest.approx(0.0)

    def test_april_6_falls_in_current_tax_year(self, client):
        """6 April is the FIRST day of the current tax year — must appear in YTD."""
        h = auth(client)
        tax_start = _this_year_april_6()

        client.post(INCOME_URL, json={"amount": 999.0, "date_received": tax_start.isoformat()}, headers=h)

        body = client.get(SUMMARY_URL, headers=h).json()
        assert body["revenue_ytd"] == pytest.approx(999.0)

    def test_summary_isolation(self, client):
        alice = auth(client, "alice@test.com")
        bob = auth(client, "bob@test.com")
        client.post(INCOME_URL, json={"amount": 5000.0, "date_received": TODAY}, headers=alice)
        body = client.get(SUMMARY_URL, headers=bob).json()
        assert body["revenue_ytd"] == 0.0
