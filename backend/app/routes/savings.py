from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SavingsGoal
from app.models.user import User
from app.routes.auth import get_current_user
from app.schemas import SavingsCreate, SavingsOut, SavingsUpdate
from app.utils import get_owned_or_404

router = APIRouter(prefix="/savings", tags=["savings"])


@router.post("", response_model=SavingsOut, status_code=status.HTTP_201_CREATED)
def create_savings_goal(
    body: SavingsCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = SavingsGoal(**body.model_dump(), user_id=current_user.id)
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
    for field, value in body.model_dump(exclude_unset=True).items():
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
