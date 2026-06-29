"""
Student loan payoff / write-off projection.
Pure function — no database access. Fully unit-testable with plain values.
"""
from dataclasses import dataclass
from datetime import date


@dataclass
class LoanProjectionResult:
    outcome: str               # "paid_off" | "written_off"
    first_repay_date: date
    write_off_date: date
    payoff_date: date | None   # set when outcome == "paid_off"
    remaining_balance_at_writeoff: float  # 0 when paid_off
    years_simulated: float
    annual_salary_assumption: float


def _add_months(d: date, n: int) -> date:
    """Add n calendar months to a date, handling year rollover."""
    month_0 = d.month - 1 + n
    return d.replace(year=d.year + month_0 // 12, month=month_0 % 12 + 1)


def calculate_loan_projection(
    balance: float,
    interest_rate: float,            # annual percentage, e.g. 7.3 means 7.3%
    graduation_year: int,
    plan_threshold: float,           # annual repayment threshold in GBP
    plan_repayment_rate_pct: float,  # e.g. 9.0
    plan_write_off_years: int,
    annual_salary: float,
) -> LoanProjectionResult:
    """
    Simulate month-by-month student loan balance from April 6 the year after graduation.

    Each month:
      1. Apply monthly interest (interest_rate / 12) to the balance.
      2. Subtract the month's repayment: max(0, salary - threshold) * rate / 12.
      3. If balance <= 0: loan is paid off.
      4. If 'plan_write_off_years' * 12 months elapse: loan is written off.

    Returns a LoanProjectionResult describing the outcome, key dates, and remaining
    balance at write-off (if applicable).
    """
    first_repay_date = date(graduation_year + 1, 4, 6)
    write_off_date = first_repay_date.replace(year=first_repay_date.year + plan_write_off_years)

    monthly_interest_rate = interest_rate / 100 / 12
    monthly_repayment = max(0.0, (annual_salary - plan_threshold) * plan_repayment_rate_pct / 100 / 12)

    current_balance = float(balance)
    max_months = plan_write_off_years * 12

    for month in range(1, max_months + 1):
        current_balance += current_balance * monthly_interest_rate
        current_balance -= monthly_repayment

        if current_balance <= 0:
            return LoanProjectionResult(
                outcome="paid_off",
                first_repay_date=first_repay_date,
                write_off_date=write_off_date,
                payoff_date=_add_months(first_repay_date, month),
                remaining_balance_at_writeoff=0.0,
                years_simulated=round(month / 12, 1),
                annual_salary_assumption=annual_salary,
            )

    return LoanProjectionResult(
        outcome="written_off",
        first_repay_date=first_repay_date,
        write_off_date=write_off_date,
        payoff_date=None,
        remaining_balance_at_writeoff=round(current_balance, 2),
        years_simulated=float(plan_write_off_years),
        annual_salary_assumption=annual_salary,
    )
