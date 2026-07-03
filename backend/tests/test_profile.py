"""
Profile endpoint and postcode lookup tests.
"""
from app.services.postcode_lookup import get_region_from_postcode, validate_postcode_outward

REGISTER = "/api/auth/register"
LOGIN = "/api/auth/login"
PROFILE = "/api/profile"

_ALICE = {"email": "alice@example.com", "password": "s3cur3!"}


def _register(client, credentials=_ALICE):
    return client.post(REGISTER, json=credentials)


def _auth_header(client, credentials=_ALICE):
    token = client.post(
        LOGIN, data={"username": credentials["email"], "password": credentials["password"]}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Postcode lookup unit tests (no HTTP, no DB)
# ---------------------------------------------------------------------------

class TestPostcodeLookup:
    def test_london_sw_prefix(self):
        assert get_region_from_postcode("SW1A") == "London"

    def test_london_e_prefix(self):
        assert get_region_from_postcode("E1") == "London"

    def test_scotland_eh_prefix(self):
        assert get_region_from_postcode("EH1") == "Scotland"

    def test_scotland_g_prefix(self):
        assert get_region_from_postcode("G1") == "Scotland"

    def test_north_west_m_prefix(self):
        assert get_region_from_postcode("M1") == "North West"

    def test_wales_cf_prefix(self):
        assert get_region_from_postcode("CF10") == "Wales"

    def test_northern_ireland_bt_prefix(self):
        assert get_region_from_postcode("BT1") == "Northern Ireland"

    def test_yorkshire_s_prefix(self):
        assert get_region_from_postcode("S1") == "Yorkshire and the Humber"

    def test_case_insensitive(self):
        assert get_region_from_postcode("sw1a") == "London"

    def test_unrecognized_prefix_returns_none(self):
        assert get_region_from_postcode("ZZ1") is None

    def test_none_input_returns_none(self):
        assert get_region_from_postcode(None) is None

    def test_empty_string_returns_none(self):
        assert get_region_from_postcode("") is None


class TestValidatePostcodeOutward:
    def test_valid_two_char(self):
        assert validate_postcode_outward("M1") is True

    def test_valid_three_char(self):
        assert validate_postcode_outward("SW1") is True

    def test_valid_four_char(self):
        assert validate_postcode_outward("SW1A") is True

    def test_valid_ec_style(self):
        assert validate_postcode_outward("EC1A") is True

    def test_lowercase_accepted(self):
        assert validate_postcode_outward("sw1a") is True

    def test_full_postcode_rejected(self):
        assert validate_postcode_outward("SW1A 1AA") is False

    def test_garbage_rejected(self):
        assert validate_postcode_outward("HELLO") is False

    def test_digits_only_rejected(self):
        assert validate_postcode_outward("123") is False

    def test_empty_rejected(self):
        assert validate_postcode_outward("") is False


# ---------------------------------------------------------------------------
# Profile API tests
# ---------------------------------------------------------------------------

class TestProfileAPI:
    def test_get_profile_empty_for_new_user(self, client, db):
        _register(client)
        body = client.get(PROFILE, headers=_auth_header(client)).json()
        assert body["date_of_birth"] is None
        assert body["occupation"] is None
        assert body["postcode_outward"] is None
        assert body["region"] is None

    def test_update_all_fields(self, client, db):
        _register(client)
        headers = _auth_header(client)
        resp = client.put(PROFILE, json={
            "date_of_birth": "1990-06-15",
            "occupation": "Software Engineer",
            "postcode_outward": "SW1A",
        }, headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["date_of_birth"] == "1990-06-15"
        assert body["occupation"] == "Software Engineer"
        assert body["postcode_outward"] == "SW1A"
        assert body["region"] == "London"

    def test_partial_update_preserves_existing(self, client, db):
        _register(client)
        headers = _auth_header(client)
        client.put(PROFILE, json={"occupation": "Teacher", "postcode_outward": "EH1"}, headers=headers)
        # Update only occupation
        client.put(PROFILE, json={"occupation": "Doctor"}, headers=headers)
        body = client.get(PROFILE, headers=headers).json()
        assert body["occupation"] == "Doctor"
        assert body["postcode_outward"] == "EH1"  # unchanged
        assert body["region"] == "Scotland"

    def test_postcode_normalized_to_uppercase(self, client, db):
        _register(client)
        headers = _auth_header(client)
        client.put(PROFILE, json={"postcode_outward": "m1"}, headers=headers)
        body = client.get(PROFILE, headers=headers).json()
        assert body["postcode_outward"] == "M1"

    def test_region_derived_not_stored(self, client, db):
        # Region comes from the lookup each time, not a stored column.
        # Verified by checking the response rather than the DB directly.
        _register(client)
        headers = _auth_header(client)
        client.put(PROFILE, json={"postcode_outward": "BT1"}, headers=headers)
        body = client.get(PROFILE, headers=headers).json()
        assert body["region"] == "Northern Ireland"

    def test_unrecognized_postcode_region_is_null(self, client, db):
        _register(client)
        headers = _auth_header(client)
        # ZZ1 is a valid format but not a real postcode area
        client.put(PROFILE, json={"postcode_outward": "ZZ1"}, headers=headers)
        body = client.get(PROFILE, headers=headers).json()
        assert body["postcode_outward"] == "ZZ1"
        assert body["region"] is None

    def test_postcode_invalid_format_rejected(self, client, db):
        _register(client)
        headers = _auth_header(client)
        resp = client.put(PROFILE, json={"postcode_outward": "SW1A 1AA"}, headers=headers)
        assert resp.status_code == 422

    def test_postcode_garbage_rejected(self, client, db):
        _register(client)
        headers = _auth_header(client)
        resp = client.put(PROFILE, json={"postcode_outward": "NOT-A-POSTCODE"}, headers=headers)
        assert resp.status_code == 422

    def test_clear_field_with_null(self, client, db):
        _register(client)
        headers = _auth_header(client)
        client.put(PROFILE, json={"occupation": "Nurse"}, headers=headers)
        client.put(PROFILE, json={"occupation": None}, headers=headers)
        body = client.get(PROFILE, headers=headers).json()
        assert body["occupation"] is None

    def test_requires_auth(self, client, db):
        resp = client.get(PROFILE)
        assert resp.status_code == 401

    def test_users_isolated(self, client, db):
        bob = {"email": "bob@example.com", "password": "bobpass1"}
        _register(client)
        client.post(REGISTER, json=bob)
        alice_headers = _auth_header(client)
        bob_headers = _auth_header(client, bob)

        client.put(PROFILE, json={"occupation": "Alice's job"}, headers=alice_headers)
        bob_body = client.get(PROFILE, headers=bob_headers).json()
        assert bob_body["occupation"] is None

    def test_first_name_null_for_new_user(self, client, db):
        _register(client)
        body = client.get(PROFILE, headers=_auth_header(client)).json()
        assert body["first_name"] is None

    def test_put_saves_first_name(self, client, db):
        _register(client)
        headers = _auth_header(client)
        resp = client.put(PROFILE, json={"first_name": "Ben"}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["first_name"] == "Ben"

    def test_first_name_persists_on_get(self, client, db):
        _register(client)
        headers = _auth_header(client)
        client.put(PROFILE, json={"first_name": "Alice"}, headers=headers)
        body = client.get(PROFILE, headers=headers).json()
        assert body["first_name"] == "Alice"


class TestProfilePatch:
    def test_patch_saves_first_name(self, client, db):
        _register(client)
        headers = _auth_header(client)
        resp = client.patch(PROFILE, json={"first_name": "Sam"}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["first_name"] == "Sam"

    def test_patch_partial_does_not_null_other_fields(self, client, db):
        _register(client)
        headers = _auth_header(client)
        client.patch(PROFILE, json={"occupation": "Engineer", "postcode_outward": "M1"}, headers=headers)
        client.patch(PROFILE, json={"first_name": "Jo"}, headers=headers)
        body = client.get(PROFILE, headers=headers).json()
        assert body["first_name"] == "Jo"
        assert body["occupation"] == "Engineer"
        assert body["postcode_outward"] == "M1"

    def test_patch_saves_date_of_birth(self, client, db):
        _register(client)
        headers = _auth_header(client)
        resp = client.patch(PROFILE, json={"date_of_birth": "1995-03-20"}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["date_of_birth"] == "1995-03-20"

    def test_patch_saves_occupation(self, client, db):
        _register(client)
        headers = _auth_header(client)
        resp = client.patch(PROFILE, json={"occupation": "Software Engineer"}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["occupation"] == "Software Engineer"

    def test_patch_saves_postcode(self, client, db):
        _register(client)
        headers = _auth_header(client)
        resp = client.patch(PROFILE, json={"postcode_outward": "SW1A"}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["postcode_outward"] == "SW1A"

    def test_patch_all_four_fields(self, client, db):
        _register(client)
        headers = _auth_header(client)
        resp = client.patch(PROFILE, json={
            "first_name": "Taylor",
            "date_of_birth": "1998-07-04",
            "occupation": "Teacher",
            "postcode_outward": "EH1",
        }, headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["first_name"] == "Taylor"
        assert body["date_of_birth"] == "1998-07-04"
        assert body["occupation"] == "Teacher"
        assert body["postcode_outward"] == "EH1"
        assert body["region"] == "Scotland"

    def test_patch_requires_auth(self, client, db):
        resp = client.patch(PROFILE, json={"first_name": "X"})
        assert resp.status_code == 401
