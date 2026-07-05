"""
Admin endpoint tests.
All tests use the in-memory SQLite DB wired up in conftest.py.
ADMIN_KEY is set to "test-admin-key" by conftest before app import.
"""
from datetime import datetime, timezone

from app.models import Asset, Debt, Expense, FinancialSnapshot, IncomeSource, PensionPot, SavingsGoal
from app.models.user import User
from app.security import hash_password

ADMIN_USERS = "/api/admin/users"
ADMIN_STATS = "/api/admin/stats"
REGISTER = "/api/auth/register"

GOOD_KEY = {"X-Admin-Key": "test-admin-key"}
BAD_KEY  = {"X-Admin-Key": "wrong-key"}


def _register(client, email="alice@example.com", password="password123"):
    return client.post(REGISTER, json={"email": email, "password": password})


def _make_user(db, email="bob@example.com"):
    u = User(email=email, password_hash=hash_password("pw"))
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


# ---------------------------------------------------------------------------
# Auth protection
# ---------------------------------------------------------------------------

class TestAdminKeyRequired:
    def test_users_no_key(self, client):
        assert client.get(ADMIN_USERS).status_code == 403

    def test_users_wrong_key(self, client):
        assert client.get(ADMIN_USERS, headers=BAD_KEY).status_code == 403

    def test_stats_no_key(self, client):
        assert client.get(ADMIN_STATS).status_code == 403

    def test_stats_wrong_key(self, client):
        assert client.get(ADMIN_STATS, headers=BAD_KEY).status_code == 403

    def test_delete_no_key(self, client):
        assert client.delete("/api/admin/users/1").status_code == 403

    def test_delete_wrong_key(self, client):
        assert client.delete("/api/admin/users/1", headers=BAD_KEY).status_code == 403

    def test_bearer_jwt_cannot_access_admin(self, client):
        _register(client)
        login_r = client.post("/api/auth/login", data={"username": "alice@example.com", "password": "password123"})
        token = login_r.json()["access_token"]
        r = client.get(ADMIN_USERS, headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# GET /api/admin/users
# ---------------------------------------------------------------------------

class TestAdminUsers:
    def test_empty_list(self, client):
        r = client.get(ADMIN_USERS, headers=GOOD_KEY)
        assert r.status_code == 200
        assert r.json() == []

    def test_lists_user(self, client):
        _register(client)
        r = client.get(ADMIN_USERS, headers=GOOD_KEY)
        assert r.status_code == 200
        users = r.json()
        assert len(users) == 1
        u = users[0]
        assert u["email"] == "alice@example.com"
        assert u["onboarding_completed"] is False
        assert u["financial_goals"] is None

    def test_profile_complete_all_false_for_new_user(self, client):
        _register(client)
        u = client.get(ADMIN_USERS, headers=GOOD_KEY).json()[0]
        pc = u["profile_complete"]
        for cat in ("income", "expenses", "debts", "savings", "pension", "assets"):
            assert pc[cat] is False

    def test_profile_complete_income_true(self, client, db):
        user = _make_user(db)
        db.add(IncomeSource(
            user_id=user.id, label="Salary", gross_annual_salary=40000,
            pay_frequency="annual", is_active=True,
        ))
        db.commit()
        r = client.get(ADMIN_USERS, headers=GOOD_KEY).json()
        assert r[0]["profile_complete"]["income"] is True

    def test_last_active_falls_back_to_created_at(self, client):
        _register(client)
        u = client.get(ADMIN_USERS, headers=GOOD_KEY).json()[0]
        assert u["last_active"] == u["created_at"]

    def test_last_active_uses_latest_snapshot(self, client, db):
        user = _make_user(db)
        snap_time = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        db.add(FinancialSnapshot(
            user_id=user.id, captured_at=snap_time,
            net_worth=10000, monthly_disposable_income=500,
            total_savings_balance=2000, total_debt_balance=0,
            pension_pot_balance=0,
        ))
        db.commit()
        r = client.get(ADMIN_USERS, headers=GOOD_KEY).json()
        assert "2025-06-01" in r[0]["last_active"]

    def test_financial_goals_parsed(self, client, db):
        import json
        user = _make_user(db)
        user.financial_goals = json.dumps(["building_my_savings", "buying_a_home"])
        db.commit()
        r = client.get(ADMIN_USERS, headers=GOOD_KEY).json()
        assert r[0]["financial_goals"] == ["building_my_savings", "buying_a_home"]

    def test_multiple_users(self, client):
        _register(client, "a@example.com")
        _register(client, "b@example.com")
        r = client.get(ADMIN_USERS, headers=GOOD_KEY).json()
        assert len(r) == 2

    def test_required_fields_present(self, client):
        _register(client)
        u = client.get(ADMIN_USERS, headers=GOOD_KEY).json()[0]
        for field in ("id", "email", "first_name", "created_at", "last_active",
                      "profile_complete", "onboarding_completed", "financial_goals"):
            assert field in u


# ---------------------------------------------------------------------------
# GET /api/admin/stats
# ---------------------------------------------------------------------------

class TestAdminStats:
    def test_empty_stats(self, client):
        r = client.get(ADMIN_STATS, headers=GOOD_KEY)
        assert r.status_code == 200
        s = r.json()
        assert s["total_users"] == 0
        assert s["users_active_last_7_days"] == 0
        assert s["users_active_last_30_days"] == 0
        assert s["users_completed_onboarding"] == 0
        assert s["avg_income_sources_per_user"] == 0.0

    def test_total_users(self, client):
        _register(client, "a@example.com")
        _register(client, "b@example.com")
        assert client.get(ADMIN_STATS, headers=GOOD_KEY).json()["total_users"] == 2

    def test_completed_onboarding_count(self, client, db):
        u1 = _make_user(db, "c1@example.com")
        u2 = _make_user(db, "c2@example.com")
        u1.onboarding_completed = True
        db.commit()
        s = client.get(ADMIN_STATS, headers=GOOD_KEY).json()
        assert s["users_completed_onboarding"] == 1

    def test_users_with_income(self, client, db):
        user = _make_user(db)
        db.add(IncomeSource(
            user_id=user.id, label="Salary", gross_annual_salary=35000,
            pay_frequency="annual", is_active=True,
        ))
        db.commit()
        s = client.get(ADMIN_STATS, headers=GOOD_KEY).json()
        assert s["users_with_income"] == 1
        assert s["feature_adoption"]["income"] == 100.0

    def test_feature_adoption_keys_present(self, client):
        fa = client.get(ADMIN_STATS, headers=GOOD_KEY).json()["feature_adoption"]
        for key in ("income", "expenses", "debts", "savings", "pension", "assets"):
            assert key in fa

    def test_avg_income_sources(self, client, db):
        u1 = _make_user(db, "u1@example.com")
        u2 = _make_user(db, "u2@example.com")
        db.add(IncomeSource(user_id=u1.id, label="S1", gross_annual_salary=30000, pay_frequency="annual", is_active=True))
        db.add(IncomeSource(user_id=u1.id, label="S2", gross_annual_salary=5000, pay_frequency="annual", is_active=True))
        db.commit()
        s = client.get(ADMIN_STATS, headers=GOOD_KEY).json()
        assert s["avg_income_sources_per_user"] == 1.0  # 2 rows / 2 users

    def test_inactive_records_excluded(self, client, db):
        user = _make_user(db)
        db.add(IncomeSource(
            user_id=user.id, label="Old", gross_annual_salary=20000,
            pay_frequency="annual", is_active=False,
        ))
        db.commit()
        s = client.get(ADMIN_STATS, headers=GOOD_KEY).json()
        assert s["users_with_income"] == 0


# ---------------------------------------------------------------------------
# DELETE /api/admin/users/{user_id}
# ---------------------------------------------------------------------------

class TestAdminDeleteUser:
    def test_delete_nonexistent_returns_404(self, client):
        r = client.delete("/api/admin/users/9999", headers=GOOD_KEY)
        assert r.status_code == 404

    def test_delete_success(self, client):
        _register(client)
        user_id = client.get(ADMIN_USERS, headers=GOOD_KEY).json()[0]["id"]
        r = client.delete(f"/api/admin/users/{user_id}", headers=GOOD_KEY)
        assert r.status_code == 200
        assert client.get(ADMIN_USERS, headers=GOOD_KEY).json() == []

    def test_delete_cascades_all_data(self, client, db):
        user = _make_user(db)
        uid = user.id
        db.add(IncomeSource(user_id=uid, label="S", gross_annual_salary=30000, pay_frequency="annual", is_active=True))
        db.add(Expense(user_id=uid, category="Rent", amount=1000, frequency="monthly", is_fixed=True, is_active=True))
        db.add(Debt(user_id=uid, debt_type="credit_card", balance=500, interest_rate=19.9, min_payment=25, is_active=True))
        db.add(SavingsGoal(user_id=uid, name="Emergency", current_balance=1000, target_amount=5000, monthly_contribution=200, is_active=True))
        db.add(PensionPot(user_id=uid, current_balance=10000, employee_contribution_pct=5, employer_contribution_pct=3, is_active=True))
        db.add(Asset(user_id=uid, name="Car", asset_type="vehicle", current_value=8000, is_active=True))
        db.add(FinancialSnapshot(
            user_id=uid,
            captured_at=datetime.now(timezone.utc),
            net_worth=5000, monthly_disposable_income=500,
            total_savings_balance=1000, total_debt_balance=500,
            pension_pot_balance=10000,
        ))
        db.commit()

        r = client.delete(f"/api/admin/users/{uid}", headers=GOOD_KEY)
        assert r.status_code == 200

        # All child records gone
        assert db.query(IncomeSource).filter_by(user_id=uid).count() == 0
        assert db.query(Expense).filter_by(user_id=uid).count() == 0
        assert db.query(Debt).filter_by(user_id=uid).count() == 0
        assert db.query(SavingsGoal).filter_by(user_id=uid).count() == 0
        assert db.query(PensionPot).filter_by(user_id=uid).count() == 0
        assert db.query(Asset).filter_by(user_id=uid).count() == 0
        assert db.query(FinancialSnapshot).filter_by(user_id=uid).count() == 0
        assert db.query(User).filter_by(id=uid).first() is None

    def test_delete_requires_admin_key(self, client):
        _register(client)
        user_id = client.get(ADMIN_USERS, headers=GOOD_KEY).json()[0]["id"]
        assert client.delete(f"/api/admin/users/{user_id}").status_code == 403
        # User still exists
        assert len(client.get(ADMIN_USERS, headers=GOOD_KEY).json()) == 1
