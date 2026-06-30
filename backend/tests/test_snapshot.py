"""
Tests for financial snapshot capture and change comparison.
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.models import FinancialSnapshot, TaxYearConfig
from app.services.snapshot_service import (
    FinancialChanges,
    get_financial_changes,
    maybe_capture_snapshot,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

REGISTER = "/api/auth/register"
LOGIN = "/api/auth/login"
CHANGES = "/api/finance/changes"
SUMMARY = "/api/finance/summary"

_ALICE = {"email": "alice@example.com", "password": "s3cur3!"}
_BOB = {"email": "bob@example.com", "password": "s3cur3!"}


def _register(client, creds=_ALICE):
    return client.post(REGISTER, json=creds)


def _login(client, creds=_ALICE):
    return client.post(LOGIN, data={"username": creds["email"], "password": creds["password"]})


def _auth_header(client, creds=_ALICE):
    token = _login(client, creds).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _seed_tax_config(db):
    db.add(TaxYearConfig(
        tax_year="2026/27",
        personal_allowance=12570, basic_rate_threshold=50270, basic_rate_pct=20,
        higher_rate_threshold=125140, higher_rate_pct=40, additional_rate_pct=45,
        ni_primary_threshold=12584, ni_upper_threshold=50284,
        ni_main_rate_pct=8, ni_upper_rate_pct=2,
        pension_qualifying_lower=6240, pension_qualifying_upper=50270,
        pension_min_total_pct=8, pension_min_employer_pct=3,
    ))
    db.commit()


def _insert_snapshot(db, user_id: int, days_ago: float, **overrides) -> FinancialSnapshot:
    """Insert a FinancialSnapshot with captured_at set to `days_ago` days in the past."""
    captured_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
    defaults = dict(
        net_worth=10000.0,
        monthly_disposable_income=500.0,
        total_savings_balance=5000.0,
        total_debt_balance=2000.0,
        pension_pot_balance=8000.0,
        months_of_runway=3.0,
    )
    defaults.update(overrides)
    snap = FinancialSnapshot(user_id=user_id, captured_at=captured_at, **defaults)
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return snap


# ---------------------------------------------------------------------------
# maybe_capture_snapshot
# ---------------------------------------------------------------------------

class TestMaybeCaptureSnapshot:
    def test_creates_snapshot_when_none_exists(self, client, db):
        _seed_tax_config(db)
        user_id = _register(client).json()["user_id"]

        maybe_capture_snapshot(user_id, db)

        count = db.query(FinancialSnapshot).filter_by(user_id=user_id).count()
        assert count == 1

    def test_does_not_duplicate_within_24h(self, client, db):
        _seed_tax_config(db)
        user_id = _register(client).json()["user_id"]

        maybe_capture_snapshot(user_id, db)
        maybe_capture_snapshot(user_id, db)  # second call within 24h
        maybe_capture_snapshot(user_id, db)  # third call

        count = db.query(FinancialSnapshot).filter_by(user_id=user_id).count()
        assert count == 1

    def test_does_not_duplicate_with_recent_snapshot_in_db(self, client, db):
        _seed_tax_config(db)
        user_id = _register(client).json()["user_id"]

        # Existing snapshot from 2 hours ago
        _insert_snapshot(db, user_id, days_ago=2 / 24)

        maybe_capture_snapshot(user_id, db)

        count = db.query(FinancialSnapshot).filter_by(user_id=user_id).count()
        assert count == 1

    def test_creates_new_snapshot_after_24h(self, client, db):
        _seed_tax_config(db)
        user_id = _register(client).json()["user_id"]

        # Old snapshot from 25 hours ago
        _insert_snapshot(db, user_id, days_ago=25 / 24)

        maybe_capture_snapshot(user_id, db)

        count = db.query(FinancialSnapshot).filter_by(user_id=user_id).count()
        assert count == 2

    def test_skips_when_no_tax_config(self, client, db):
        # No tax config seeded — should not raise, should insert nothing
        user_id = _register(client).json()["user_id"]

        maybe_capture_snapshot(user_id, db)

        count = db.query(FinancialSnapshot).filter_by(user_id=user_id).count()
        assert count == 0

    def test_snapshot_records_correct_values(self, client, db):
        _seed_tax_config(db)
        user_id = _register(client).json()["user_id"]
        headers = _auth_header(client)

        client.post("/api/savings", json={
            "name": "ISA", "current_balance": 5000.0,
            "target_amount": 10000.0, "monthly_contribution": 0.0,
        }, headers=headers)
        client.post("/api/debts", json={
            "debt_type": "credit_card", "balance": 1000.0,
            "interest_rate": 20.0, "min_payment": 50.0, "student_loan_plan_id": None,
        }, headers=headers)

        maybe_capture_snapshot(user_id, db)

        snap = db.query(FinancialSnapshot).filter_by(user_id=user_id).first()
        assert snap.total_savings_balance == 5000.0
        assert snap.total_debt_balance == 1000.0
        assert snap.net_worth == 4000.0  # 5000 - 1000


# ---------------------------------------------------------------------------
# get_financial_changes — no / insufficient snapshots
# ---------------------------------------------------------------------------

class TestGetFinancialChangesNoData:
    def test_returns_both_null_when_no_snapshots(self, client, db):
        _seed_tax_config(db)
        user_id = _register(client).json()["user_id"]

        result = get_financial_changes(user_id, db)
        assert result.weekly is None
        assert result.monthly is None

    def test_returns_null_when_snapshot_too_recent(self, client, db):
        _seed_tax_config(db)
        user_id = _register(client).json()["user_id"]

        # Only a 3-day-old snapshot — not eligible for weekly (need >=6)
        _insert_snapshot(db, user_id, days_ago=3)

        result = get_financial_changes(user_id, db)
        assert result.weekly is None
        assert result.monthly is None

    def test_returns_null_monthly_when_only_8_day_old_snapshot(self, client, db):
        _seed_tax_config(db)
        user_id = _register(client).json()["user_id"]

        # 8 days — enough for weekly but not monthly (need >=27)
        _insert_snapshot(db, user_id, days_ago=8)

        result = get_financial_changes(user_id, db)
        assert result.weekly is not None
        assert result.monthly is None


# ---------------------------------------------------------------------------
# Band boundary tests for weekly comparison
# ---------------------------------------------------------------------------

class TestWeeklyComparisonBoundaries:
    def _result(self, client, db, days_ago):
        _seed_tax_config(db)
        user_id = _register(client).json()["user_id"]
        _insert_snapshot(db, user_id, days_ago=days_ago)
        return get_financial_changes(user_id, db)

    def test_exactly_6_days_matches_weekly(self, client, db):
        result = self._result(client, db, 6)
        assert result.weekly is not None
        assert result.weekly.elapsed_days == 6

    def test_5_days_does_not_match_weekly(self, client, db):
        result = self._result(client, db, 5)
        assert result.weekly is None

    def test_6_days_label_is_last_week(self, client, db):
        result = self._result(client, db, 6)
        assert result.weekly.label == "vs last week"

    def test_9_days_label_is_last_week(self, client, db):
        result = self._result(client, db, 9)
        assert result.weekly.label == "vs last week"

    def test_10_days_label_is_days_ago(self, client, db):
        result = self._result(client, db, 10)
        assert result.weekly.label == "vs 10 days ago"

    def test_no_caveat_within_range(self, client, db):
        result = self._result(client, db, 8)
        assert result.weekly.data_caveat is None

    def test_caveat_triggers_outside_range(self, client, db):
        result = self._result(client, db, 14)
        assert result.weekly.data_caveat is not None
        assert "14 days ago" in result.weekly.data_caveat


# ---------------------------------------------------------------------------
# Band boundary tests for monthly comparison
# ---------------------------------------------------------------------------

class TestMonthlyComparisonBoundaries:
    def _result(self, client, db, days_ago):
        _seed_tax_config(db)
        user_id = _register(client).json()["user_id"]
        _insert_snapshot(db, user_id, days_ago=days_ago)
        return get_financial_changes(user_id, db)

    def test_exactly_27_days_matches_monthly(self, client, db):
        result = self._result(client, db, 27)
        assert result.monthly is not None
        assert result.monthly.elapsed_days == 27

    def test_26_days_does_not_match_monthly(self, client, db):
        result = self._result(client, db, 26)
        assert result.monthly is None

    def test_27_days_label_is_last_month(self, client, db):
        result = self._result(client, db, 27)
        assert result.monthly.label == "vs last month"

    def test_32_days_label_is_last_month(self, client, db):
        result = self._result(client, db, 32)
        assert result.monthly.label == "vs last month"

    def test_33_days_label_is_days_ago(self, client, db):
        result = self._result(client, db, 33)
        assert result.monthly.label == "vs 33 days ago"

    def test_no_caveat_at_32_days(self, client, db):
        result = self._result(client, db, 32)
        assert result.monthly.data_caveat is None

    def test_caveat_triggers_at_33_days(self, client, db):
        result = self._result(client, db, 33)
        assert result.monthly.data_caveat is not None

    def test_caveat_triggers_at_40_days(self, client, db):
        result = self._result(client, db, 40)
        assert result.monthly.data_caveat is not None
        assert "40 days ago" in result.monthly.data_caveat


# ---------------------------------------------------------------------------
# Comparison values and direction
# ---------------------------------------------------------------------------

class TestComparisonValues:
    def _setup(self, client, db, prev_net_worth=10000.0, current_net_worth=None):
        _seed_tax_config(db)
        user_id = _register(client).json()["user_id"]
        headers = _auth_header(client)

        if current_net_worth is not None:
            # Add savings to drive net worth
            client.post("/api/savings", json={
                "name": "ISA", "current_balance": current_net_worth,
                "target_amount": 99999.0, "monthly_contribution": 0.0,
            }, headers=headers)

        _insert_snapshot(db, user_id, days_ago=8, net_worth=prev_net_worth)
        return user_id

    def test_direction_up_when_increased(self, client, db):
        user_id = self._setup(client, db, prev_net_worth=5000.0, current_net_worth=8000.0)
        result = get_financial_changes(user_id, db)
        assert result.weekly.net_worth.direction == "up"
        assert result.weekly.net_worth.absolute_change == 3000.0

    def test_direction_down_when_decreased(self, client, db):
        user_id = self._setup(client, db, prev_net_worth=10000.0, current_net_worth=7000.0)
        result = get_financial_changes(user_id, db)
        assert result.weekly.net_worth.direction == "down"
        assert result.weekly.net_worth.absolute_change == -3000.0

    def test_direction_unchanged_when_equal(self, client, db):
        user_id = self._setup(client, db, prev_net_worth=0.0, current_net_worth=None)
        result = get_financial_changes(user_id, db)
        assert result.weekly.net_worth.direction == "unchanged"
        assert result.weekly.net_worth.absolute_change == 0.0

    def test_current_and_previous_values_populated(self, client, db):
        user_id = self._setup(client, db, prev_net_worth=5000.0, current_net_worth=8000.0)
        result = get_financial_changes(user_id, db)
        nw = result.weekly.net_worth
        assert nw.previous_value == 5000.0
        assert nw.current_value == 8000.0

    def test_runway_null_when_current_has_null_runway(self, client, db):
        _seed_tax_config(db)
        user_id = _register(client).json()["user_id"]
        # No expenses → current runway is null; snapshot has non-null runway
        _insert_snapshot(db, user_id, days_ago=8, months_of_runway=3.0)
        result = get_financial_changes(user_id, db)
        # Current runway is null (no expenses set), previous is 3.0 — omit the metric
        assert result.weekly.months_of_runway is None

    def test_most_recent_snapshot_used_for_weekly_not_oldest(self, client, db):
        # Two snapshots: 8 days ago and 15 days ago — weekly should use 8-day-old one
        _seed_tax_config(db)
        user_id = _register(client).json()["user_id"]
        _insert_snapshot(db, user_id, days_ago=15, net_worth=1000.0)
        _insert_snapshot(db, user_id, days_ago=8,  net_worth=5000.0)
        result = get_financial_changes(user_id, db)
        assert result.weekly.net_worth.previous_value == 5000.0


# ---------------------------------------------------------------------------
# Isolation between users
# ---------------------------------------------------------------------------

class TestSnapshotIsolation:
    def test_snapshots_isolated_between_users(self, client, db):
        _seed_tax_config(db)
        alice_id = _register(client, _ALICE).json()["user_id"]
        bob_id = _register(client, _BOB).json()["user_id"]

        _insert_snapshot(db, alice_id, days_ago=8, net_worth=50000.0)

        bob_result = get_financial_changes(bob_id, db)
        assert bob_result.weekly is None


# ---------------------------------------------------------------------------
# HTTP endpoint tests
# ---------------------------------------------------------------------------

class TestChangesEndpoint:
    def test_requires_auth(self, client, db):
        resp = client.get(CHANGES)
        assert resp.status_code == 401

    def test_returns_200_with_null_comparisons_for_new_user(self, client, db):
        _seed_tax_config(db)
        _register(client)
        body = client.get(CHANGES, headers=_auth_header(client)).json()
        assert body["weekly"] is None
        assert body["monthly"] is None

    def test_calling_changes_creates_snapshot(self, client, db):
        _seed_tax_config(db)
        user_id = _register(client).json()["user_id"]

        assert db.query(FinancialSnapshot).filter_by(user_id=user_id).count() == 0
        client.get(CHANGES, headers=_auth_header(client))
        assert db.query(FinancialSnapshot).filter_by(user_id=user_id).count() == 1

    def test_weekly_comparison_returned_in_response(self, client, db):
        _seed_tax_config(db)
        user_id = _register(client).json()["user_id"]

        _insert_snapshot(db, user_id, days_ago=8)

        body = client.get(CHANGES, headers=_auth_header(client)).json()
        assert body["weekly"] is not None
        assert body["weekly"]["label"] == "vs last week"
        assert body["weekly"]["elapsed_days"] == 8
        assert "net_worth" in body["weekly"]
        assert "direction" in body["weekly"]["net_worth"]

    def test_calling_summary_also_creates_snapshot(self, client, db):
        _seed_tax_config(db)
        user_id = _register(client).json()["user_id"]

        client.get(SUMMARY, headers=_auth_header(client))
        assert db.query(FinancialSnapshot).filter_by(user_id=user_id).count() == 1
