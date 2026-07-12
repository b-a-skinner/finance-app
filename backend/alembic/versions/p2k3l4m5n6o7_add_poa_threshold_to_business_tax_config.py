"""Add poa_threshold field to business_tax_configs.

Revision ID: p2k3l4m5n6o7
Revises: o1j2k3l4m5n6
Create Date: 2026-07-12
"""
from alembic import op
import sqlalchemy as sa

revision = 'p2k3l4m5n6o7'
down_revision = 'o1j2k3l4m5n6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('business_tax_configs', sa.Column('poa_threshold', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('business_tax_configs', 'poa_threshold')
