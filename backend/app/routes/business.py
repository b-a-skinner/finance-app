from datetime import date

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import BusinessExpense, BusinessIncome
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
# Summary
# ---------------------------------------------------------------------------

@router.get("/summary", response_model=BusinessSummaryOut)
def get_business_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    start = _tax_year_start()
    end = _tax_year_end()

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

    revenue            = round(sum(i.amount for i in income_ytd), 2)
    total_expenses     = round(sum(e.amount for e in expenses_ytd), 2)
    allowable_expenses = round(sum(e.amount for e in expenses_ytd if e.is_allowable), 2)

    return BusinessSummaryOut(
        revenue_ytd=revenue,
        total_expenses_ytd=total_expenses,
        allowable_expenses_ytd=allowable_expenses,
        cash_profit=round(revenue - total_expenses, 2),
        taxable_profit=round(revenue - allowable_expenses, 2),
        has_business_data=any_income is not None or any_expense is not None,
    )
