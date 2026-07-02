import math
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SavingsGoal
from app.models.user import User
from app.routes.auth import get_current_user
from app.schemas import SavingsCreate, SavingsOut, SavingsProjectionOut, SavingsUpdate
from app.utils import get_owned_or_404

router = APIRouter(prefix="/savings", tags=["savings"])

_MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


@router.post("", response_model=SavingsOut, status_code=status.HTTP_201_CREATED)
def create_savings_goal(
    body: SavingsCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = body.model_dump()
    data['target_amount'] = data['target_amount'] or 0.0
    item = SavingsGoal(**data, user_id=current_user.id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("", response_model=list[SavingsOut])
def list_savings_goals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(SavingsGoal).filter_by(user_id=current_user.id, is_active=True).all()


@router.put("/{item_id}", response_model=SavingsOut)
def update_savings_goal(
    item_id: int,
    body: SavingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = get_owned_or_404(db, SavingsGoal, item_id, current_user.id)
    data = body.model_dump(exclude_unset=True)
    if 'target_amount' in data and data['target_amount'] is None:
        data['target_amount'] = 0.0
    for field, value in data.items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_savings_goal(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = get_owned_or_404(db, SavingsGoal, item_id, current_user.id)
    item.is_active = False
    db.commit()


@router.get("/{item_id}/projection", response_model=SavingsProjectionOut)
def get_savings_projection(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    goal = get_owned_or_404(db, SavingsGoal, item_id, current_user.id)

    if not goal.target_amount or goal.target_amount <= 0:
        raise HTTPException(status_code=400, detail="No target amount set for this goal.")
    if goal.monthly_contribution <= 0:
        raise HTTPException(status_code=400, detail="Monthly contribution must be greater than zero.")
    if goal.current_balance >= goal.target_amount:
        raise HTTPException(status_code=400, detail="Goal already reached.")

    months = math.ceil((goal.target_amount - goal.current_balance) / goal.monthly_contribution)

    today = date.today()
    total_months = today.month - 1 + months
    proj_year = today.year + total_months // 12
    proj_month = total_months % 12 + 1
    projected_date_str = f"{_MONTH_NAMES[proj_month - 1]} {proj_year}"

    return SavingsProjectionOut(months_to_goal=months, projected_date=projected_date_str)
