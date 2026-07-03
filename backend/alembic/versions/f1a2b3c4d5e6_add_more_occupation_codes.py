"""add_more_occupation_codes

Revision ID: f1a2b3c4d5e6
Revises: b3f2d1c9a4e0
Create Date: 2026-07-03 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'b3f2d1c9a4e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NEW_OCCUPATIONS = [
    # (title, soc_code, soc_group)
    # Finance & Accounting
    ('Trader',                  '2422', 'Finance & Accounting'),
    ('Equity Trader',           '2422', 'Finance & Accounting'),
    ('FX Trader',               '2422', 'Finance & Accounting'),
    ('Portfolio Manager',       '2422', 'Finance & Accounting'),
    ('Hedge Fund Manager',      '2422', 'Finance & Accounting'),
    ('Quantitative Analyst',    '2425', 'Finance & Accounting'),
    ('Risk Analyst',            '2422', 'Finance & Accounting'),
    ('Compliance Officer',      '2429', 'Finance & Accounting'),
    ('Fund Manager',            '2422', 'Finance & Accounting'),
    ('Insurance Underwriter',   '3521', 'Finance & Accounting'),
    ('Claims Handler',          '3521', 'Finance & Accounting'),
    ('Pensions Administrator',  '4122', 'Finance & Accounting'),
    ('Payroll Manager',         '4122', 'Finance & Accounting'),
    ('Credit Analyst',          '2422', 'Finance & Accounting'),
    ('Wealth Manager',          '2423', 'Finance & Accounting'),
    # Technology & Engineering
    ('Frontend Developer',      '2136', 'Technology & Engineering'),
    ('Backend Developer',       '2136', 'Technology & Engineering'),
    ('Full Stack Developer',    '2136', 'Technology & Engineering'),
    ('Mobile Developer',        '2136', 'Technology & Engineering'),
    ('Machine Learning Engineer','2137','Technology & Engineering'),
    ('AI Engineer',             '2137', 'Technology & Engineering'),
    ('Cloud Engineer',          '2138', 'Technology & Engineering'),
    ('QA Engineer',             '2136', 'Technology & Engineering'),
    ('Scrum Master',            '2135', 'Technology & Engineering'),
    ('Technical Lead',          '2136', 'Technology & Engineering'),
    ('Solutions Architect',     '2135', 'Technology & Engineering'),
    ('Database Administrator',  '2135', 'Technology & Engineering'),
    # Healthcare & Medicine
    ('Occupational Therapist',  '2221', 'Healthcare & Medicine'),
    ('Speech Therapist',        '2229', 'Healthcare & Medicine'),
    ('Dietitian',               '2223', 'Healthcare & Medicine'),
    ('Podiatrist',              '2229', 'Healthcare & Medicine'),
    ('Anaesthetist',            '2212', 'Healthcare & Medicine'),
    ('Psychiatrist',            '2211', 'Healthcare & Medicine'),
    ('A&E Doctor',              '2212', 'Healthcare & Medicine'),
    ('Care Worker',             '6145', 'Healthcare & Medicine'),
    ('Healthcare Assistant',    '6141', 'Healthcare & Medicine'),
    ('Dental Nurse',            '3217', 'Healthcare & Medicine'),
    ('Veterinarian',            '2216', 'Healthcare & Medicine'),
    ('Veterinary Nurse',        '3218', 'Healthcare & Medicine'),
    # Legal
    ('Conveyancer',             '2419', 'Legal'),
    ('Company Secretary',       '2419', 'Legal'),
    ('Compliance Manager',      '2419', 'Legal'),
    ('Notary',                  '2413', 'Legal'),
    # Education
    ('School Counsellor',       '2442', 'Education'),
    ('SENCO',                   '2316', 'Education'),
    ('Librarian',               '2312', 'Education'),
    ('Youth Worker',            '3231', 'Education'),
    ('Careers Adviser',         '3231', 'Education'),
    # Creative & Media
    ('Animator',                '3421', 'Creative & Media'),
    ('Game Developer',          '2136', 'Creative & Media'),
    ('Sound Engineer',          '3417', 'Creative & Media'),
    ('Art Director',            '3421', 'Creative & Media'),
    ('Social Media Manager',    '3543', 'Creative & Media'),
    ('Podcast Producer',        '3416', 'Creative & Media'),
    ('Web Designer',            '2166', 'Creative & Media'),
    # Trades & Construction
    ('Scaffolder',                      '5319', 'Trades & Construction'),
    ('Gas Engineer',                    '5244', 'Trades & Construction'),
    ('Tiler',                           '5329', 'Trades & Construction'),
    ('Floorer',                         '5329', 'Trades & Construction'),
    ('Joiner',                          '5215', 'Trades & Construction'),
    ('Project Manager (Construction)',  '2432', 'Trades & Construction'),
    ('Site Manager',                    '2432', 'Trades & Construction'),
    ('Estimator',                       '2432', 'Trades & Construction'),
    # Sales & Marketing
    ('Recruitment Consultant',  '3545', 'Sales & Marketing'),
    ('Estate Agent',            '3543', 'Sales & Marketing'),
    ('Buyer',                   '3544', 'Sales & Marketing'),
    ('Procurement Manager',     '3544', 'Sales & Marketing'),
    ('E-commerce Manager',      '3543', 'Sales & Marketing'),
    ('CRM Manager',             '3543', 'Sales & Marketing'),
    # Public Sector & Civil Service
    ('Prison Officer',          '3313', 'Public Sector & Civil Service'),
    ('Border Force Officer',    '3312', 'Public Sector & Civil Service'),
    ('HMRC Officer',            '4132', 'Public Sector & Civil Service'),
    ('NHS Manager',             '1184', 'Public Sector & Civil Service'),
    ('Council Officer',         '4132', 'Public Sector & Civil Service'),
    ('Charity Worker',          '3231', 'Public Sector & Civil Service'),
    ('Housing Officer',         '4132', 'Public Sector & Civil Service'),
    # Transport & Logistics (new group)
    ('HGV Driver',              '8211', 'Transport & Logistics'),
    ('Pilot',                   '3511', 'Transport & Logistics'),
    ('Air Traffic Controller',  '3512', 'Transport & Logistics'),
    ('Train Driver',            '8111', 'Transport & Logistics'),
    ('Logistics Manager',       '1133', 'Transport & Logistics'),
    ('Warehouse Manager',       '1133', 'Transport & Logistics'),
    ('Courier',                 '9229', 'Transport & Logistics'),
    ('Delivery Driver',         '8211', 'Transport & Logistics'),
    ('Supply Chain Manager',    '1133', 'Transport & Logistics'),
    # Science & Research (new group)
    ('Biologist',               '2112', 'Science & Research'),
    ('Chemist',                 '2111', 'Science & Research'),
    ('Physicist',               '2111', 'Science & Research'),
    ('Research Scientist',      '2119', 'Science & Research'),
    ('Lab Technician',          '3111', 'Science & Research'),
    ('Geologist',               '2114', 'Science & Research'),
    ('Ecologist',               '2113', 'Science & Research'),
    ('Forensic Scientist',      '2119', 'Science & Research'),
    ('Astronomer',              '2111', 'Science & Research'),
    # Property (new group)
    ('Letting Agent',           '3543', 'Property'),
    ('Property Developer',      '1319', 'Property'),
    ('Facilities Manager',      '1251', 'Property'),
    ('Surveyor',                '2432', 'Property'),
    ('Land Agent',              '2432', 'Property'),
    # HR & People (new group)
    ('HR Manager',                      '1136', 'HR & People'),
    ('HR Business Partner',             '1136', 'HR & People'),
    ('Recruiter',                       '3545', 'HR & People'),
    ('L&D Manager',                     '1136', 'HR & People'),
    ('Organisational Psychologist',     '2112', 'HR & People'),
    ('Talent Acquisition Specialist',   '3545', 'HR & People'),
    ('People Operations Manager',       '1136', 'HR & People'),
    # Customer Service & Admin (new group)
    ('Office Manager',          '4151', 'Customer Service & Admin'),
    ('Personal Assistant',      '4215', 'Customer Service & Admin'),
    ('Executive Assistant',     '4215', 'Customer Service & Admin'),
    ('Customer Service Manager','1136', 'Customer Service & Admin'),
    ('Receptionist',            '4232', 'Customer Service & Admin'),
    ('Administrator',           '4151', 'Customer Service & Admin'),
    ('Data Entry Clerk',        '4132', 'Customer Service & Admin'),
    ('Operations Manager',      '1133', 'Customer Service & Admin'),
]


def upgrade() -> None:
    occupation_codes = sa.table(
        'occupation_codes',
        sa.column('title', sa.String),
        sa.column('soc_code', sa.String),
        sa.column('soc_group', sa.String),
    )
    op.bulk_insert(occupation_codes, [
        {'title': t, 'soc_code': s, 'soc_group': g}
        for t, s, g in _NEW_OCCUPATIONS
    ])


def downgrade() -> None:
    titles = [t for t, _, _ in _NEW_OCCUPATIONS]
    op.execute(
        sa.text('DELETE FROM occupation_codes WHERE title IN :titles').bindparams(
            sa.bindparam('titles', expanding=True)
        ),
        {'titles': titles},
    )
