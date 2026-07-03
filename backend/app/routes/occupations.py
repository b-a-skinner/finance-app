from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.config import OccupationCode
from app.schemas import OccupationOut

router = APIRouter(prefix="/occupations", tags=["occupations"])


@router.get("", response_model=list[OccupationOut])
def list_occupations(db: Session = Depends(get_db)):
    return (
        db.query(OccupationCode)
        .order_by(OccupationCode.soc_group, OccupationCode.title)
        .all()
    )
