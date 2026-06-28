"""
Auth endpoint tests.
All tests use an in-memory SQLite DB (wired in conftest.py) — no real DB needed.
"""
from app.models import TaxYearConfig

REGISTER = "/api/auth/register"
LOGIN = "/api/auth/login"
SUMMARY = "/api/finance/summary"

_ALICE = {"email": "alice@example.com", "password": "s3cur3!"}


def _register(client, credentials=_ALICE):
    return client.post(REGISTER, json=credentials)


def _login(client, credentials=_ALICE):
    return client.post(LOGIN, data={"username": credentials["email"], "password": credentials["password"]})


def _auth_header(client, credentials=_ALICE):
    token = _login(client, credentials).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class TestRegister:
    def test_success(self, client):
        r = _register(client)
        assert r.status_code == 201
        body = r.json()
        assert body["message"] == "User created successfully"
        assert "user_id" in body
        assert "password" not in body          # hash must never be exposed

    def test_duplicate_email_rejected(self, client):
        _register(client)
        r = _register(client)                  # same email again
        assert r.status_code == 400
        assert "already registered" in r.json()["detail"]


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

class TestLogin:
    def test_correct_credentials_return_token(self, client):
        _register(client)
        r = _login(client)
        assert r.status_code == 200
        body = r.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    def test_wrong_password_rejected(self, client):
        _register(client)
        r = client.post(LOGIN, data={"username": _ALICE["email"], "password": "wrong!"})
        assert r.status_code == 401

    def test_unknown_email_rejected(self, client):
        r = client.post(LOGIN, data={"username": "nobody@example.com", "password": "anything"})
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Finance summary — auth enforcement
# ---------------------------------------------------------------------------

class TestFinanceSummaryAuth:
    def test_no_token_rejected(self, client):
        r = client.get(SUMMARY)
        assert r.status_code == 401

    def test_valid_token_accepted(self, client, db):
        # Seed tax config so the route can compute a result
        db.add(TaxYearConfig(
            tax_year="2026/27",
            personal_allowance=12570, basic_rate_threshold=50270, basic_rate_pct=20,
            higher_rate_threshold=125140, higher_rate_pct=40, additional_rate_pct=45,
            ni_primary_threshold=12584, ni_upper_threshold=50284,
            ni_main_rate_pct=8, ni_upper_rate_pct=2,
            pension_qualifying_lower=6240, pension_qualifying_upper=50270,
            pension_min_total_pct=8, pension_min_employer_pct=3,
        ))
        db.commit()

        _register(client)
        r = client.get(SUMMARY, headers=_auth_header(client))
        assert r.status_code == 200
        body = r.json()
        assert body["tax_year"] == "2026/27"
        assert body["take_home"]["gross_annual"] == 0.0   # no income sources added yet
