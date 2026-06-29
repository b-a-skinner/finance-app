"""
CRUD endpoint tests for all five financial resources.

Pattern per resource:
  - test_create       — POST returns 201 with correct data
  - test_list         — GET returns the created item
  - test_update       — PUT returns 200 with changed fields
  - test_delete       — DELETE returns 204; item gone from list
  - test_isolation    — another user gets 404 on PUT/DELETE and empty GET

The _CRUDBase mixin provides helpers; each concrete class only declares
URL, CREATE payload, UPDATE payload, and one field to assert after update.
"""
import pytest


REGISTER = "/api/auth/register"
LOGIN = "/api/auth/login"


def auth(client, email="alice@test.com", password="testpass123!"):
    """Register (idempotent) and return Bearer auth headers."""
    client.post(REGISTER, json={"email": email, "password": password})
    r = client.post(LOGIN, data={"username": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


class _CRUDBase:
    URL: str
    CREATE: dict
    UPDATE: dict
    UPDATE_FIELD: str   # which field to assert changed after update
    UPDATE_VALUE: object

    def _create(self, client, headers) -> dict:
        r = client.post(self.URL, json=self.CREATE, headers=headers)
        assert r.status_code == 201
        return r.json()

    # -----------------------------------------------------------------------

    def test_create(self, client):
        h = auth(client)
        r = client.post(self.URL, json=self.CREATE, headers=h)
        assert r.status_code == 201
        body = r.json()
        assert "id" in body
        assert body["is_active"] is True

    def test_list(self, client):
        h = auth(client)
        item = self._create(client, h)
        ids = [i["id"] for i in client.get(self.URL, headers=h).json()]
        assert item["id"] in ids

    def test_update(self, client):
        h = auth(client)
        item = self._create(client, h)
        r = client.put(f"{self.URL}/{item['id']}", json=self.UPDATE, headers=h)
        assert r.status_code == 200
        assert r.json()[self.UPDATE_FIELD] == self.UPDATE_VALUE

    def test_delete(self, client):
        h = auth(client)
        item = self._create(client, h)
        r = client.delete(f"{self.URL}/{item['id']}", headers=h)
        assert r.status_code == 204
        ids = [i["id"] for i in client.get(self.URL, headers=h).json()]
        assert item["id"] not in ids

    def test_isolation(self, client):
        """User B cannot update, delete, or see User A's records."""
        alice = auth(client, "alice@test.com")
        bob = auth(client, "bob@test.com")

        item = self._create(client, alice)
        item_id = item["id"]

        # Bob cannot update Alice's item
        r = client.put(f"{self.URL}/{item_id}", json=self.UPDATE, headers=bob)
        assert r.status_code == 404, "Bob should get 404 on PUT to Alice's item"

        # Bob cannot delete Alice's item
        r = client.delete(f"{self.URL}/{item_id}", headers=bob)
        assert r.status_code == 404, "Bob should get 404 on DELETE of Alice's item"

        # Bob's own list is empty — Alice's items are invisible to him
        r = client.get(self.URL, headers=bob)
        assert r.json() == [], "Bob's list should not contain Alice's items"

        # Alice's item is still there (Bob's 404s didn't soft-delete it)
        ids = [i["id"] for i in client.get(self.URL, headers=alice).json()]
        assert item_id in ids, "Alice's item should still exist after Bob's failed attempts"


# ---------------------------------------------------------------------------
# Concrete test classes — one per resource
# ---------------------------------------------------------------------------

class TestIncomeCRUD(_CRUDBase):
    URL = "/api/income"
    CREATE = {"label": "Day Job", "gross_annual_salary": 45_000.0, "pay_frequency": "monthly"}
    UPDATE = {"label": "Senior Role", "gross_annual_salary": 55_000.0}
    UPDATE_FIELD = "label"
    UPDATE_VALUE = "Senior Role"


class TestExpenseCRUD(_CRUDBase):
    URL = "/api/expenses"
    CREATE = {"category": "Rent", "amount": 1_200.0, "frequency": "monthly", "is_fixed": True}
    UPDATE = {"amount": 1_400.0}
    UPDATE_FIELD = "amount"
    UPDATE_VALUE = 1_400.0


class TestDebtCRUD(_CRUDBase):
    URL = "/api/debts"
    CREATE = {"debt_type": "credit_card", "balance": 3_000.0, "interest_rate": 19.9, "min_payment": 75.0}
    UPDATE = {"balance": 2_500.0}
    UPDATE_FIELD = "balance"
    UPDATE_VALUE = 2_500.0


class TestSavingsCRUD(_CRUDBase):
    URL = "/api/savings"
    CREATE = {"name": "Emergency Fund", "current_balance": 2_000.0, "target_amount": 10_000.0, "monthly_contribution": 200.0}
    UPDATE = {"monthly_contribution": 300.0}
    UPDATE_FIELD = "monthly_contribution"
    UPDATE_VALUE = 300.0


class TestPensionCRUD(_CRUDBase):
    URL = "/api/pension"
    CREATE = {"current_balance": 15_000.0, "employee_contribution_pct": 5.0, "employer_contribution_pct": 3.0}
    UPDATE = {"current_balance": 16_000.0}
    UPDATE_FIELD = "current_balance"
    UPDATE_VALUE = 16_000.0


class TestAssetCRUD(_CRUDBase):
    URL = "/api/assets"
    CREATE = {"name": "Family Home", "asset_type": "property", "current_value": 300_000.0}
    UPDATE = {"current_value": 320_000.0}
    UPDATE_FIELD = "current_value"
    UPDATE_VALUE = 320_000.0
