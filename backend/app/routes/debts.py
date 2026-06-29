from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Debt, IncomeSource
from app.models.config import StudentLoanPlanConfig
from app.models.user import User
from app.routes.auth import get_current_user
from app.schemas import DebtCreate, DebtOut, DebtUpdate, LoanProjectionOut
from app.services.student_loan_projection import calculate_loan_projection
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


@router.get("/{item_id}/projection", response_model=LoanProjectionOut)
def get_debt_projection(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    debt = get_owned_or_404(db, Debt, item_id, current_user.id)

    if debt.debt_type != "student_loan":
        raise HTTPException(status_code=400, detail="Projection is only available for student loan debts.")
    if not debt.graduation_year:
        raise HTTPException(status_code=400, detail="graduation_year is required to calculate a projection.")
    if not debt.student_loan_plan_id:
        raise HTTPException(status_code=400, detail="student_loan_plan_id is required to calculate a projection.")

    plan = db.get(StudentLoanPlanConfig, debt.student_loan_plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Student loan plan not found.")
    if not plan.write_off_years:
        raise HTTPException(status_code=400, detail="write_off_years not configured for this plan.")

    annual_salary = sum(
        s.gross_annual_salary
        for s in db.query(IncomeSource).filter_by(user_id=current_user.id, is_active=True).all()
    )

    result = calculate_loan_projection(
        balance=debt.balance,
        interest_rate=debt.interest_rate,
        graduation_year=debt.graduation_year,
        plan_threshold=plan.threshold,
        plan_repayment_rate_pct=plan.repayment_rate_pct,
        plan_write_off_years=plan.write_off_years,
        annual_salary=annual_salary,
    )
    return result
