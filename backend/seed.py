"""
Populate reference data tables with UK 2026/27 figures.
Run once after `alembic upgrade head`:
    python seed.py        (from backend/ with .venv active)
"""
from app.database import SessionLocal
from app.models import StudentLoanPlanConfig, TaxYearConfig


def seed() -> None:
    db = SessionLocal()
    try:
        if db.query(TaxYearConfig).filter_by(tax_year="2026/27").first():
            print("Reference data already seeded — skipping.")
            return

        db.add(TaxYearConfig(
            tax_year="2026/27",
            # Income tax
            personal_allowance=12570,
            basic_rate_threshold=50270,
            basic_rate_pct=20,
            higher_rate_threshold=125140,
            higher_rate_pct=40,
            additional_rate_pct=45,
            # National Insurance (weekly thresholds × 52)
            ni_primary_threshold=12584,   # £242/week
            ni_upper_threshold=50284,     # £967/week
            ni_main_rate_pct=8,
            ni_upper_rate_pct=2,
            # Auto-enrolment pension qualifying earnings
            pension_qualifying_lower=6240,
            pension_qualifying_upper=50270,
            pension_min_total_pct=8,
            pension_min_employer_pct=3,
        ))

        db.add_all([
            StudentLoanPlanConfig(plan_name="Plan 1",       tax_year="2026/27", threshold=26900, repayment_rate_pct=9),
            StudentLoanPlanConfig(plan_name="Plan 2",       tax_year="2026/27", threshold=29385, repayment_rate_pct=9),
            StudentLoanPlanConfig(plan_name="Plan 4",       tax_year="2026/27", threshold=33795, repayment_rate_pct=9),
            StudentLoanPlanConfig(plan_name="Plan 5",       tax_year="2026/27", threshold=25000, repayment_rate_pct=9),
            StudentLoanPlanConfig(plan_name="Postgraduate", tax_year="2026/27", threshold=21000, repayment_rate_pct=6),
        ])

        db.commit()
        print("Seeded TaxYearConfig and 5 StudentLoanPlanConfig rows for 2026/27.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
