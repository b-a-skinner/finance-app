import json
import os
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi import Header as FastAPIHeader
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Asset, BusinessExpense, BusinessIncome, Debt, Expense, FinancialSnapshot, IncomeSource, PensionPot, SavingsGoal
from app.models.user import User
from app.routes.business import _tax_year_bounds, _years_with_data

router = APIRouter(prefix="/admin", tags=["admin"])

BUSINESS_TYPES = ("sole_trader", "limited_company", "partnership", "llp", "not_sure")


def _require_admin_key(x_admin_key: Optional[str] = FastAPIHeader(None)) -> None:
    admin_key = os.getenv("ADMIN_KEY", "")
    if not admin_key or x_admin_key != admin_key:
        raise HTTPException(status_code=403, detail="Forbidden")


class ProfileComplete(BaseModel):
    income: bool
    expenses: bool
    debts: bool
    savings: bool
    pension: bool
    assets: bool


class BusinessFeatures(BaseModel):
    income: bool        # business income logged
    expenses: bool       # business expenses logged
    mileage: bool         # a mileage-method expense logged
    home_office: bool     # a home-office flat-rate expense logged
    recurring: bool        # any income/expense set to recur
    scheduled: bool         # any future-dated (not-yet-approved) entry


class AdminUserOut(BaseModel):
    id: int
    email: str
    first_name: Optional[str]
    created_at: datetime
    last_active: datetime
    profile_complete: ProfileComplete
    onboarding_completed: bool
    financial_goals: Optional[list]
    business_mode: bool
    business_type: Optional[str]
    business_features: BusinessFeatures


class FeatureAdoption(BaseModel):
    income: float
    expenses: float
    debts: float
    savings: float
    pension: float
    assets: float


class BusinessOverview(BaseModel):
    users_in_business_mode: int
    users_with_business_income: int
    users_with_business_expenses: int
    users_with_completed_tax_year: int   # confirmed data in a tax year whose 5 April has passed


class BusinessTypeBreakdown(BaseModel):
    sole_trader: int
    limited_company: int
    partnership: int
    llp: int
    not_sure: int
    not_set: int   # in business mode but haven't chosen a type


class BusinessFeatureAdoption(BaseModel):
    """Percentage of users IN BUSINESS MODE who have used each feature (denominator = users_in_business_mode)."""
    income: float
    expenses: float
    mileage: float
    home_office: float
    recurring: float
    scheduled: float


class AdminStatsOut(BaseModel):
    total_users: int
    users_active_last_7_days: int
    users_active_last_30_days: int
    users_completed_onboarding: int
    avg_income_sources_per_user: float
    avg_debts_per_user: float
    avg_savings_goals_per_user: float
    users_with_income: int
    users_with_debts: int
    users_with_savings: int
    users_with_pension: int
    users_with_assets: int
    feature_adoption: FeatureAdoption
    business_overview: BusinessOverview
    business_type_breakdown: BusinessTypeBreakdown
    business_feature_adoption: BusinessFeatureAdoption


def _is_business_mode(user: User) -> bool:
    """Ever used business mode — currently active, or a business type was chosen at some point."""
    return user.active_mode == "business" or user.business_type is not None


def _distinct_user_ids(query) -> set[int]:
    return {row[0] for row in query.distinct().all()}


def _business_feature_user_sets(db: Session) -> dict[str, set[int]]:
    """Distinct user IDs who have used each business feature — metadata only, no amounts read."""
    income_users  = _distinct_user_ids(db.query(BusinessIncome.user_id).filter_by(is_active=True))
    expense_users = _distinct_user_ids(db.query(BusinessExpense.user_id).filter_by(is_active=True))
    mileage_users = _distinct_user_ids(
        db.query(BusinessExpense.user_id).filter_by(is_active=True, expense_method="mileage")
    )
    home_office_users = _distinct_user_ids(
        db.query(BusinessExpense.user_id).filter_by(is_active=True, expense_method="home_office_flat")
    )
    recurring_users = _distinct_user_ids(
        db.query(BusinessIncome.user_id).filter(BusinessIncome.is_active == True, BusinessIncome.recurrence_freq.isnot(None))
    ) | _distinct_user_ids(
        db.query(BusinessExpense.user_id).filter(BusinessExpense.is_active == True, BusinessExpense.recurrence_freq.isnot(None))
    )
    scheduled_users = _distinct_user_ids(
        db.query(BusinessIncome.user_id).filter(BusinessIncome.is_active == True, BusinessIncome.is_approved == False)
    ) | _distinct_user_ids(
        db.query(BusinessExpense.user_id).filter(BusinessExpense.is_active == True, BusinessExpense.is_approved == False)
    )
    return {
        "income": income_users,
        "expenses": expense_users,
        "mileage": mileage_users,
        "home_office": home_office_users,
        "recurring": recurring_users,
        "scheduled": scheduled_users,
    }


