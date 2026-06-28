from fastapi import HTTPException, status
from sqlalchemy.orm import Session


def get_owned_or_404(db: Session, model, item_id: int, user_id: int):
    """
    Fetch an active record by id that belongs to user_id.
    Returns 404 whether the record doesn't exist OR belongs to a different user,
    so callers can't distinguish the two cases (no data leakage).
    """
    item = db.query(model).filter_by(id=item_id, user_id=user_id, is_active=True).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return item
