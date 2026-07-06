# Importing all models here ensures they are registered with Base.metadata
# before Alembic or any other code that depends on it runs.
from app.models.config import AgeBenchmarkPension, AgeBenchmarkSalary, OccupationCode, OccupationSalaryBenchmark, RegionalSalaryBenchmark, StudentLoanPlanConfig, TaxYearConfig
from app.models.finance import Asset, AssetType, Debt, Expense, FinancialSnapshot, IncomeSource, PayFrequency, PensionPot, SavingsGoal
from app.models.user import User

__all__ = [
    "User",
    "TaxYearConfig",
    "StudentLoanPlanConfig",
    "AgeBenchmarkSalary",
    "AgeBenchmarkPension",
    "OccupationCode",
    "OccupationSalaryBenchmark",
    "RegionalSalaryBenchmark",
    "FinancialSnapshot",
    "IncomeSource",
    "Expense",
    "Debt",
    "SavingsGoal",
    "PensionPot",
    "Asset",
    "AssetType",
    "PayFrequency",
]
