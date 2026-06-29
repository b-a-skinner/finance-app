from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.config import StudentLoanPlanConfig

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/student-loan-plans")
def list_student_loan_plans(db: Session = Depends(get_db)):
    plans = db.query(StudentLoanPlanConfig).order_by(StudentLoanPlanConfig.id).all()
    return [{"id": p.id, "plan_name": p.plan_name} for p in plans]
