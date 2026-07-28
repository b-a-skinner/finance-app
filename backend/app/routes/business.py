import calendar
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import BusinessExpense, BusinessIncome, Invoice
from app.models.config import BusinessTaxConfig, TaxYearConfig
from app.services.tax_calculator import calculate_payments_on_account, calculate_sole_trader_tax
from app.models.user import User
from app.routes.auth import get_current_user
from app.schemas import (
    ApproveExpenseBody,
    ApproveIncomeBody,
    BusinessExpenseCreate,
    BusinessExpenseOut,
    BusinessExpenseUpdate,
    BusinessIncomeCreate,
    BusinessIncomeOut,
    BusinessIncomeUpdate,
    BusinessSummaryOut,
    BusinessTaxConfigOut,
    BusinessTaxYearsOut,
    BusinessUpcomingOut,
    SoleTraderTaxOut,
    TaxDeadlineFiguresOut,
)
from app.utils import get_owned_or_404

router = APIRouter(prefix="/business", tags=["business"])

_FREQ_DAY_DELTA = {
    "weekly":      7,
    "two_weekly":  14,
    "four_weekly": 28,
}
_FREQ_MONTH_DELTA = {
    "monthly":    1,
    "two_monthly": 2,
    "quarterly":  3,
    "biannually": 6,
    "annually":   12,
    "two_yearly": 24,
}


def _backfill_income(item: "BusinessIncome", db: "Session", today: date) -> None:
    """
    Creates confirmed transactions for all past occurrences of a newly-created recurring
    income entry, then advances the rolling entry to the first future occurrence.
    If every occurrence is already past (or beyond end_date), deactivates the entry.
    """
    freq      = item.recurrence_freq
    end_date  = item.recurrence_end_date
    occurrence = item.date_received

    while occurrence <= today and (end_date is None or occurrence <= end_date):
        db.add(BusinessIncome(
            user_id=item.user_id,
            amount=item.amount,
            date_received=occurrence,
            description=item.description,
            is_active=True,
            is_approved=True,
            recurrence_freq=None,
            recurrence_end_date=None,
        ))
        occurrence = _advance_date(occurrence, freq)

    if occurrence > today and (end_date is None or occurrence <= end_date):
        item.date_received = occurrence
    else:
        item.is_active = False


def _backfill_expense(item: "BusinessExpense", db: "Session", today: date) -> None:
    """
    Creates confirmed transactions for all past occurrences of a newly-created recurring
    expense entry, then advances the rolling entry to the first future occurrence.
    """
    freq      = item.recurrence_freq
    end_date  = item.recurrence_end_date
    occurrence = item.date_incurred

    while occurrence <= today and (end_date is None or occurrence <= end_date):
        db.add(BusinessExpense(
            user_id=item.user_id,
            amount=item.amount,
            date_incurred=occurrence,
            category=item.category,
            description=item.description,
            is_allowable=item.is_allowable,
            is_active=True,
            is_approved=True,
            business_use_percent=item.business_use_percent,
            expense_method=item.expense_method,
            home_office_hours_band=item.home_office_hours_band,
            business_miles=item.business_miles,
            vehicle_type=item.vehicle_type,
            recurrence_freq=None,
            recurrence_end_date=None,
        ))
        occurrence = _advance_date(occurrence, freq)

    if occurrence > today and (end_date is None or occurrence <= end_date):
        item.date_incurred = occurrence
    else:
        item.is_active = False


def _advance_date(from_date: date, freq: str) -> date:
    if freq in _FREQ_DAY_DELTA:
        return from_date + timedelta(days=_FREQ_DAY_DELTA[freq])
    if freq in _FREQ_MONTH_DELTA:
        months = _FREQ_MONTH_DELTA[freq]
        m = from_date.month + months
        year = from_date.year + (m - 1) // 12
        month = (m - 1) % 12 + 1
        day = min(from_date.day, calendar.monthrange(year, month)[1])
        return date(year, month, day)
    raise ValueError(f"Unknown recurrence frequency: {freq!r}")


