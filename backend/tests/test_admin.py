"""
Admin endpoint tests.
All tests use the in-memory SQLite DB wired up in conftest.py.
ADMIN_KEY is set to "test-admin-key" by conftest before app import.
"""
import json
from datetime import date, datetime, timezone

from app.models import Asset, BusinessExpense, BusinessIncome, Debt, Expense, FinancialSnapshot, IncomeSource, PensionPot, SavingsGoal
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


# ---------------------------------------------------------------------------
# Business-side metrics — overview, type breakdown, feature adoption, badges.
# Business income/expense amounts are set to non-trivial, distinctive values
# specifically so the "no monetary values" tests below would catch them if
# they ever leaked into the admin response.
# ---------------------------------------------------------------------------

def _completed_tax_year_date() -> date:
    """A date inside a UK tax year whose 5 April has already passed."""
    today = date.today()
    current_start_year = today.year if today >= date(today.year, 4, 6) else today.year - 1
    return date(current_start_year - 1, 6, 15)


def _current_tax_year_date() -> date:
    return date.today()


class TestAdminBusinessMode:
    def test_business_mode_false_by_default(self, client, db):
        _make_user(db)
        u = client.get(ADMIN_USERS, headers=GOOD_KEY).json()[0]
        assert u["business_mode"] is False
        assert u["business_type"] is None

    def test_business_mode_true_from_active_mode(self, client, db):
        user = _make_user(db)
        user.active_mode = "business"
        db.commit()
        u = client.get(ADMIN_USERS, headers=GOOD_KEY).json()[0]
        assert u["business_mode"] is True

    def test_business_mode_true_from_business_type_even_if_active_mode_personal(self, client, db):
        """A user who set a business type but has since switched back to personal
        mode still counts as having 'ever used' business mode."""
        user = _make_user(db)
        user.active_mode = "personal"
        user.business_type = "sole_trader"
        db.commit()
        u = client.get(ADMIN_USERS, headers=GOOD_KEY).json()[0]
        assert u["business_mode"] is True
        assert u["business_type"] == "sole_trader"

    def test_business_features_all_false_with_no_data(self, client, db):
        user = _make_user(db)
        user.active_mode = "business"
        db.commit()
        u = client.get(ADMIN_USERS, headers=GOOD_KEY).json()[0]
        for key in ("income", "expenses", "mileage", "home_office", "recurring", "scheduled"):
            assert u["business_features"][key] is False

    def test_business_features_income_and_expenses(self, client, db):
        user = _make_user(db)
        db.add(BusinessIncome(user_id=user.id, amount=5000.0, date_received=_current_tax_year_date(), is_active=True, is_approved=True))
        db.add(BusinessExpense(user_id=user.id, amount=200.0, date_incurred=_current_tax_year_date(), category="software", is_active=True, is_approved=True))
        db.commit()
        u = client.get(ADMIN_USERS, headers=GOOD_KEY).json()[0]
        assert u["business_features"]["income"] is True
        assert u["business_features"]["expenses"] is True
        assert u["business_features"]["mileage"] is False
        assert u["business_features"]["home_office"] is False

    def test_business_features_mileage(self, client, db):
        user = _make_user(db)
        db.add(BusinessExpense(
            user_id=user.id, amount=0, date_incurred=_current_tax_year_date(), category="travel",
            is_active=True, is_approved=True, expense_method="mileage", business_miles=100, vehicle_type="car_van",
        ))
        db.commit()
        u = client.get(ADMIN_USERS, headers=GOOD_KEY).json()[0]
        assert u["business_features"]["mileage"] is True
        assert u["business_features"]["expenses"] is True  # any BusinessExpense row counts, mileage included

    def test_business_features_home_office(self, client, db):
        user = _make_user(db)
        db.add(BusinessExpense(
            user_id=user.id, amount=0, date_incurred=_current_tax_year_date(), category="home_office",
            is_active=True, is_approved=True, expense_method="home_office_flat", home_office_hours_band="25_50",
        ))
        db.commit()
        u = client.get(ADMIN_USERS, headers=GOOD_KEY).json()[0]
        assert u["business_features"]["home_office"] is True

    def test_business_features_recurring_income(self, client, db):
        user = _make_user(db)
        db.add(BusinessIncome(
            user_id=user.id, amount=1000.0, date_received=_current_tax_year_date(),
            is_active=True, is_approved=False, recurrence_freq="monthly",
        ))
        db.commit()
        u = client.get(ADMIN_USERS, headers=GOOD_KEY).json()[0]
        assert u["business_features"]["recurring"] is True

    def test_business_features_recurring_expense(self, client, db):
        user = _make_user(db)
        db.add(BusinessExpense(
            user_id=user.id, amount=50.0, date_incurred=_current_tax_year_date(), category="software",
            is_active=True, is_approved=False, recurrence_freq="monthly",
        ))
        db.commit()
        u = client.get(ADMIN_USERS, headers=GOOD_KEY).json()[0]
        assert u["business_features"]["recurring"] is True

    def test_business_features_scheduled_future_dated_entry(self, client, db):
        from datetime import timedelta
        future = date.today() + timedelta(days=30)
        user = _make_user(db)
        db.add(BusinessIncome(user_id=user.id, amount=1000.0, date_received=future, is_active=True, is_approved=False))
        db.commit()
        u = client.get(ADMIN_USERS, headers=GOOD_KEY).json()[0]
        assert u["business_features"]["scheduled"] is True

    def test_inactive_business_rows_excluded_from_badges(self, client, db):
        user = _make_user(db)
        db.add(BusinessIncome(user_id=user.id, amount=1000.0, date_received=_current_tax_year_date(), is_active=False, is_approved=True))
        db.commit()
        u = client.get(ADMIN_USERS, headers=GOOD_KEY).json()[0]
        assert u["business_features"]["income"] is False


