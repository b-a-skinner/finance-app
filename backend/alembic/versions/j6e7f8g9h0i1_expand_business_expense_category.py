"""expand business_expense category from PostgreSQL enum to VARCHAR

The original migration created the category column as a named PostgreSQL
enum type (businessexpensecategory) with 8 values. Phase 2 added 10 new
categories; those fail on PostgreSQL because the native enum type rejects
values not in its original list. SQLite was unaffected (stored as VARCHAR
with no CHECK constraint).

This migration:
  1. Adds the 10 new values to the PostgreSQL enum type (so existing INSERTs
     that may have been attempted are now valid).
  2. Converts the column to plain VARCHAR(50) so future category additions
     never require a schema migration.
  3. Drops the now-unused enum type.

SQLite has no enum type — nothing to do.

Revision ID: j6e7f8g9h0i1
Revises: i5d6e7f8g9h0
Create Date: 2026-07-08 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'j6e7f8g9h0i1'
down_revision = 'i5d6e7f8g9h0'
branch_labels = None
depends_on = None

_NEW_VALUES = [
    'insurance', 'staff_costs', 'phone_internet', 'pension_employer', 'bank_charges',
    'client_entertainment', 'fines', 'personal', 'political', 'home_office',
]


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == 'postgresql':
        # Step 1: extend the enum so any existing rows (if any) remain valid
        for v in _NEW_VALUES:
            op.execute(f"ALTER TYPE businessexpensecategory ADD VALUE IF NOT EXISTS '{v}'")
        # Step 2: convert column to plain VARCHAR — no more enum constraint
        op.execute(
            "ALTER TABLE business_expenses "
            "ALTER COLUMN category TYPE VARCHAR(50)"
        )
        # Step 3: drop the now-unused enum type
        op.execute("DROP TYPE IF EXISTS businessexpensecategory")
    # SQLite: column is already stored as VARCHAR; nothing to change


def downgrade() -> None:
    # Recreating the named PostgreSQL enum type is complex and lossy
    # (any new-category rows would be invalid after downgrade).
    # Treat this as a one-way migration.
    pass
