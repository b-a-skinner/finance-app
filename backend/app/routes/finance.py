from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/finance", tags=["finance"])


class FinancialSummary(BaseModel):
    salary: float
    expenses: float
    savings: float
    debt: float
    pension_contribution: float


@router.get("/summary", response_model=FinancialSummary)
def get_summary():
    # Placeholder — replace with real data layer
    return FinancialSummary(
        salary=0.0,
        expenses=0.0,
        savings=0.0,
        debt=0.0,
        pension_contribution=0.0,
    )
