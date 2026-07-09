# Importing all models here ensures they are registered with Base.metadata
# before Alembic or any other code that depends on it runs.
from app.models.config import AgeBenchmarkPension, AgeBenchmarkSalary, BusinessTaxConfig, OccupationCode, OccupationSalaryBenchmark, RegionalSalaryBenchmark, StudentLoanPlanConfig, TaxYearConfig
from app.models.finance import Asset, AssetType, BusinessExpense, BusinessExpenseCategory, BusinessIncome, Debt, Expense, FinancialSnapshot, IncomeSource, PayFrequency, PensionPot, SavingsGoal
from app.models.user import User

__all__ = [
    "User",
    "TaxYearConfig",
    "BusinessTaxConfig",
    "StudentLoanPlanConfig",
    "AgeBenchmarkSalary",
    "AgeBenchmarkPension",
    "OccupationCode",
    "OccupationSalaryBenchmark",
    "RegionalSalaryBenchmark",
    "FinancialSnapshot",
    "BusinessIncome",
    "BusinessExpense",
    "BusinessExpenseCategory",
    "IncomeSource",
    "Expense",
    "Debt",
    "SavingsGoal",
    "PensionPot",
    "Asset",
    "AssetType",
    "PayFrequency",
]
