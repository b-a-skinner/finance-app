"""add_occupation_salary_benchmark

Revision ID: d9e1f2a3b4c5
Revises: a1b2c3d4e5f6
Create Date: 2026-07-06 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd9e1f2a3b4c5'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('occupation_salary_benchmark',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('soc_code', sa.String(length=10), nullable=False),
        sa.Column('soc_level', sa.Integer(), nullable=False),
        sa.Column('soc_group_description', sa.String(length=255), nullable=False),
        sa.Column('median_annual_salary', sa.Float(), nullable=False),
        sa.Column('source', sa.String(length=255), nullable=False),
        sa.Column('source_notes', sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    _SRC = "ONS ASHE, April 2025, released October 2025"
    _NOTES = "all employees, median annual gross pay"
    t = sa.table('occupation_salary_benchmark',
                 sa.column('soc_code', sa.String),
                 sa.column('soc_level', sa.Integer),
                 sa.column('soc_group_description', sa.String),
                 sa.column('median_annual_salary', sa.Float),
                 sa.column('source', sa.String),
                 sa.column('source_notes', sa.String))

    # ── soc_level=2: 2-digit sub-major groups ───────────────────────────────
    op.bulk_insert(t, [
        {'soc_code': '11', 'soc_level': 2, 'soc_group_description': 'Corporate managers and directors',            'median_annual_salary': 57745, 'source': _SRC, 'source_notes': _NOTES},
        {'soc_code': '12', 'soc_level': 2, 'soc_group_description': 'Other managers and proprietors',              'median_annual_salary': 38949, 'source': _SRC, 'source_notes': _NOTES},
        {'soc_code': '21', 'soc_level': 2, 'soc_group_description': 'Science, research, engineering and technology professionals', 'median_annual_salary': 51148, 'source': _SRC, 'source_notes': _NOTES},
        {'soc_code': '22', 'soc_level': 2, 'soc_group_description': 'Health professionals',                        'median_annual_salary': 40294, 'source': _SRC, 'source_notes': _NOTES},
        {'soc_code': '23', 'soc_level': 2, 'soc_group_description': 'Teaching and educational professionals',      'median_annual_salary': 43119, 'source': _SRC, 'source_notes': _NOTES},
        {'soc_code': '24', 'soc_level': 2, 'soc_group_description': 'Business, media and public service professionals', 'median_annual_salary': 46925, 'source': _SRC, 'source_notes': _NOTES},
        {'soc_code': '31', 'soc_level': 2, 'soc_group_description': 'Science, engineering and technology associate professionals', 'median_annual_salary': 34828, 'source': _SRC, 'source_notes': _NOTES},
        {'soc_code': '32', 'soc_level': 2, 'soc_group_description': 'Health and social care associate professionals', 'median_annual_salary': 25813, 'source': _SRC, 'source_notes': _NOTES},
        {'soc_code': '34', 'soc_level': 2, 'soc_group_description': 'Culture, media and sports occupations',       'median_annual_salary': 28102, 'source': _SRC, 'source_notes': _NOTES},
        {'soc_code': '35', 'soc_level': 2, 'soc_group_description': 'Business and public service associate professionals', 'median_annual_salary': 38760, 'source': _SRC, 'source_notes': _NOTES},
        {'soc_code': '41', 'soc_level': 2, 'soc_group_description': 'Administrative occupations',                  'median_annual_salary': 27006, 'source': _SRC, 'source_notes': _NOTES},
        {'soc_code': '42', 'soc_level': 2, 'soc_group_description': 'Secretarial and related occupations',         'median_annual_salary': 21061, 'source': _SRC, 'source_notes': _NOTES},
        {'soc_code': '51', 'soc_level': 2, 'soc_group_description': 'Skilled agricultural and related trades',     'median_annual_salary': 27550, 'source': _SRC, 'source_notes': _NOTES},
        {'soc_code': '52', 'soc_level': 2, 'soc_group_description': 'Skilled metal, electrical and electronic trades', 'median_annual_salary': 39155, 'source': _SRC, 'source_notes': _NOTES},
        {'soc_code': '53', 'soc_level': 2, 'soc_group_description': 'Skilled construction and building trades',    'median_annual_salary': 34928, 'source': _SRC, 'source_notes': _NOTES},
        {'soc_code': '54', 'soc_level': 2, 'soc_group_description': 'Textiles, printing and other skilled trades', 'median_annual_salary': 26063, 'source': _SRC, 'source_notes': _NOTES},
        {'soc_code': '61', 'soc_level': 2, 'soc_group_description': 'Caring personal service occupations',         'median_annual_salary': 21082, 'source': _SRC, 'source_notes': _NOTES},
        {'soc_code': '62', 'soc_level': 2, 'soc_group_description': 'Leisure, travel and related personal service occupations', 'median_annual_salary': 22297, 'source': _SRC, 'source_notes': _NOTES},
        {'soc_code': '63', 'soc_level': 2, 'soc_group_description': 'Customer service occupations',                'median_annual_salary': 31050, 'source': _SRC, 'source_notes': _NOTES},
        {'soc_code': '71', 'soc_level': 2, 'soc_group_description': 'Sales occupations',                           'median_annual_salary': 15975, 'source': _SRC, 'source_notes': _NOTES},
        {'soc_code': '72', 'soc_level': 2, 'soc_group_description': 'Customer service occupations',                'median_annual_salary': 25127, 'source': _SRC, 'source_notes': _NOTES},
        {'soc_code': '81', 'soc_level': 2, 'soc_group_description': 'Process, plant and machine operatives',       'median_annual_salary': 29940, 'source': _SRC, 'source_notes': _NOTES},
        {'soc_code': '82', 'soc_level': 2, 'soc_group_description': 'Transport and mobile machine drivers and operatives', 'median_annual_salary': 33960, 'source': _SRC, 'source_notes': _NOTES},
        {'soc_code': '91', 'soc_level': 2, 'soc_group_description': 'Elementary trades and related occupations',   'median_annual_salary': 26716, 'source': _SRC, 'source_notes': _NOTES},
        {'soc_code': '92', 'soc_level': 2, 'soc_group_description': 'Elementary administration and service occupations', 'median_annual_salary': 17287, 'source': _SRC, 'source_notes': _NOTES},
    ])

    # ── soc_level=1: 1-digit major groups (fallback) ─────────────────────────
    op.bulk_insert(t, [
        {'soc_code': '1', 'soc_level': 1, 'soc_group_description': 'Managers, directors and senior officials', 'median_annual_salary': 51733, 'source': _SRC, 'source_notes': _NOTES},
        {'soc_code': '2', 'soc_level': 1, 'soc_group_description': 'Professional occupations',                 'median_annual_salary': 45254, 'source': _SRC, 'source_notes': _NOTES},
        {'soc_code': '3', 'soc_level': 1, 'soc_group_description': 'Associate professional and technical occupations', 'median_annual_salary': 35000, 'source': _SRC, 'source_notes': _NOTES},
        {'soc_code': '4', 'soc_level': 1, 'soc_group_description': 'Administrative and secretarial occupations', 'median_annual_salary': 26154, 'source': _SRC, 'source_notes': _NOTES},
        {'soc_code': '5', 'soc_level': 1, 'soc_group_description': 'Skilled trades occupations',               'median_annual_salary': 34241, 'source': _SRC, 'source_notes': _NOTES},
        {'soc_code': '6', 'soc_level': 1, 'soc_group_description': 'Caring, leisure and other service occupations', 'median_annual_salary': 21331, 'source': _SRC, 'source_notes': _NOTES},
        {'soc_code': '7', 'soc_level': 1, 'soc_group_description': 'Sales and customer service occupations',   'median_annual_salary': 18001, 'source': _SRC, 'source_notes': _NOTES},
        {'soc_code': '8', 'soc_level': 1, 'soc_group_description': 'Process, plant and machine operatives',    'median_annual_salary': 31830, 'source': _SRC, 'source_notes': _NOTES},
        {'soc_code': '9', 'soc_level': 1, 'soc_group_description': 'Elementary occupations',                   'median_annual_salary': 19087, 'source': _SRC, 'source_notes': _NOTES},
    ])


def downgrade() -> None:
    op.drop_table('occupation_salary_benchmark')