def _has_completed_tax_year(db: Session, user_id: int) -> bool:
    """Has at least one confirmed entry in a tax year whose 5 April has already passed."""
    years = _years_with_data(db, user_id)
    today = date.today()
    return any(_tax_year_bounds(year)[1] < today for year in years)


@router.get("/users", response_model=list[AdminUserOut])
def list_users(
    db: Session = Depends(get_db),
    _: None = Depends(_require_admin_key),
):
    users = db.query(User).all()
    biz_sets = _business_feature_user_sets(db)
    result = []
    for user in users:
        last_snapshot = (
            db.query(FinancialSnapshot)
            .filter_by(user_id=user.id)
            .order_by(FinancialSnapshot.captured_at.desc())
            .first()
        )
        last_active = last_snapshot.captured_at if last_snapshot else user.created_at

        has_income   = db.query(IncomeSource).filter_by(user_id=user.id, is_active=True).first() is not None
        has_expenses = db.query(Expense).filter_by(user_id=user.id, is_active=True).first() is not None
        has_debts    = db.query(Debt).filter_by(user_id=user.id, is_active=True).first() is not None
        has_savings  = db.query(SavingsGoal).filter_by(user_id=user.id, is_active=True).first() is not None
        has_pension  = db.query(PensionPot).filter_by(user_id=user.id, is_active=True).first() is not None
        has_assets   = db.query(Asset).filter_by(user_id=user.id, is_active=True).first() is not None

        goals = None
        if user.financial_goals:
            try:
                goals = json.loads(user.financial_goals)
            except (json.JSONDecodeError, TypeError):
                goals = None

        result.append(AdminUserOut(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            created_at=user.created_at,
            last_active=last_active,
            profile_complete=ProfileComplete(
                income=has_income,
                expenses=has_expenses,
                debts=has_debts,
                savings=has_savings,
                pension=has_pension,
                assets=has_assets,
            ),
            onboarding_completed=user.onboarding_completed,
            financial_goals=goals,
            business_mode=_is_business_mode(user),
            business_type=user.business_type,
            business_features=BusinessFeatures(
                income=user.id in biz_sets["income"],
                expenses=user.id in biz_sets["expenses"],
                mileage=user.id in biz_sets["mileage"],
                home_office=user.id in biz_sets["home_office"],
                recurring=user.id in biz_sets["recurring"],
                scheduled=user.id in biz_sets["scheduled"],
            ),
        ))
    return result


