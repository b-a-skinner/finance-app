from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import BusinessExpense, BusinessIncome
from app.models.config import BusinessTaxConfig
from app.models.user import User
from app.routes.auth import get_current_user
from app.schemas import (
    BusinessExpenseCreate,
    BusinessExpenseOut,
    BusinessExpenseUpdate,
    BusinessIncomeCreate,
    BusinessIncomeOut,
    BusinessIncomeUpdate,
    BusinessSummaryOut,
    BusinessTaxConfigOut,
)
from app.utils import get_owned_or_404

router = APIRouter(prefix="/business", tags=["business"])


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


def _get_biz_config(db: Session) -> BusinessTaxConfig | None:
    return db.query(BusinessTaxConfig).filter_by(tax_year=_tax_year_label()).first()


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
        .filter_by(user_id=current_user.id, is_active=True)
        .order_by(BusinessIncome.date_received.desc())
        .all()
    )


@router.post("/income", response_model=BusinessIncomeOut, status_code=status.HTTP_201_CREATED)
def create_income(
    body: BusinessIncomeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = BusinessIncome(**body.model_dump(), user_id=current_user.id)
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
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


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
        .filter_by(user_id=current_user.id, is_active=True)
        .order_by(BusinessExpense.date_incurred.desc())
        .all()
    )


@router.post("/expenses", response_model=BusinessExpenseOut, status_code=status.HTTP_201_CREATED)
def create_expense(
    body: BusinessExpenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = BusinessExpense(**body.model_dump(), user_id=current_user.id)
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
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


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
# Tax config (read-only — seeded, not user-editable)
# ---------------------------------------------------------------------------

@router.get("/tax-config", response_model=BusinessTaxConfigOut)
def get_tax_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cfg = _get_biz_config(db)
    if not cfg:
        raise HTTPException(status_code=404, detail="Business tax config not found for current tax year.")
    return cfg


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

@router.get("/summary", response_model=BusinessSummaryOut)
def get_business_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    start = _tax_year_start()
    end = _tax_year_end()
    cfg = _get_biz_config(db)

    income_ytd = (
        db.query(BusinessIncome)
        .filter(
            BusinessIncome.user_id == current_user.id,
            BusinessIncome.is_active == True,
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

    cash_expenses  = 0.0
    allowable_cash = 0.0

    for e in other_expenses:
        method = e.expense_method

        if method == "home_office_flat":
            if cfg:
                allowable_cash += _home_office_flat_rate(e.home_office_hours_band, cfg)

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

    return BusinessSummaryOut(
        revenue_ytd=revenue,
        total_expenses_ytd=total_expenses_ytd,
        allowable_expenses_ytd=allowable_expenses_ytd,
        cash_profit=round(revenue - total_expenses_ytd, 2),
        taxable_profit=round(revenue - allowable_expenses_ytd, 2),
        has_business_data=any_income is not None or any_expense is not None,
        total_business_miles=total_miles,
        total_mileage_allowance=mileage_allowance,
        mileage_crossover_msg=crossover_msg,
        mileage_attribution=mileage_attribution,
    )
