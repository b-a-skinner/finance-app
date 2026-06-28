from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Debt
from app.models.user import User
from app.routes.auth import get_current_user
from app.schemas import DebtCreate, DebtOut, DebtUpdate
from app.utils import get_owned_or_404

router = APIRouter(prefix="/debts", tags=["debts"])


@router.post("", response_model=DebtOut, status_code=status.HTTP_201_CREATED)
def create_debt(
    body: DebtCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = Debt(**body.model_dump(), user_id=current_user.id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("", response_model=list[DebtOut])
def list_debts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Debt).filter_by(user_id=current_user.id, is_active=True).all()


@router.put("/{item_id}", response_model=DebtOut)
def update_debt(
    item_id: int,
    body: DebtUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = get_owned_or_404(db, Debt, item_id, current_user.id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_debt(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = get_owned_or_404(db, Debt, item_id, current_user.id)
    item.is_active = False
    db.commit()