class TestAdminBusinessOverview:
    def test_empty_overview(self, client):
        s = client.get(ADMIN_STATS, headers=GOOD_KEY).json()
        bo = s["business_overview"]
        assert bo["users_in_business_mode"] == 0
        assert bo["users_with_business_income"] == 0
        assert bo["users_with_business_expenses"] == 0
        assert bo["users_with_completed_tax_year"] == 0

    def test_users_in_business_mode_counts_both_signals(self, client, db):
        u1 = _make_user(db, "b1@example.com")
        u1.active_mode = "business"
        u2 = _make_user(db, "b2@example.com")
        u2.business_type = "llp"
        _make_user(db, "personal-only@example.com")  # not in business mode
        db.commit()
        bo = client.get(ADMIN_STATS, headers=GOOD_KEY).json()["business_overview"]
        assert bo["users_in_business_mode"] == 2

    def test_users_with_business_income_and_expenses(self, client, db):
        u1 = _make_user(db, "inc@example.com")
        u2 = _make_user(db, "exp@example.com")
        db.add(BusinessIncome(user_id=u1.id, amount=2000.0, date_received=_current_tax_year_date(), is_active=True, is_approved=True))
        db.add(BusinessExpense(user_id=u2.id, amount=300.0, date_incurred=_current_tax_year_date(), category="software", is_active=True, is_approved=True))
        db.commit()
        bo = client.get(ADMIN_STATS, headers=GOOD_KEY).json()["business_overview"]
        assert bo["users_with_business_income"] == 1
        assert bo["users_with_business_expenses"] == 1

    def test_users_with_completed_tax_year(self, client, db):
        completed_user = _make_user(db, "completed@example.com")
        current_only_user = _make_user(db, "current-only@example.com")
        db.add(BusinessIncome(user_id=completed_user.id, amount=9000.0, date_received=_completed_tax_year_date(), is_active=True, is_approved=True))
        db.add(BusinessIncome(user_id=current_only_user.id, amount=1000.0, date_received=_current_tax_year_date(), is_active=True, is_approved=True))
        db.commit()
        bo = client.get(ADMIN_STATS, headers=GOOD_KEY).json()["business_overview"]
        assert bo["users_with_completed_tax_year"] == 1


class TestAdminBusinessTypeBreakdown:
    def test_counts_across_types(self, client, db):
        types = ["sole_trader", "sole_trader", "limited_company", "partnership", "llp", "not_sure"]
        for i, t in enumerate(types):
            u = _make_user(db, f"type{i}@example.com")
            u.business_type = t
        db.commit()
        breakdown = client.get(ADMIN_STATS, headers=GOOD_KEY).json()["business_type_breakdown"]
        assert breakdown["sole_trader"] == 2
        assert breakdown["limited_company"] == 1
        assert breakdown["partnership"] == 1
        assert breakdown["llp"] == 1
        assert breakdown["not_sure"] == 1
        assert breakdown["not_set"] == 0

    def test_business_mode_without_chosen_type_counts_as_not_set(self, client, db):
        u = _make_user(db, "nomode@example.com")
        u.active_mode = "business"
        db.commit()
        breakdown = client.get(ADMIN_STATS, headers=GOOD_KEY).json()["business_type_breakdown"]
        assert breakdown["not_set"] == 1

    def test_non_business_users_excluded_from_breakdown(self, client, db):
        _make_user(db, "purely-personal@example.com")
        breakdown = client.get(ADMIN_STATS, headers=GOOD_KEY).json()["business_type_breakdown"]
        assert sum(breakdown.values()) == 0


