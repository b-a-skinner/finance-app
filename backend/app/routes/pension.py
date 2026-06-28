from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PensionPot
from app.models.user import User
from app.routes.auth import get_current_user
from app.schemas import PensionCreate, PensionOut, PensionUpdate
from app.utils import get_owned_or_404

router = APIRouter(prefix="/pension", tags=["pension"])


@router.post("", response_model=PensionOut, status_code=status.HTTP_201_CREATED)
def create_pension_pot(
    body: PensionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = PensionPot(**body.model_dump(), user_id=current_user.id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("", response_model=list[PensionOut])
def list_pension_pots(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(PensionPot).filter_by(user_id=current_user.id, is_active=True).all()


@router.put("/{item_id}", response_model=PensionOut)
def update_pension_pot(
    item_id: int,
    body: PensionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = get_owned_or_404(db, PensionPot, item_id, current_user.id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pension_pot(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = get_owned_or_404(db, PensionPot, item_id, current_user.id)
    item.is_active = False
    db.commit()
