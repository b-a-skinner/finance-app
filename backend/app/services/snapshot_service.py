"""
Lazy snapshot capture and financial change computation.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.finance import FinancialSnapshot
from app.services.finance_summary import compute_snapshot_values


# ── Result types ─────────────────────────────────────────────────────────────

@dataclass
class MetricChange:
    current_value: float
    previous_value: float
    absolute_change: float
    direction: str          # "up" | "down" | "unchanged"
    elapsed_days: int


@dataclass
class ComparisonPeriod:
    label: str              # "vs last week" | "vs last month" | "vs X days ago"
    elapsed_days: int
    data_caveat: Optional[str]  # non-null when gap differs notably from intended period
    net_worth: MetricChange
    monthly_disposable_income: MetricChange
    total_savings_balance: MetricChange
    total_debt_balance: MetricChange
    pension_pot_balance: MetricChange
    months_of_runway: Optional[MetricChange]  # null when either endpoint has null runway


@dataclass
class FinancialChanges:
    weekly: Optional[ComparisonPeriod]
    monthly: Optional[ComparisonPeriod]


# ── Snapshot capture ──────────────────────────────────────────────────────────

def maybe_capture_snapshot(user_id: int, db: Session) -> None:
    """
    Insert a FinancialSnapshot unless one already exists within the last 24 hours.
    Safe to call on every request — the 24-hour guard keeps the table lean.
    Silently skips if the tax config is not yet seeded (avoids recording zeros).
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    already_captured = (
        db.query(FinancialSnapshot)
        .filter(
            FinancialSnapshot.user_id == user_id,
            FinancialSnapshot.captured_at >= cutoff,
        )
        .first()
    )
    if already_captured:
        return

    values = compute_snapshot_values(user_id, db)
    if values is None:
        return

    db.add(FinancialSnapshot(
        user_id=user_id,
        captured_at=datetime.now(timezone.utc),
        net_worth=values.net_worth,
        monthly_disposable_income=values.monthly_disposable_income,
        total_savings_balance=values.total_savings_balance,
        total_debt_balance=values.total_debt_balance,
        pension_pot_balance=values.pension_pot_balance,
        months_of_runway=values.months_of_runway,
    ))
    db.commit()


# ── Change computation ────────────────────────────────────────────────────────

def _metric_change(current_val: float, prev_val: float, elapsed_days: int) -> MetricChange:
    delta = round(current_val - prev_val, 2)
    direction = "up" if delta > 0 else ("down" if delta < 0 else "unchanged")
    return MetricChange(
        current_value=current_val,
        previous_value=prev_val,
        absolute_change=delta,
        direction=direction,
        elapsed_days=elapsed_days,
    )


def _aware(dt: datetime) -> datetime:
    """Make a datetime timezone-aware (UTC) if it is naive — SQLite drops tzinfo."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _find_eligible_snapshot(
    snapshots: list[FinancialSnapshot],
    now: datetime,
    min_days: int,
) -> Optional[FinancialSnapshot]:
    """Return the most recent snapshot that is at least min_days old."""
    cutoff = now - timedelta(days=min_days)
    for snap in snapshots:
        if _aware(snap.captured_at) <= cutoff:
            return snap
    return None


def _build_period(
    current_values: "SnapshotValues",  # type: ignore[name-defined]
    snap: FinancialSnapshot,
    now: datetime,
    exact_min: int,
    exact_max: int,
    periodic_label: str,
) -> ComparisonPeriod:
    elapsed = (now - _aware(snap.captured_at)).days

    if exact_min <= elapsed <= exact_max:
        label = periodic_label
    else:
        label = f"vs {elapsed} days ago"

    data_caveat: Optional[str] = None
    if elapsed > exact_max:
        period_name = periodic_label.replace("vs ", "")
        data_caveat = (
            f"Nearest available snapshot is {elapsed} days ago "
            f"(further back than the intended {period_name})"
        )

    runway_change: Optional[MetricChange] = None
    if current_values.months_of_runway is not None and snap.months_of_runway is not None:
        runway_change = _metric_change(
            current_values.months_of_runway, snap.months_of_runway, elapsed
        )

    return ComparisonPeriod(
        label=label,
        elapsed_days=elapsed,
        data_caveat=data_caveat,
        net_worth=_metric_change(current_values.net_worth, snap.net_worth, elapsed),
        monthly_disposable_income=_metric_change(
            current_values.monthly_disposable_income, snap.monthly_disposable_income, elapsed
        ),
        total_savings_balance=_metric_change(
            current_values.total_savings_balance, snap.total_savings_balance, elapsed
        ),
        total_debt_balance=_metric_change(
            current_values.total_debt_balance, snap.total_debt_balance, elapsed
        ),
        pension_pot_balance=_metric_change(
            current_values.pension_pot_balance, snap.pension_pot_balance, elapsed
        ),
        months_of_runway=runway_change,
    )


def get_financial_changes(user_id: int, db: Session) -> FinancialChanges:
    """
    Compute weekly and monthly change comparisons against historical snapshots.

    Uses live current values (via compute_snapshot_values) so the comparison
    reflects the state right now, not the state when the most recent snapshot
    was taken (which could be up to 24 hours ago).
    """
    current_values = compute_snapshot_values(user_id, db)
    if current_values is None:
        return FinancialChanges(weekly=None, monthly=None)

    snapshots: list[FinancialSnapshot] = (
        db.query(FinancialSnapshot)
        .filter_by(user_id=user_id)
        .order_by(FinancialSnapshot.captured_at.desc())
        .all()
    )

    if not snapshots:
        return FinancialChanges(weekly=None, monthly=None)

    now = datetime.now(timezone.utc)

    weekly_snap = _find_eligible_snapshot(snapshots, now, min_days=6)
    monthly_snap = _find_eligible_snapshot(snapshots, now, min_days=27)

    weekly = (
        _build_period(current_values, weekly_snap, now, 6, 9, "vs last week")
        if weekly_snap else None
    )
    monthly = (
        _build_period(current_values, monthly_snap, now, 27, 32, "vs last month")
        if monthly_snap else None
    )

    return FinancialChanges(weekly=weekly, monthly=monthly)
