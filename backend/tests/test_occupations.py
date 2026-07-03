"""Tests for GET /api/occupations."""
import pytest
from fastapi.testclient import TestClient

from app.models.config import OccupationCode

OCCUPATIONS_URL = "/api/occupations"


def _seed(db, entries):
    for title, soc_code, soc_group in entries:
        db.add(OccupationCode(title=title, soc_code=soc_code, soc_group=soc_group))
    db.commit()


class TestListOccupations:
    def test_empty_when_no_data(self, client):
        r = client.get(OCCUPATIONS_URL)
        assert r.status_code == 200
        assert r.json() == []

    def test_no_auth_required(self, client, db):
        _seed(db, [('Software Engineer', '2136', 'Technology & Engineering')])
        r = client.get(OCCUPATIONS_URL)
        assert r.status_code == 200

    def test_returns_correct_fields(self, client, db):
        _seed(db, [('Nurse', '2231', 'Healthcare & Medicine')])
        item = client.get(OCCUPATIONS_URL).json()[0]
        assert item['title'] == 'Nurse'
        assert item['soc_code'] == '2231'
        assert item['soc_group'] == 'Healthcare & Medicine'
        assert 'id' in item

    def test_ordered_by_group_then_title(self, client, db):
        _seed(db, [
            ('Plumber',           '5232', 'Trades & Construction'),
            ('Accountant',        '2421', 'Finance & Accounting'),
            ('Electrician',       '5241', 'Trades & Construction'),
            ('Financial Analyst', '2422', 'Finance & Accounting'),
        ])
        titles = [i['title'] for i in client.get(OCCUPATIONS_URL).json()]
        # Finance & Accounting comes before Trades & Construction alphabetically
        assert titles.index('Accountant') < titles.index('Plumber')
        assert titles.index('Financial Analyst') < titles.index('Plumber')
        # Within Trades: Electrician before Plumber alphabetically
        assert titles.index('Electrician') < titles.index('Plumber')

    def test_multiple_groups_returned(self, client, db):
        _seed(db, [
            ('Software Engineer', '2136', 'Technology & Engineering'),
            ('Nurse',             '2231', 'Healthcare & Medicine'),
        ])
        groups = {i['soc_group'] for i in client.get(OCCUPATIONS_URL).json()}
        assert 'Technology & Engineering' in groups
        assert 'Healthcare & Medicine' in groups
