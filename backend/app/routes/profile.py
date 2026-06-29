from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.routes.auth import get_current_user
from app.schemas import ProfileOut, ProfileUpdate
from app.services.postcode_lookup import get_region_from_postcode

router = APIRouter(prefix="/profile", tags=["profile"])


def _to_out(user: User) -> ProfileOut:
    return ProfileOut(
        date_of_birth=user.date_of_birth,
        occupation=user.occupation,
        postcode_outward=user.postcode_outward,
        region=get_region_from_postcode(user.postcode_outward),
    )


@router.get("", response_model=ProfileOut)
def get_profile(current_user: User = Depends(get_current_user)):
    return _to_out(current_user)


@router.put("", response_model=ProfileOut)
def update_profile(
    body: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return _to_out(current_user)
