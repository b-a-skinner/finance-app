"""Add invoicing: contacts, invoices, invoice_line_items, business profile
fields on users, and invoice_id link on business_income.

Revision ID: r4m5n6o7p8q9
Revises: q3l4m5n6o7p8
Create Date: 2026-07-28
"""
from alembic import op
import sqlalchemy as sa

revision = 'r4m5n6o7p8q9'
down_revision = 'q3l4m5n6o7p8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('business_name', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('business_address', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('bank_account_name', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('bank_sort_code', sa.String(length=20), nullable=True))
    op.add_column('users', sa.Column('bank_account_number', sa.String(length=20), nullable=True))
    op.add_column('users', sa.Column('vat_registered', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('users', sa.Column('vat_number', sa.String(length=50), nullable=True))

    op.create_table(
        'contacts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_contacts_user_id', 'contacts', ['user_id'])

    op.create_table(
        'invoices',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('contact_id', sa.Integer(), sa.ForeignKey('contacts.id'), nullable=False),
        sa.Column('invoice_number', sa.String(length=20), nullable=False),
        sa.Column('issue_date', sa.Date(), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='draft'),
        sa.Column('paid_date', sa.Date(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('vat_registered', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_invoices_user_id', 'invoices', ['user_id'])
    op.create_index('ix_invoices_contact_id', 'invoices', ['contact_id'])

    op.create_table(
        'invoice_line_items',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('invoice_id', sa.Integer(), sa.ForeignKey('invoices.id'), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('unit_price', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_invoice_line_items_invoice_id', 'invoice_line_items', ['invoice_id'])

    # SQLite can't ALTER a column onto an existing table with an inline FK
    # constraint (no support for altering constraints outside batch mode);
    # batch mode works on both SQLite (copy-and-move) and Postgres (plain ALTER).
    with op.batch_alter_table('business_income') as batch_op:
        batch_op.add_column(sa.Column('invoice_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_business_income_invoice_id', 'invoices', ['invoice_id'], ['id'])
        batch_op.create_index('ix_business_income_invoice_id', ['invoice_id'])


def downgrade() -> None:
    with op.batch_alter_table('business_income') as batch_op:
        batch_op.drop_index('ix_business_income_invoice_id')
        batch_op.drop_constraint('fk_business_income_invoice_id', type_='foreignkey')
        batch_op.drop_column('invoice_id')

    op.drop_index('ix_invoice_line_items_invoice_id', table_name='invoice_line_items')
    op.drop_table('invoice_line_items')

    op.drop_index('ix_invoices_contact_id', table_name='invoices')
    op.drop_index('ix_invoices_user_id', table_name='invoices')
    op.drop_table('invoices')

    op.drop_index('ix_contacts_user_id', table_name='contacts')
    op.drop_table('contacts')

    op.drop_column('users', 'vat_number')
    op.drop_column('users', 'vat_registered')
    op.drop_column('users', 'bank_account_number')
    op.drop_column('users', 'bank_sort_code')
    op.drop_column('users', 'bank_account_name')
    op.drop_column('users', 'business_address')
    op.drop_column('users', 'business_name')