class TestAdminBusinessFeatureAdoption:
    def test_denominator_is_business_mode_users_only(self, client, db):
        biz_user = _make_user(db, "biz@example.com")
        biz_user.active_mode = "business"
        _make_user(db, "personal@example.com")  # not business mode — must not count in denominator
        db.add(BusinessIncome(user_id=biz_user.id, amount=4000.0, date_received=_current_tax_year_date(), is_active=True, is_approved=True))
        db.commit()
        fa = client.get(ADMIN_STATS, headers=GOOD_KEY).json()["business_feature_adoption"]
        assert fa["income"] == 100.0  # 1 of 1 business-mode user, not 1 of 2 total users

    def test_zero_percent_with_no_usage(self, client, db):
        u = _make_user(db, "biz2@example.com")
        u.active_mode = "business"
        db.commit()
        fa = client.get(ADMIN_STATS, headers=GOOD_KEY).json()["business_feature_adoption"]
        for key in ("income", "expenses", "mileage", "home_office", "recurring", "scheduled"):
            assert fa[key] == 0.0

    def test_partial_adoption_percentage(self, client, db):
        u1 = _make_user(db, "biz3@example.com"); u1.active_mode = "business"
        u2 = _make_user(db, "biz4@example.com"); u2.active_mode = "business"
        db.add(BusinessIncome(user_id=u1.id, amount=1000.0, date_received=_current_tax_year_date(), is_active=True, is_approved=True))
        db.commit()
        fa = client.get(ADMIN_STATS, headers=GOOD_KEY).json()["business_feature_adoption"]
        assert fa["income"] == 50.0

    def test_feature_adoption_keys_present(self, client):
        fa = client.get(ADMIN_STATS, headers=GOOD_KEY).json()["business_feature_adoption"]
        for key in ("income", "expenses", "mileage", "home_office", "recurring", "scheduled"):
            assert key in fa


# ---------------------------------------------------------------------------
# Privacy boundary — the admin page must NEVER surface monetary figures,
# personal or business. This is the single most important guarantee in this
# file: it seeds real, distinctive money amounts and asserts none of them,
# nor any known monetary field name, appear anywhere in either admin response.
# ---------------------------------------------------------------------------

FORBIDDEN_MONEY_TOKENS = [
    "amount", "revenue", "profit", "balance", "salary", "net_worth",
    "current_value", "target_amount", "monthly_contribution", "gross_annual",
    "interest_rate", "min_payment", "tax_due", "tax_owed", "tax_estimate",
    "income_tax", "class4", "total_set_aside", "cash_profit", "taxable_profit",
]

# A distinctive amount that would be easy to spot leaking into the JSON if the
# forbidden-token scan above ever missed a new field name.
_TELLTALE_AMOUNT = 123456.78


class TestAdminNoMonetaryValues:
    def _seed_full_dataset(self, db):
        user = _make_user(db, "moneytest@example.com")
        user.active_mode = "business"
        user.business_type = "sole_trader"
        db.add(IncomeSource(user_id=user.id, label="Salary", gross_annual_salary=_TELLTALE_AMOUNT, pay_frequency="annual", is_active=True))
        db.add(Debt(user_id=user.id, debt_type="credit_card", balance=_TELLTALE_AMOUNT, interest_rate=19.9, min_payment=25, is_active=True))
        db.add(SavingsGoal(user_id=user.id, name="Emergency", current_balance=_TELLTALE_AMOUNT, target_amount=5000, monthly_contribution=200, is_active=True))
        db.add(PensionPot(user_id=user.id, current_balance=_TELLTALE_AMOUNT, employee_contribution_pct=5, employer_contribution_pct=3, is_active=True))
        db.add(Asset(user_id=user.id, name="Car", asset_type="vehicle", current_value=_TELLTALE_AMOUNT, is_active=True))
        db.add(BusinessIncome(user_id=user.id, amount=_TELLTALE_AMOUNT, date_received=_completed_tax_year_date(), is_active=True, is_approved=True))
        db.add(BusinessExpense(
            user_id=user.id, amount=_TELLTALE_AMOUNT, date_incurred=_completed_tax_year_date(), category="software",
            is_active=True, is_approved=True,
        ))
        db.commit()
        return user

    def test_no_monetary_values_in_users_response(self, client, db):
        self._seed_full_dataset(db)
        payload = client.get(ADMIN_USERS, headers=GOOD_KEY).json()
        text = json.dumps(payload).lower()
        assert str(_TELLTALE_AMOUNT) not in text
        for token in FORBIDDEN_MONEY_TOKENS:
            assert token not in text, f"Forbidden monetary token '{token}' found in /admin/users response"

    def test_no_monetary_values_in_stats_response(self, client, db):
        self._seed_full_dataset(db)
        payload = client.get(ADMIN_STATS, headers=GOOD_KEY).json()
        text = json.dumps(payload).lower()
        assert str(_TELLTALE_AMOUNT) not in text
        for token in FORBIDDEN_MONEY_TOKENS:
            assert token not in text, f"Forbidden monetary token '{token}' found in /admin/stats response"
