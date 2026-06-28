from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import IncomeSource
from app.models.user import User
from app.routes.auth import get_current_user
from app.schemas import IncomeCreate, IncomeOut, IncomeUpdate
from app.utils import get_owned_or_404

router = APIRouter(prefix="/income", tags=["income"])


@router.post("", response_model=IncomeOut, status_code=status.HTTP_201_CREATED)
def create_income(
    body: IncomeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = IncomeSource(**body.model_dump(), user_id=current_user.id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("", response_model=list[IncomeOut])
def list_income(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(IncomeSource).filter_by(user_id=current_user.id, is_active=True).all()


@router.put("/{item_id}", response_model=IncomeOut)
def update_income(
    item_id: int,
    body: IncomeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = get_owned_or_404(db, IncomeSource, item_id, current_user.id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_income(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = get_owned_or_404(db, IncomeSource, item_id, current_user.id)
    item.is_active = False
    db.commit()