@router.get("/stats", response_model=AdminStatsOut)
def get_stats(
    db: Session = Depends(get_db),
    _: None = Depends(_require_admin_key),
):
    now = datetime.now(timezone.utc)
    seven_days_ago  = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    total_users = db.query(User).count()

    users_active_7 = (
        db.query(FinancialSnapshot.user_id)
        .filter(FinancialSnapshot.captured_at >= seven_days_ago)
        .distinct()
        .count()
    )
    users_active_30 = (
        db.query(FinancialSnapshot.user_id)
        .filter(FinancialSnapshot.captured_at >= thirty_days_ago)
        .distinct()
        .count()
    )

    users_completed = db.query(User).filter_by(onboarding_completed=True).count()

    users_with_income   = db.query(IncomeSource.user_id).filter_by(is_active=True).distinct().count()
    users_with_expenses = db.query(Expense.user_id).filter_by(is_active=True).distinct().count()
    users_with_debts    = db.query(Debt.user_id).filter_by(is_active=True).distinct().count()
    users_with_savings  = db.query(SavingsGoal.user_id).filter_by(is_active=True).distinct().count()
    users_with_pension  = db.query(PensionPot.user_id).filter_by(is_active=True).distinct().count()
    users_with_assets   = db.query(Asset.user_id).filter_by(is_active=True).distinct().count()

    total_income_rows  = db.query(IncomeSource).filter_by(is_active=True).count()
    total_debt_rows    = db.query(Debt).filter_by(is_active=True).count()
    total_savings_rows = db.query(SavingsGoal).filter_by(is_active=True).count()

    def avg(n: int) -> float:
        return round(n / total_users, 2) if total_users else 0.0

    def pct(n: int) -> float:
        return round((n / total_users) * 100, 1) if total_users else 0.0

    # -- Business overview, type breakdown, and feature adoption --------------
    biz_sets = _business_feature_user_sets(db)
    business_mode_users = [u for u in db.query(User).all() if _is_business_mode(u)]
    business_mode_ids = {u.id for u in business_mode_users}
    users_in_business_mode = len(business_mode_ids)

    users_with_any_business_data = biz_sets["income"] | biz_sets["expenses"]
    users_with_completed_tax_year = sum(
        1 for uid in users_with_any_business_data if _has_completed_tax_year(db, uid)
    )

    type_counts = {t: 0 for t in BUSINESS_TYPES}
    type_counts["not_set"] = 0
    for u in business_mode_users:
        key = u.business_type if u.business_type in BUSINESS_TYPES else "not_set"
        type_counts[key] += 1

    def biz_pct(feature_users: set[int]) -> float:
        n = len(feature_users & business_mode_ids)
        return round((n / users_in_business_mode) * 100, 1) if users_in_business_mode else 0.0

    return AdminStatsOut(
        total_users=total_users,
        users_active_last_7_days=users_active_7,
        users_active_last_30_days=users_active_30,
        users_completed_onboarding=users_completed,
        avg_income_sources_per_user=avg(total_income_rows),
        avg_debts_per_user=avg(total_debt_rows),
        avg_savings_goals_per_user=avg(total_savings_rows),
        users_with_income=users_with_income,
        users_with_debts=users_with_debts,
        users_with_savings=users_with_savings,
        users_with_pension=users_with_pension,
        users_with_assets=users_with_assets,
        feature_adoption=FeatureAdoption(
            income=pct(users_with_income),
            expenses=pct(users_with_expenses),
            debts=pct(users_with_debts),
            savings=pct(users_with_savings),
            pension=pct(users_with_pension),
            assets=pct(users_with_assets),
        ),
        business_overview=BusinessOverview(
            users_in_business_mode=users_in_business_mode,
            users_with_business_income=len(biz_sets["income"]),
            users_with_business_expenses=len(biz_sets["expenses"]),
            users_with_completed_tax_year=users_with_completed_tax_year,
        ),
        business_type_breakdown=BusinessTypeBreakdown(**type_counts),
        business_feature_adoption=BusinessFeatureAdoption(
            income=biz_pct(biz_sets["income"]),
            expenses=biz_pct(biz_sets["expenses"]),
            mileage=biz_pct(biz_sets["mileage"]),
            home_office=biz_pct(biz_sets["home_office"]),
            recurring=biz_pct(biz_sets["recurring"]),
            scheduled=biz_pct(biz_sets["scheduled"]),
        ),
    )


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(_require_admin_key),
):
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.query(IncomeSource).filter_by(user_id=user_id).delete(synchronize_session=False)
    db.query(Expense).filter_by(user_id=user_id).delete(synchronize_session=False)
    db.query(Debt).filter_by(user_id=user_id).delete(synchronize_session=False)
    db.query(SavingsGoal).filter_by(user_id=user_id).delete(synchronize_session=False)
    db.query(PensionPot).filter_by(user_id=user_id).delete(synchronize_session=False)
    db.query(Asset).filter_by(user_id=user_id).delete(synchronize_session=False)
    db.query(FinancialSnapshot).filter_by(user_id=user_id).delete(synchronize_session=False)

    db.delete(user)
    db.commit()
    return {"message": "User deleted"}