def _tax_year_start() -> date:
    today = date.today()
    year = today.year if today >= date(today.year, 4, 6) else today.year - 1
    return date(year, 4, 6)


def _tax_year_end() -> date:
    start = _tax_year_start()
    return date(start.year + 1, 4, 5)


def _tax_year_label() -> str:
    start = _tax_year_start()
    return f"{start.year}/{str(start.year + 1)[2:]}"


def _tax_year_label_for_date(d: date) -> str:
    """The 'YYYY/YY' tax year label (6 April – 5 April) that a given date falls in."""
    year = d.year if d >= date(d.year, 4, 6) else d.year - 1
    return f"{year}/{str(year + 1)[2:]}"


def _tax_year_bounds(label: str) -> tuple[date, date]:
    """Parse a 'YYYY/YY' tax year label into its [6 April, 5 April] date bounds."""
    start_year = int(label.split("/")[0])
    return date(start_year, 4, 6), date(start_year + 1, 4, 5)


def _get_biz_config(db: Session, tax_year: str) -> BusinessTaxConfig | None:
    return db.query(BusinessTaxConfig).filter_by(tax_year=tax_year).first()


def _home_office_flat_rate(band: str | None, cfg: BusinessTaxConfig) -> float:
    return {
        "25_50":    cfg.home_office_band_25_50,
        "51_100":   cfg.home_office_band_51_100,
        "101_plus": cfg.home_office_band_101_plus,
    }.get(band or "", 0.0)


def _vehicle_rate_info(vehicle_type: str, cfg: BusinessTaxConfig) -> dict | None:
    """
    Returns the rate structure for a vehicle type from config.

    Tiered types have both first/over rates and a threshold — the two-tier flag
    is implicit in having these keys (not derived from the vehicle name).
    Flat types have only a single rate.
    Returns None for unknown vehicle types.
    """
    lookup: dict[str, dict] = {
        "car_van":    {"tiered": True,  "first": cfg.mileage_car_van_first,
                       "over": cfg.mileage_car_van_over, "threshold": cfg.mileage_threshold},
        "motorcycle": {"tiered": False, "rate": cfg.mileage_motorcycle},
        "bicycle":    {"tiered": False, "rate": cfg.mileage_bicycle},
    }
    return lookup.get(vehicle_type)


def _attribute_mileage_entries(
    entries: list,
    cfg: BusinessTaxConfig,
) -> tuple[float, dict[int, float]]:
    """
    Returns (annual_allowance_total, {entry_id: attributed_value}).

    Tiered vehicle types accrue cumulative miles against their own independent
    per-type threshold pool, ordered deterministically by (date_incurred, id).
    Flat-rate types: attributed = miles × rate, no cumulative dependency.
    """
    sorted_entries = sorted(entries, key=lambda e: (e.date_incurred, e.id))

    cumulative: dict[str, int] = {}   # vehicle_type → cumulative miles (tiered types only)
    per_entry:  dict[int, float] = {}

    for e in sorted_entries:
        miles = e.business_miles or 0
        vt    = e.vehicle_type or ""
        info  = _vehicle_rate_info(vt, cfg)

        if info is None:
            per_entry[e.id] = 0.0
            continue

        if info["tiered"]:
            threshold   = info["threshold"]
            before      = cumulative.get(vt, 0)
            after       = before + miles
            lower_miles = max(0, min(after, threshold) - before)
            upper_miles = miles - lower_miles
            value       = round(lower_miles * info["first"] + upper_miles * info["over"], 2)
            cumulative[vt] = after
        else:
            value = round(miles * info["rate"], 2)

        per_entry[e.id] = value

    annual_total = round(sum(per_entry.values()), 2)
    return annual_total, per_entry


