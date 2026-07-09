"""
Populate reference data tables with UK 2026/27 figures.
Run once after `alembic upgrade head`:
    python seed.py        (from backend/ with .venv active)
"""
from app.database import SessionLocal
from app.models import AgeBenchmarkPension, AgeBenchmarkSalary, RegionalSalaryBenchmark, StudentLoanPlanConfig, TaxYearConfig
from app.models.config import BusinessTaxConfig


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
            StudentLoanPlanConfig(plan_name="Plan 1",       tax_year="2026/27", threshold=26900, repayment_rate_pct=9, write_off_years=25),
            StudentLoanPlanConfig(plan_name="Plan 2",       tax_year="2026/27", threshold=29385, repayment_rate_pct=9, write_off_years=30),
            StudentLoanPlanConfig(plan_name="Plan 4",       tax_year="2026/27", threshold=33795, repayment_rate_pct=9, write_off_years=30),
            StudentLoanPlanConfig(plan_name="Plan 5",       tax_year="2026/27", threshold=25000, repayment_rate_pct=9, write_off_years=40),
            StudentLoanPlanConfig(plan_name="Postgraduate", tax_year="2026/27", threshold=21000, repayment_rate_pct=6, write_off_years=30),
        ])

        db.commit()
        print("Seeded TaxYearConfig and 5 StudentLoanPlanConfig rows for 2026/27.")

        # Seed age benchmarks (idempotent: skip if already present)
        if not db.query(AgeBenchmarkSalary).first():
            _SAL = "ONS, May 2026"
            _SAL_M = "all employees, median monthly pay before tax"
            db.add_all([
                AgeBenchmarkSalary(age_band="18-24", min_age=18, max_age=24,  median_monthly_salary=1830, source=_SAL, source_metric=_SAL_M),
                AgeBenchmarkSalary(age_band="25-34", min_age=25, max_age=34,  median_monthly_salary=2820, source=_SAL, source_metric=_SAL_M),
                AgeBenchmarkSalary(age_band="35-49", min_age=35, max_age=49,  median_monthly_salary=3062, source=_SAL, source_metric=_SAL_M),
                AgeBenchmarkSalary(age_band="50-64", min_age=50, max_age=64,  median_monthly_salary=2698, source=_SAL, source_metric=_SAL_M),
                AgeBenchmarkSalary(age_band="65+",   min_age=65, max_age=None, median_monthly_salary=1582, source=_SAL, source_metric=_SAL_M),
            ])
            _PEN = "ONS Wealth and Assets Survey"
            _PEN_M = "median pension wealth, individual"
            db.add_all([
                AgeBenchmarkPension(age_band="Under 25", min_age=0,  max_age=24, median_pension_pot=5500,   source=_PEN, source_metric=_PEN_M),
                AgeBenchmarkPension(age_band="25-34",    min_age=25, max_age=34, median_pension_pot=18800,  source=_PEN, source_metric=_PEN_M),
                AgeBenchmarkPension(age_band="35-44",    min_age=35, max_age=44, median_pension_pot=39500,  source=_PEN, source_metric=_PEN_M),
                AgeBenchmarkPension(age_band="45-54",    min_age=45, max_age=54, median_pension_pot=None,   source=_PEN, source_metric=_PEN_M),
                AgeBenchmarkPension(age_band="55-64",    min_age=55, max_age=64, median_pension_pot=None,   source=_PEN, source_metric=_PEN_M),
                AgeBenchmarkPension(age_band="65-74",    min_age=65, max_age=74, median_pension_pot=145900, source=_PEN, source_metric=_PEN_M),
            ])
            db.commit()
            print("Seeded age benchmark tables.")

        if not db.query(BusinessTaxConfig).filter_by(tax_year="2026/27").first():
            db.add(BusinessTaxConfig(
                tax_year="2026/27",
                # Home office flat rates — £/month (HMRC simplified expenses)
                home_office_band_25_50=10.0,
                home_office_band_51_100=18.0,
                home_office_band_101_plus=26.0,
                # Mileage rates — increased from 45p to 55p for 2026/27 (HMRC April 2026)
                mileage_car_van_first=0.55,
                mileage_car_van_over=0.25,
                mileage_motorcycle=0.24,
                mileage_bicycle=0.20,
                mileage_threshold=10000,
                source_note="HMRC simplified expenses, 2026/27. Mileage rate increased from 45p to 55p from 6 April 2026.",
            ))
            db.commit()
            print("Seeded BusinessTaxConfig for 2026/27.")

        if not db.query(RegionalSalaryBenchmark).first():
            _R = "ONS ASHE, April 2025, released October 2025"
            _RN = "all employees except London which is full-time only — see note"
            db.add_all([
                RegionalSalaryBenchmark(region_name="London",                   median_annual_salary=49692, source=_R, source_notes=_RN),
                RegionalSalaryBenchmark(region_name="South East",               median_annual_salary=35215, source=_R, source_notes=_RN),
                RegionalSalaryBenchmark(region_name="East of England",          median_annual_salary=34104, source=_R, source_notes=_RN),
                RegionalSalaryBenchmark(region_name="Scotland",                 median_annual_salary=33061, source=_R, source_notes=_RN),
                RegionalSalaryBenchmark(region_name="South West",               median_annual_salary=31432, source=_R, source_notes=_RN),
                RegionalSalaryBenchmark(region_name="West Midlands",            median_annual_salary=31345, source=_R, source_notes=_RN),
                RegionalSalaryBenchmark(region_name="North West",               median_annual_salary=31330, source=_R, source_notes=_RN),
                RegionalSalaryBenchmark(region_name="Northern Ireland",         median_annual_salary=31232, source=_R, source_notes=_RN),
                RegionalSalaryBenchmark(region_name="Wales",                    median_annual_salary=30732, source=_R, source_notes=_RN),
                RegionalSalaryBenchmark(region_name="East Midlands",            median_annual_salary=30690, source=_R, source_notes=_RN),
                RegionalSalaryBenchmark(region_name="Yorkshire and the Humber", median_annual_salary=30682, source=_R, source_notes=_RN),
                RegionalSalaryBenchmark(region_name="North East",               median_annual_salary=29584, source=_R, source_notes=_RN),
                RegionalSalaryBenchmark(region_name="UK overall",               median_annual_salary=32890, source=_R, source_notes=_RN),
            ])
            db.commit()
            print("Seeded regional salary benchmark table.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
