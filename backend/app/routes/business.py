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


def _compute_mileage(car_van: int, moto: int, bike: int, cfg: BusinessTaxConfig) -> tuple[float, str | None]:
    threshold = cfg.mileage_threshold
    if car_van <= threshold:
        cv_allowance = car_van * cfg.mileage_car_van_first
    else:
        cv_allowance = (threshold * cfg.mileage_car_van_first
                        + (car_van - threshold) * cfg.mileage_car_van_over)

    total = round(cv_allowance + moto * cfg.mileage_motorcycle + bike * cfg.mileage_bicycle, 2)

    if car_van > 0 and car_van < threshold:
        remaining = threshold - car_van
        msg = f"{remaining:,} miles remaining at {int(cfg.mileage_car_van_first * 100)}p/mile"
    elif car_van >= threshold:
        over = car_van - threshold
        msg = f"Threshold reached — {over:,} miles at {int(cfg.mileage_car_van_over * 100)}p/mile"
    else:
        msg = None

    return total, msg


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

    cash_expenses   = 0.0
    allowable_cash  = 0.0
    car_van_miles   = 0
    moto_miles      = 0
    bike_miles      = 0

    for e in expenses_ytd:
        method = e.expense_method

        if method == "mileage":
            miles = e.business_miles or 0
            vt    = e.vehicle_type or ""
            if vt == "car_van":
                car_van_miles += miles
            elif vt == "motorcycle":
                moto_miles += miles
            elif vt == "bicycle":
                bike_miles += miles
            # mileage expenses have amount=0, don't add to cash

        elif method == "home_office_flat":
            # no cash outlay; allowable = HMRC flat rate for the month
            if cfg:
                allowable_cash += _home_office_flat_rate(e.home_office_hours_band, cfg)

        elif method in ("home_office_actual", "percentage"):
            cash_expenses  += e.amount
            pct = (e.business_use_percent or 100) / 100
            if e.is_allowable:
                allowable_cash += round(e.amount * pct, 2)

        else:
            # Standard expense
            cash_expenses += e.amount
            if e.is_allowable:
                allowable_cash += e.amount

    # Cumulative mileage allowance
    if cfg and (car_van_miles or moto_miles or bike_miles):
        mileage_allowance, crossover_msg = _compute_mileage(car_van_miles, moto_miles, bike_miles, cfg)
    else:
        mileage_allowance = 0.0
        crossover_msg     = None

    total_miles            = car_van_miles + moto_miles + bike_miles
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
    )
