"""Tests for the savings projection endpoint and optional target_amount."""
import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _register_and_login(client: TestClient, email: str = "user@example.com") -> dict:
    client.post("/api/auth/register", json={"email": email, "password": "pass123"})
    r = client.post(
        "/api/auth/login",
        data={"username": email, "password": "pass123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _create_goal(client, headers, **overrides) -> dict:
    defaults = {
        "name": "House deposit",
        "current_balance": 2000.0,
        "target_amount": 10000.0,
        "monthly_contribution": 500.0,
    }
    r = client.post("/api/savings", json={**defaults, **overrides}, headers=headers)
    assert r.status_code == 201
    return r.json()


# ---------------------------------------------------------------------------
# Optional target_amount on create
# ---------------------------------------------------------------------------

class TestOptionalTarget:
    def test_create_without_target_returns_null(self, client):
        h = _register_and_login(client)
        r = client.post(
            "/api/savings",
            json={"name": "Rainy day", "current_balance": 500.0, "monthly_contribution": 100.0},
            headers=h,
        )
        assert r.status_code == 201
        assert r.json()["target_amount"] is None

    def test_create_with_explicit_null_target(self, client):
        h = _register_and_login(client)
        r = client.post(
            "/api/savings",
            json={"name": "Rainy day", "current_balance": 500.0, "target_amount": None, "monthly_contribution": 100.0},
            headers=h,
        )
        assert r.status_code == 201
        assert r.json()["target_amount"] is None

    def test_create_with_target_returns_value(self, client):
        h = _register_and_login(client)
        r = client.post(
            "/api/savings",
            json={"name": "Goal", "current_balance": 0.0, "target_amount": 5000.0, "monthly_contribution": 200.0},
            headers=h,
        )
        assert r.status_code == 201
        assert r.json()["target_amount"] == 5000.0

    def test_update_clears_target_to_null(self, client):
        h = _register_and_login(client)
        goal = _create_goal(client, h)
        r = client.put(
            f"/api/savings/{goal['id']}",
            json={"name": goal["name"], "current_balance": goal["current_balance"],
                  "target_amount": None, "monthly_contribution": goal["monthly_contribution"]},
            headers=h,
        )
        assert r.status_code == 200
        assert r.json()["target_amount"] is None

    def test_list_includes_null_target(self, client):
        h = _register_and_login(client)
        _create_goal(client, h, target_amount=None)
        r = client.get("/api/savings", headers=h)
        assert r.status_code == 200
        assert r.json()[0]["target_amount"] is None


# ---------------------------------------------------------------------------
# Projection endpoint — happy path
# ---------------------------------------------------------------------------

class TestProjectionHappyPath:
    def test_returns_months_and_date(self, client):
        h = _register_and_login(client)
        goal = _create_goal(client, h, current_balance=0.0, target_amount=1000.0, monthly_contribution=500.0)
        r = client.get(f"/api/savings/{goal['id']}/projection", headers=h)
        assert r.status_code == 200
        data = r.json()
        assert data["months_to_goal"] == 2
        assert "projected_date" in data
        # projected_date is "Month YYYY" format
        parts = data["projected_date"].split()
        assert len(parts) == 2
        assert parts[1].isdigit()

    def test_months_rounded_up(self, client):
        # 1500 remaining / 400 per month = 3.75 → 4 months
        h = _register_and_login(client)
        goal = _create_goal(client, h, current_balance=500.0, target_amount=2000.0, monthly_contribution=400.0)
        r = client.get(f"/api/savings/{goal['id']}/projection", headers=h)
        assert r.status_code == 200
        assert r.json()["months_to_goal"] == 4

    def test_exact_months(self, client):
        # 1000 remaining / 500 = exactly 2 months
        h = _register_and_login(client)
        goal = _create_goal(client, h, current_balance=0.0, target_amount=1000.0, monthly_contribution=500.0)
        r = client.get(f"/api/savings/{goal['id']}/projection", headers=h)
        assert r.status_code == 200
        assert r.json()["months_to_goal"] == 2

    def test_one_month_to_go(self, client):
        h = _register_and_login(client)
        goal = _create_goal(client, h, current_balance=9900.0, target_amount=10000.0, monthly_contribution=200.0)
        r = client.get(f"/api/savings/{goal['id']}/projection", headers=h)
        assert r.status_code == 200
        assert r.json()["months_to_goal"] == 1


# ---------------------------------------------------------------------------
# Projection endpoint — error cases (400)
# ---------------------------------------------------------------------------

class TestProjectionErrors:
    def test_no_target_returns_400(self, client):
        h = _register_and_login(client)
        goal = _create_goal(client, h, target_amount=None)
        r = client.get(f"/api/savings/{goal['id']}/projection", headers=h)
        assert r.status_code == 400

    def test_zero_contribution_returns_400(self, client):
        h = _register_and_login(client)
        goal = _create_goal(client, h, monthly_contribution=0.0)
        r = client.get(f"/api/savings/{goal['id']}/projection", headers=h)
        assert r.status_code == 400

    def test_goal_already_reached_returns_400(self, client):
        h = _register_and_login(client)
        goal = _create_goal(client, h, current_balance=10000.0, target_amount=10000.0)
        r = client.get(f"/api/savings/{goal['id']}/projection", headers=h)
        assert r.status_code == 400

    def test_balance_exceeds_target_returns_400(self, client):
        h = _register_and_login(client)
        goal = _create_goal(client, h, current_balance=12000.0, target_amount=10000.0)
        r = client.get(f"/api/savings/{goal['id']}/projection", headers=h)
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Auth and isolation
# ---------------------------------------------------------------------------

class TestProjectionAuth:
    def test_unauthenticated_returns_401(self, client):
        r = client.get("/api/savings/1/projection")
        assert r.status_code == 401

    def test_other_users_goal_returns_404(self, client):
        h_a = _register_and_login(client, "a@example.com")
        h_b = _register_and_login(client, "b@example.com")
        goal = _create_goal(client, h_a)
        r = client.get(f"/api/savings/{goal['id']}/projection", headers=h_b)
        assert r.status_code == 404
