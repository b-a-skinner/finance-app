# Importing all models here ensures they are registered with Base.metadata
# before Alembic or any other code that depends on it runs.
from app.models.config import AgeBenchmarkPension, AgeBenchmarkSalary, StudentLoanPlanConfig, TaxYearConfig
from app.models.finance import Asset, AssetType, Debt, Expense, IncomeSource, PayFrequency, PensionPot, SavingsGoal
from app.models.user import User

__all__ = [
    "User",
    "TaxYearConfig",
    "StudentLoanPlanConfig",
    "AgeBenchmarkSalary",
    "AgeBenchmarkPension",
    "IncomeSource",
    "Expense",
    "Debt",
    "SavingsGoal",
    "PensionPot",
    "Asset",
    "AssetType",
    "PayFrequency",
]
