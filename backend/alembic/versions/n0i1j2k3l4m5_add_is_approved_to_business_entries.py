"""Add is_approved to business income and expense entries.

All existing rows get server_default=false (unapproved). We then backfill
past-dated and today-dated entries to true so they continue to appear in
analytics unchanged. Future-dated entries stay false — they become "scheduled".
"""
from datetime import date as _date

from alembic import op
import sqlalchemy as sa

revision = 'n0i1j2k3l4m5'
down_revision = 'm9h0i1j2k3l4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'business_income',
        sa.Column('is_approved', sa.Boolean(), nullable=False, server_default=sa.text('false')),
    )
    op.add_column(
        'business_expenses',
        sa.Column('is_approved', sa.Boolean(), nullable=False, server_default=sa.text('false')),
    )

    # Existing past/today entries have already happened — approve them.
    # Future-dated entries remain false (scheduled).
    today = _date.today().isoformat()
    op.execute(sa.text(
        f"UPDATE business_income SET is_approved = true"
        f" WHERE date_received <= '{today}' AND is_active = true"
    ))
    op.execute(sa.text(
        f"UPDATE business_expenses SET is_approved = true"
        f" WHERE date_incurred <= '{today}' AND is_active = true"
    ))


def downgrade() -> None:
    op.drop_column('business_expenses', 'is_approved')
    op.drop_column('business_income', 'is_approved')
