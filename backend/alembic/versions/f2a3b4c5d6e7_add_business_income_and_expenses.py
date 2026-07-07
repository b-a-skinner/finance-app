"""add business_income and business_expenses tables

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-07-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'f2a3b4c5d6e7'
down_revision = 'e1f2a3b4c5d6'
branch_labels = None
depends_on = None

_EXPENSE_CATEGORIES = ('equipment', 'software', 'travel', 'office', 'professional_fees', 'training', 'marketing', 'other')


def upgrade() -> None:
    op.create_table(
        'business_income',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('date_received', sa.Date(), nullable=False),
        sa.Column('description', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        'business_expenses',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('date_incurred', sa.Date(), nullable=False),
        sa.Column('category', sa.Enum(*_EXPENSE_CATEGORIES, name='businessexpensecategory'), nullable=False),
        sa.Column('description', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('business_expenses')
    op.drop_table('business_income')
