"""add_first_name_and_occupation_codes

Revision ID: b3f2d1c9a4e0
Revises: 084efd8df333
Create Date: 2026-07-02 22:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'b3f2d1c9a4e0'
down_revision: Union[str, None] = '084efd8df333'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OCCUPATIONS = [
    # (title, soc_code, soc_group)
    # Technology & Engineering
    ('Civil Engineer',           '2121', 'Technology & Engineering'),
    ('Mechanical Engineer',      '2122', 'Technology & Engineering'),
    ('Electrical Engineer',      '2123', 'Technology & Engineering'),
    ('IT Manager',               '2133', 'Technology & Engineering'),
    ('Product Manager',          '2135', 'Technology & Engineering'),
    ('Software Engineer',        '2136', 'Technology & Engineering'),
    ('DevOps Engineer',          '2136', 'Technology & Engineering'),
    ('Data Analyst',             '2137', 'Technology & Engineering'),
    ('Data Scientist',           '2137', 'Technology & Engineering'),
    ('Network Engineer',         '2138', 'Technology & Engineering'),
    ('Cybersecurity Analyst',    '2139', 'Technology & Engineering'),
    ('UX/UI Designer',           '2166', 'Technology & Engineering'),
    # Finance & Accounting
    ('Accountant',               '2421', 'Finance & Accounting'),
    ('Auditor',                  '2421', 'Finance & Accounting'),
    ('Financial Analyst',        '2422', 'Finance & Accounting'),
    ('Investment Banker',        '2422', 'Finance & Accounting'),
    ('Financial Adviser',        '2423', 'Finance & Accounting'),
    ('Mortgage Adviser',         '2423', 'Finance & Accounting'),
    ('Actuary',                  '2424', 'Finance & Accounting'),
    ('Tax Adviser',              '2429', 'Finance & Accounting'),
    ('Bookkeeper',               '4122', 'Finance & Accounting'),
    # Healthcare & Medicine
    ('Doctor (GP)',              '2211', 'Healthcare & Medicine'),
    ('Hospital Doctor',          '2212', 'Healthcare & Medicine'),
    ('Surgeon',                  '2212', 'Healthcare & Medicine'),
    ('Pharmacist',               '2213', 'Healthcare & Medicine'),
    ('Dentist',                  '2214', 'Healthcare & Medicine'),
    ('Optometrist',              '2215', 'Healthcare & Medicine'),
    ('Physiotherapist',          '2221', 'Healthcare & Medicine'),
    ('Nurse',                    '2231', 'Healthcare & Medicine'),
    ('Mental Health Nurse',      '2232', 'Healthcare & Medicine'),
    ('Midwife',                  '2236', 'Healthcare & Medicine'),
    ('Radiographer',             '2229', 'Healthcare & Medicine'),
    ('Paramedic',                '3213', 'Healthcare & Medicine'),
    # Education
    ('University Lecturer',              '2311', 'Education'),
    ('Primary School Teacher',           '2314', 'Education'),
    ('Secondary School Teacher',         '2315', 'Education'),
    ('Special Educational Needs Teacher','2316', 'Education'),
    ('Tutor',                            '2319', 'Education'),
    ('Headteacher',                      '1184', 'Education'),
    ('Early Years Practitioner',         '6121', 'Education'),
    ('Teaching Assistant',               '6126', 'Education'),
    # Legal
    ('Barrister',                '2411', 'Legal'),
    ('Judge',                    '2412', 'Legal'),
    ('Solicitor',                '2413', 'Legal'),
    ('Paralegal',                '2419', 'Legal'),
    ('Legal Executive',          '2419', 'Legal'),
    ('Legal Secretary',          '4215', 'Legal'),
    # Sales & Marketing
    ('Marketing Manager',              '1132', 'Sales & Marketing'),
    ('Brand Manager',                  '1132', 'Sales & Marketing'),
    ('PR Manager',                     '1134', 'Sales & Marketing'),
    ('Sales Manager',                  '1135', 'Sales & Marketing'),
    ('Digital Marketing Executive',    '3543', 'Sales & Marketing'),
    ('SEO Specialist',                 '3543', 'Sales & Marketing'),
    ('Content Creator',                '3417', 'Sales & Marketing'),
    ('Account Manager',                '3545', 'Sales & Marketing'),
    ('Business Development Manager',   '3545', 'Sales & Marketing'),
    # Creative & Media
    ('Architect',                '2431', 'Creative & Media'),
    ('Musician',                 '3411', 'Creative & Media'),
    ('Actor',                    '3411', 'Creative & Media'),
    ('Journalist',               '3412', 'Creative & Media'),
    ('Copywriter',               '3412', 'Creative & Media'),
    ('Film/TV Producer',         '3416', 'Creative & Media'),
    ('Graphic Designer',         '3421', 'Creative & Media'),
    ('Interior Designer',        '3422', 'Creative & Media'),
    ('Photographer',             '3431', 'Creative & Media'),
    ('Videographer',             '3432', 'Creative & Media'),
    # Trades & Construction
    ('Quantity Surveyor',        '2432', 'Trades & Construction'),
    ('Welder',                   '5211', 'Trades & Construction'),
    ('Carpenter',                '5215', 'Trades & Construction'),
    ('Plumber',                  '5232', 'Trades & Construction'),
    ('Electrician',              '5241', 'Trades & Construction'),
    ('HVAC Engineer',            '5244', 'Trades & Construction'),
    ('Bricklayer',               '5312', 'Trades & Construction'),
    ('Roofer',                   '5316', 'Trades & Construction'),
    ('Plasterer',                '5319', 'Trades & Construction'),
    ('Painter & Decorator',      '5329', 'Trades & Construction'),
    # Hospitality & Retail
    ('Hotel Manager',            '1223', 'Hospitality & Retail'),
    ('Restaurant Manager',       '1224', 'Hospitality & Retail'),
    ('Retail Manager',           '1142', 'Hospitality & Retail'),
    ('Event Planner',            '3456', 'Hospitality & Retail'),
    ('Chef',                     '5434', 'Hospitality & Retail'),
    ('Bartender',                '9271', 'Hospitality & Retail'),
    ('Barista',                  '9272', 'Hospitality & Retail'),
    # Public Sector & Civil Service
    ('Armed Forces Officer',          '1171', 'Public Sector & Civil Service'),
    ('Headteacher',                   '1184', 'Public Sector & Civil Service'),
    ('Firefighter',                   '3311', 'Public Sector & Civil Service'),
    ('Police Officer',                '3312', 'Public Sector & Civil Service'),
    ('Civil Servant',                 '4132', 'Public Sector & Civil Service'),
    ('Social Worker',                 '2442', 'Public Sector & Civil Service'),
    ('Probation Officer',             '2443', 'Public Sector & Civil Service'),
    ('Town Planner',                  '2433', 'Public Sector & Civil Service'),
    ('Environmental Health Officer',  '2463', 'Public Sector & Civil Service'),
    # Other
    ('Self-employed / Freelancer', '0000', 'Other'),
    ('Student',                    '0001', 'Other'),
    ('Retired',                    '0002', 'Other'),
    ('Prefer not to say',          '0003', 'Other'),
    ('Business Owner',             '1190', 'Other'),
    ('Carer',                      '6145', 'Other'),
]


def upgrade() -> None:
    op.add_column('users', sa.Column('first_name', sa.String(100), nullable=True))

    op.create_table(
        'occupation_codes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('soc_code', sa.String(10), nullable=False),
        sa.Column('soc_group', sa.String(100), nullable=False),
    )

    occupation_codes = sa.table(
        'occupation_codes',
        sa.column('title', sa.String),
        sa.column('soc_code', sa.String),
        sa.column('soc_group', sa.String),
    )
    op.bulk_insert(occupation_codes, [
        {'title': t, 'soc_code': s, 'soc_group': g}
        for t, s, g in _OCCUPATIONS
    ])


def downgrade() -> None:
    op.drop_table('occupation_codes')
    op.drop_column('users', 'first_name')
