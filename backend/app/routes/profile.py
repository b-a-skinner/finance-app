import dataclasses

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AgeBenchmarkPension, AgeBenchmarkSalary, IncomeSource, OccupationCode, OccupationSalaryBenchmark, PensionPot, RegionalSalaryBenchmark
from app.models.user import User
from app.routes.auth import get_current_user
from app.schemas import AgeComparisonOut, ModeUpdate, OnboardingOut, OnboardingUpdate, OccupationOut, ProfileOut, ProfileUpdate
from app.services.age_benchmark import get_age_comparison, get_occupation_comparison, get_regional_comparison
from app.services.postcode_lookup import get_region_from_postcode

router = APIRouter(prefix="/profile", tags=["profile"])


def _to_out(user: User) -> ProfileOut:
    return ProfileOut(
        first_name=user.first_name,
        date_of_birth=user.date_of_birth,
        occupation=user.occupation,
        postcode_outward=user.postcode_outward,
        region=get_region_from_postcode(user.postcode_outward),
        active_mode=user.active_mode,
        business_type=user.business_type,
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


@router.patch("", response_model=ProfileOut)
def patch_profile(
    body: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return _to_out(current_user)


@router.get("/onboarding", response_model=OnboardingOut)
def get_onboarding(current_user: User = Depends(get_current_user)):
    return OnboardingOut(
        onboarding_completed=current_user.onboarding_completed,
        onboarding_dismiss_count=current_user.onboarding_dismiss_count,
        financial_goals=current_user.financial_goals,
        current_onboarding_step=current_user.current_onboarding_step,
    )


@router.patch("/onboarding", response_model=OnboardingOut)
def update_onboarding(
    body: OnboardingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return OnboardingOut(
        onboarding_completed=current_user.onboarding_completed,
        onboarding_dismiss_count=current_user.onboarding_dismiss_count,
        financial_goals=current_user.financial_goals,
        current_onboarding_step=current_user.current_onboarding_step,
    )


@router.patch("/mode")
def update_mode(
    body: ModeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current_user.active_mode = body.active_mode
    db.commit()
    return {"active_mode": body.active_mode}


@router.get("/comparison", response_model=AgeComparisonOut)
def get_profile_comparison(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    salary_benchmarks = db.query(AgeBenchmarkSalary).order_by(AgeBenchmarkSalary.min_age).all()
    pension_benchmarks = db.query(AgeBenchmarkPension).order_by(AgeBenchmarkPension.min_age).all()
    regional_benchmarks = db.query(RegionalSalaryBenchmark).all()
    occupation_benchmarks = db.query(OccupationSalaryBenchmark).all()

    income_sources = db.query(IncomeSource).filter_by(user_id=current_user.id, is_active=True).all()
    annual_salary = sum(s.gross_annual_salary for s in income_sources)
    monthly_salary = annual_salary / 12

    pension_pot = sum(
        p.current_balance
        for p in db.query(PensionPot).filter_by(user_id=current_user.id, is_active=True).all()
    )

    age_result = get_age_comparison(
        date_of_birth=current_user.date_of_birth,
        current_monthly_salary=monthly_salary,
        current_pension_pot=pension_pot,
        salary_benchmarks=salary_benchmarks,
        pension_benchmarks=pension_benchmarks,
    )
    regional_result = get_regional_comparison(
        postcode_outward=current_user.postcode_outward,
        current_annual_salary=annual_salary,
        regional_benchmarks=regional_benchmarks,
    )
    occ_record = (
        db.query(OccupationCode)
        .filter(OccupationCode.title == current_user.occupation)
        .first()
        if current_user.occupation else None
    )
    occupation_result = get_occupation_comparison(
        soc_code=occ_record.soc_code if occ_record else None,
        current_annual_salary=annual_salary,
        occupation_benchmarks=occupation_benchmarks,
    )

    return AgeComparisonOut(
        **dataclasses.asdict(age_result),
        **dataclasses.asdict(regional_result),
        **dataclasses.asdict(occupation_result),
        current_monthly_salary=monthly_salary,
        current_annual_salary=annual_salary,
        current_pension_pot=pension_pot,
    )