def _mileage_crossover_msg(mileage_entries: list, cfg: BusinessTaxConfig) -> str | None:
    """Crossover / threshold status message for tiered vehicle types."""
    type_totals: dict[str, int] = {}
    for e in mileage_entries:
        info = _vehicle_rate_info(e.vehicle_type or "", cfg)
        if info and info["tiered"]:
            vt = e.vehicle_type
            type_totals[vt] = type_totals.get(vt, 0) + (e.business_miles or 0)

    if not type_totals:
        return None

    parts = []
    for vt in sorted(type_totals):
        total = type_totals[vt]
        if total == 0:
            continue
        info      = _vehicle_rate_info(vt, cfg)
        threshold = info["threshold"]
        if total < threshold:
            remaining = threshold - total
            parts.append(f"{remaining:,} miles remaining at {int(info['first'] * 100)}p/mile")
        else:
            over = total - threshold
            parts.append(f"Threshold reached — {over:,} miles at {int(info['over'] * 100)}p/mile")

    return "; ".join(parts) if parts else None


# ---------------------------------------------------------------------------
# Income
# ---------------------------------------------------------------------------

@router.get("/income", response_model=list[BusinessIncomeOut])
def list_income(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(BusinessIncome)
        .filter(
            BusinessIncome.user_id == current_user.id,
            BusinessIncome.is_active == True,
            BusinessIncome.is_approved == True,
        )
        .order_by(BusinessIncome.date_received.desc())
        .all()
    )


@router.post("/income", response_model=BusinessIncomeOut, status_code=status.HTTP_201_CREATED)
def create_income(
    body: BusinessIncomeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if body.recurrence_freq:
        # Rolling recurring entry always starts unapproved; past occurrences are backfilled.
        item = BusinessIncome(**body.model_dump(), user_id=current_user.id, is_approved=False)
        db.add(item)
        db.flush()
        if body.date_received <= date.today():
            _backfill_income(item, db, date.today())
    else:
        is_approved = body.date_received <= date.today()
        item = BusinessIncome(**body.model_dump(), user_id=current_user.id, is_approved=is_approved)
        db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/income/{item_id}", response_model=BusinessIncomeOut)
def update_income(
    item_id: int,
    body: BusinessIncomeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = get_owned_or_404(db, BusinessIncome, item_id, current_user.id)
    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(item, field, value)
    if 'date_received' in updates and item.date_received > date.today():
        item.is_approved = False
    db.commit()
    db.refresh(item)
    return item


@router.post("/income/{item_id}/approve", response_model=BusinessIncomeOut)
def approve_income(
    item_id: int,
    body: ApproveIncomeBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = get_owned_or_404(db, BusinessIncome, item_id, current_user.id)

    if item.recurrence_freq:
        # Recurring: per-occurrence edits apply only to the confirmed transaction.
        original_date    = item.date_received
        occurrence_date  = body.date_received if body.date_received is not None else item.date_received
        occurrence_amount = body.amount if body.amount is not None else item.amount

        if occurrence_date <= date.today():
            # Create a one-off confirmed transaction for this occurrence.
            confirmed = BusinessIncome(
                user_id=item.user_id,
                amount=occurrence_amount,
                date_received=occurrence_date,
                description=item.description,
                is_active=True,
                is_approved=True,
                recurrence_freq=None,
                recurrence_end_date=None,
            )
            db.add(confirmed)
            # Roll the recurring entry forward from the original date.
            next_date = _advance_date(original_date, item.recurrence_freq)
            if item.recurrence_end_date and next_date > item.recurrence_end_date:
                item.is_active = False
            else:
                item.date_received = next_date
        else:
            # Future date: reschedule this occurrence; don't confirm.
            item.date_received = occurrence_date
    else:
        # Non-recurring: existing approval logic.
        if body.amount is not None:
            item.amount = body.amount
        if body.date_received is not None:
            item.date_received = body.date_received
        if item.date_received <= date.today():
            item.is_approved = True

    # Invoice-linked income rows are never recurring (see
    # app/routes/invoices.py: _get_or_create_invoice_income), so approving one
    # here — via the exact same confirmation flow as any other income entry —
    # is how a sent invoice becomes "paid" whether the user confirms it from
    # here (Upcoming) or from the invoice's own "Mark as paid" action. Keeps
    # the invoice and its one linked income row from ever disagreeing.
    if item.invoice_id and item.is_approved:
        invoice = db.query(Invoice).filter_by(id=item.invoice_id).first()
        if invoice is not None:
            invoice.status = "paid"
            invoice.paid_date = item.date_received

    db.commit()
    db.refresh(item)
    return item


@router.post("/income/{item_id}/dismiss", status_code=status.HTTP_204_NO_CONTENT)
def dismiss_income(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = get_owned_or_404(db, BusinessIncome, item_id, current_user.id)
    if item.recurrence_freq:
        # Skip this occurrence: roll forward without creating a transaction.
        next_date = _advance_date(item.date_received, item.recurrence_freq)
        if item.recurrence_end_date and next_date > item.recurrence_end_date:
            item.is_active = False
        else:
            item.date_received = next_date
    else:
        item.is_active = False
    db.commit()


@router.delete("/income/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_income(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = get_owned_or_404(db, BusinessIncome, item_id, current_user.id)
    item.is_active = False
    db.commit()


# ---------------------------------------------------------------------------
# Expenses
# ---------------------------------------------------------------------------

@router.get("/expenses", response_model=list[BusinessExpenseOut])
def list_expenses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(BusinessExpense)
        .filter(
            BusinessExpense.user_id == current_user.id,
            BusinessExpense.is_active == True,
            BusinessExpense.is_approved == True,
        )
        .order_by(BusinessExpense.date_incurred.desc())
        .all()
    )


@router.post("/expenses", response_model=BusinessExpenseOut, status_code=status.HTTP_201_CREATED)
def create_expense(
    body: BusinessExpenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if body.recurrence_freq:
        item = BusinessExpense(**body.model_dump(), user_id=current_user.id, is_approved=False)
        db.add(item)
        db.flush()
        if body.date_incurred <= date.today():
            _backfill_expense(item, db, date.today())
    else:
        is_approved = body.date_incurred <= date.today()
        item = BusinessExpense(**body.model_dump(), user_id=current_user.id, is_approved=is_approved)
        db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/expenses/{item_id}", response_model=BusinessExpenseOut)
def update_expense(
    item_id: int,
    body: BusinessExpenseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = get_owned_or_404(db, BusinessExpense, item_id, current_user.id)
    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(item, field, value)
    if 'date_incurred' in updates and item.date_incurred > date.today():
        item.is_approved = False
    db.commit()
    db.refresh(item)
    return item


@router.post("/expenses/{item_id}/approve", response_model=BusinessExpenseOut)
def approve_expense(
    item_id: int,
    body: ApproveExpenseBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = get_owned_or_404(db, BusinessExpense, item_id, current_user.id)

    if item.recurrence_freq:
        original_date     = item.date_incurred
        occurrence_date   = body.date_incurred if body.date_incurred is not None else item.date_incurred
        occurrence_amount = body.amount if body.amount is not None else item.amount

        if occurrence_date <= date.today():
            confirmed = BusinessExpense(
                user_id=item.user_id,
                amount=occurrence_amount,
                date_incurred=occurrence_date,
                category=item.category,
                description=item.description,
                is_allowable=item.is_allowable,
                is_active=True,
                is_approved=True,
                business_use_percent=item.business_use_percent,
                expense_method=item.expense_method,
                home_office_hours_band=item.home_office_hours_band,
                business_miles=item.business_miles,
                vehicle_type=item.vehicle_type,
                recurrence_freq=None,
                recurrence_end_date=None,
            )
            db.add(confirmed)
            next_date = _advance_date(original_date, item.recurrence_freq)
            if item.recurrence_end_date and next_date > item.recurrence_end_date:
                item.is_active = False
            else:
                item.date_incurred = next_date
        else:
            item.date_incurred = occurrence_date
    else:
        if body.amount is not None:
            item.amount = body.amount
        if body.date_incurred is not None:
            item.date_incurred = body.date_incurred
        if item.date_incurred <= date.today():
            item.is_approved = True

    db.commit()
    db.refresh(item)
    return item


@router.post("/expenses/{item_id}/dismiss", status_code=status.HTTP_204_NO_CONTENT)
def dismiss_expense(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = get_owned_or_404(db, BusinessExpense, item_id, current_user.id)
    if item.recurrence_freq:
        next_date = _advance_date(item.date_incurred, item.recurrence_freq)
        if item.recurrence_end_date and next_date > item.recurrence_end_date:
            item.is_active = False
        else:
            item.date_incurred = next_date
    else:
        item.is_active = False
    db.commit()


@router.delete("/expenses/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = get_owned_or_404(db, BusinessExpense, item_id, current_user.id)
    item.is_active = False
    db.commit()


# ---------------------------------------------------------------------------
# Upcoming (scheduled + awaiting approval)
# ---------------------------------------------------------------------------

@router.get("/upcoming", response_model=BusinessUpcomingOut)
def get_upcoming(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    income = (
        db.query(BusinessIncome)
        .filter(
            BusinessIncome.user_id == current_user.id,
            BusinessIncome.is_active == True,
            BusinessIncome.is_approved == False,
        )
        .order_by(BusinessIncome.date_received.asc())
        .all()
    )
    expenses = (
        db.query(BusinessExpense)
        .filter(
            BusinessExpense.user_id == current_user.id,
            BusinessExpense.is_active == True,
            BusinessExpense.is_approved == False,
        )
        .order_by(BusinessExpense.date_incurred.asc())
        .all()
    )
    return BusinessUpcomingOut(income=income, expenses=expenses)


# ---------------------------------------------------------------------------
# Tax config (read-only — seeded, not user-editable)
# ---------------------------------------------------------------------------

def _years_with_data(db: Session, user_id: int) -> list[str]:
    """Tax years for which the user has at least one confirmed income or expense entry, most recent first."""
    income_dates = db.query(BusinessIncome.date_received).filter(
        BusinessIncome.user_id == user_id,
        BusinessIncome.is_active == True,
        BusinessIncome.is_approved == True,
    ).all()
    expense_dates = db.query(BusinessExpense.date_incurred).filter(
        BusinessExpense.user_id == user_id,
        BusinessExpense.is_active == True,
        BusinessExpense.is_approved == True,
    ).all()
    return sorted(
        {_tax_year_label_for_date(d) for (d,) in [*income_dates, *expense_dates]},
        key=lambda label: int(label.split("/")[0]),
        reverse=True,
    )


@router.get("/tax-years", response_model=BusinessTaxYearsOut)
def list_tax_years(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tax years for which the user has at least one confirmed income or expense entry."""
    return BusinessTaxYearsOut(years=_years_with_data(db, current_user.id), current_tax_year=_tax_year_label())


@router.get("/tax-config", response_model=BusinessTaxConfigOut)
def get_tax_config(
    tax_year: str | None = Query(None, description="Tax year label e.g. '2025/26'; defaults to the current tax year."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    label = tax_year or _tax_year_label()
    cfg = _get_biz_config(db, label)
    if not cfg:
        raise HTTPException(status_code=404, detail=f"Business tax config not found for {label}.")
    return cfg


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def _build_summary(db: Session, current_user: User, label: str) -> BusinessSummaryOut:
    start, end = _tax_year_bounds(label)
    cfg = _get_biz_config(db, label)
    tax_cfg = db.query(TaxYearConfig).filter_by(tax_year=label).first()

    income_ytd = (
        db.query(BusinessIncome)
        .filter(
            BusinessIncome.user_id == current_user.id,
            BusinessIncome.is_active == True,
            BusinessIncome.is_approved == True,
            BusinessIncome.date_received >= start,
            BusinessIncome.date_received <= end,
        )
        .all()
    )
    expenses_ytd = (
        db.query(BusinessExpense)
        .filter(
            BusinessExpense.user_id == current_user.id,
            BusinessExpense.is_active == True,
            BusinessExpense.is_approved == True,
            BusinessExpense.date_incurred >= start,
            BusinessExpense.date_incurred <= end,
        )
        .all()
    )

    any_income = (
        db.query(BusinessIncome.id)
        .filter_by(user_id=current_user.id, is_active=True)
        .first()
    )
    any_expense = (
        db.query(BusinessExpense.id)
        .filter_by(user_id=current_user.id, is_active=True)
        .first()
    )

    revenue = round(sum(i.amount for i in income_ytd), 2)

    mileage_entries = [e for e in expenses_ytd if e.expense_method == "mileage"]
    other_expenses  = [e for e in expenses_ytd if e.expense_method != "mileage"]

    # Per-entry mileage attribution (shared function — single source of truth)
    if cfg and mileage_entries:
        mileage_allowance, mileage_attribution = _attribute_mileage_entries(mileage_entries, cfg)
        crossover_msg = _mileage_crossover_msg(mileage_entries, cfg)
    else:
        mileage_allowance  = 0.0
        mileage_attribution: dict[int, float] = {}
        crossover_msg      = None

    cash_expenses     = 0.0
    allowable_cash    = 0.0
    home_office_allow = 0.0

    for e in other_expenses:
        method = e.expense_method

        if method == "home_office_flat":
            if cfg:
                rate = _home_office_flat_rate(e.home_office_hours_band, cfg)
                allowable_cash    += rate
                home_office_allow += rate

        elif method in ("home_office_actual", "percentage"):
            cash_expenses += e.amount
            pct = (e.business_use_percent or 100) / 100
            if e.is_allowable:
                allowable_cash += round(e.amount * pct, 2)

        else:
            cash_expenses += e.amount
            if e.is_allowable:
                allowable_cash += e.amount

    total_miles            = sum(e.business_miles or 0 for e in mileage_entries)
    allowable_expenses_ytd = round(allowable_cash + mileage_allowance, 2)
    total_expenses_ytd     = round(cash_expenses, 2)
    taxable_profit         = round(revenue - allowable_expenses_ytd, 2)
    home_office_allowance  = round(home_office_allow, 2)

    # Sole trader tax estimate — requires both configs and Class 4 fields seeded
    tax_estimate: SoleTraderTaxOut | None = None
    if cfg and tax_cfg and cfg.class4_lower_limit is not None:
        calc = calculate_sole_trader_tax(taxable_profit, tax_cfg, cfg, starting_income=0.0)
        tax_estimate = SoleTraderTaxOut(**vars(calc))

    return BusinessSummaryOut(
        tax_year=label,
        is_complete=end < date.today(),
        tax_config_available=cfg is not None,
        revenue_ytd=revenue,
        total_expenses_ytd=total_expenses_ytd,
        allowable_expenses_ytd=allowable_expenses_ytd,
        cash_profit=round(revenue - total_expenses_ytd, 2),
        taxable_profit=taxable_profit,
        has_business_data=any_income is not None or any_expense is not None,
        total_business_miles=total_miles,
        total_mileage_allowance=mileage_allowance,
        home_office_allowance=home_office_allowance,
        mileage_crossover_msg=crossover_msg,
        mileage_attribution=mileage_attribution,
        tax_estimate=tax_estimate,
    )


@router.get("/summary", response_model=BusinessSummaryOut)
def get_business_summary(
    tax_year: str | None = Query(None, description="Tax year label e.g. '2025/26'; defaults to the current tax year."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    label = tax_year or _tax_year_label()
    return _build_summary(db, current_user, label)


# ---------------------------------------------------------------------------
# Tax deadline figures — payments on account and balancing payment
# ---------------------------------------------------------------------------

def _prior_year_label(label: str) -> str:
    start_year = int(label.split("/")[0])
    return f"{start_year - 1}/{str(start_year)[2:]}"


def _next_year_label(label: str) -> str:
    start_year = int(label.split("/")[0])
    return f"{start_year + 1}/{str(start_year + 2)[2:]}"


def _get_poa_threshold(db: Session, label: str) -> float | None:
    cfg = _get_biz_config(db, label)
    return cfg.poa_threshold if cfg and cfg.poa_threshold is not None else None


def _compute_bill(db: Session, current_user: User, label: str) -> float | None:
    """Bill = income tax + Class 4 NI for the year (Class 2 excluded — see module docs).
    None if the tax estimate can't be computed (rates not seeded for this year)."""
    summary = _build_summary(db, current_user, label)
    if summary.tax_estimate is None:
        return None
    return round(summary.tax_estimate.income_tax_on_profit + summary.tax_estimate.class4_ni, 2)


def _unavailable(reason: str, last_completed_year: str | None = None, next_year: str | None = None,
                  bill_lcy: float | None = None, poa_threshold: float | None = None) -> TaxDeadlineFiguresOut:
    return TaxDeadlineFiguresOut(
        available=False, reason=reason, last_completed_year=last_completed_year, next_year=next_year,
        poa_threshold=poa_threshold, bill_lcy=bill_lcy,
    )


@router.get("/tax-deadlines", response_model=TaxDeadlineFiguresOut)
def get_tax_deadline_figures(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Payments on account (POA) and balancing payment for the January/July Self
    Assessment deadlines, computed from the most recent COMPLETED tax year (LCY)
    the user has confirmed data for — a finished year gives a finalised bill, so
    POAs are exact HMRC figures rather than a mid-year projection.

    Bill(N)      = income tax + Class 4 NI for year N (Class 2 is excluded: it's
                   either £0 for anyone paying Class 4, or voluntary otherwise, so
                   it never forms part of the POA/balancing calculation).
    POA(N+1)     = 50% × Bill(N) per instalment, only if Bill(N) > the de minimis
                   threshold (read from N's own config — never hardcoded).
    Balancing(N) = Bill(N) − (POAs derived from Bill(N−1), i.e. Bill(N−1) in full
                   if it was itself above N−1's threshold, else £0). This derives
                   POAs from the prior year's bill rather than tracking payments
                   actually made — correct in the normal case; no payment tracking.
    """
    years = _years_with_data(db, current_user.id)
    completed_years = [y for y in years if _tax_year_bounds(y)[1] < date.today()]
    if not completed_years:
        return _unavailable("no_completed_year")

    lcy = max(completed_years, key=lambda label: int(label.split("/")[0]))
    next_year = _next_year_label(lcy)

    bill_lcy = _compute_bill(db, current_user, lcy)
    poa_threshold = _get_poa_threshold(db, lcy)
    if bill_lcy is None or poa_threshold is None:
        return _unavailable("config_missing", last_completed_year=lcy, next_year=next_year, bill_lcy=bill_lcy, poa_threshold=poa_threshold)

    prior_label = _prior_year_label(lcy)
    bill_prior, prior_threshold = 0.0, poa_threshold
    if prior_label in years:
        bill_prior = _compute_bill(db, current_user, prior_label)
        prior_threshold = _get_poa_threshold(db, prior_label)
        if bill_prior is None or prior_threshold is None:
            # Data exists for the prior year but its rates aren't seeded — we can't
            # determine what POAs it would have set for this year, so we can't
            # safely compute this year's balancing payment either.
            return _unavailable("config_missing", last_completed_year=lcy, next_year=next_year, bill_lcy=bill_lcy, poa_threshold=poa_threshold)

    poa = calculate_payments_on_account(bill_lcy, poa_threshold, bill_prior, prior_threshold)

    return TaxDeadlineFiguresOut(
        available=True, reason=None, last_completed_year=lcy, next_year=next_year,
        poa_threshold=poa_threshold, bill_lcy=bill_lcy, poa_triggered=poa.poa_triggered,
        poa_instalment=poa.poa_instalment, balancing_payment=poa.balancing_payment,
        january_total=poa.january_total, july_total=poa.july_total,
    )
