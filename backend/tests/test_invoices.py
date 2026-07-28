"""Tests for invoicing: contacts, invoice CRUD, status flow, PDF generation,
and the integration with business income (Upcoming / confirmed income)."""
from datetime import date, timedelta
from io import BytesIO

import pytest
from pypdf import PdfReader

REGISTER = "/api/auth/register"
LOGIN = "/api/auth/login"
PROFILE_URL = "/api/profile"

CONTACTS_URL = "/api/business/contacts"
INVOICES_URL = "/api/business/invoices"
INCOME_URL = "/api/business/income"
UPCOMING_URL = "/api/business/upcoming"
SUMMARY_URL = "/api/business/summary"

TODAY = date.today()


def auth(client, email="alice@test.com", password="testpass123!"):
    client.post(REGISTER, json={"email": email, "password": password})
    r = client.post(LOGIN, data={"username": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _create_contact(client, h, name="Glow Cosmetics Ltd", address=None, email=None):
    r = client.post(CONTACTS_URL, json={"name": name, "address": address, "email": email}, headers=h)
    assert r.status_code == 201, r.json()
    return r.json()


def _line_items():
    return [
        {"description": "6 Instagram pictures", "quantity": 1, "unit_price": 200.0},
        {"description": "TikTok video", "quantity": 1, "unit_price": 1000.0},
    ]


def _create_invoice(client, h, contact_id, line_items=None, status="draft", issue_date=None, due_date=None, notes=None):
    body = {
        "contact_id": contact_id,
        "issue_date": (issue_date or TODAY).isoformat(),
        "due_date": (due_date or (TODAY + timedelta(days=14))).isoformat(),
        "line_items": line_items if line_items is not None else _line_items(),
        "status": status,
        "notes": notes,
    }
    r = client.post(INVOICES_URL, json=body, headers=h)
    assert r.status_code == 201, r.json()
    return r.json()


def _set_business_profile(client, h, vat_registered=False, vat_number=None):
    body = {
        "business_name": "Alex Rivera Creative",
        "business_address": "14 Maple Street\nManchester\nM1 2AB",
        "bank_account_name": "A Rivera",
        "bank_sort_code": "12-34-56",
        "bank_account_number": "12345678",
        "vat_registered": vat_registered,
    }
    if vat_number is not None:
        body["vat_number"] = vat_number
    r = client.patch(PROFILE_URL, json=body, headers=h)
    assert r.status_code == 200, r.json()
    return r.json()


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------

class TestContacts:
    def test_create_and_list(self, client):
        h = auth(client)
        _create_contact(client, h, name="Brand A")
        _create_contact(client, h, name="Brand B")
        r = client.get(CONTACTS_URL, headers=h)
        names = [c["name"] for c in r.json()]
        assert names == ["Brand A", "Brand B"]  # alphabetical

    def test_create_with_address_and_email(self, client):
        h = auth(client)
        c = _create_contact(client, h, name="Brand C", address="1 Street\nCity", email="hi@brand.com")
        assert c["address"] == "1 Street\nCity"
        assert c["email"] == "hi@brand.com"

    def test_update(self, client):
        h = auth(client)
        c = _create_contact(client, h)
        r = client.patch(f"{CONTACTS_URL}/{c['id']}", json={"email": "new@brand.com"}, headers=h)
        assert r.status_code == 200
        assert r.json()["email"] == "new@brand.com"

    def test_delete_removes_from_list(self, client):
        h = auth(client)
        c = _create_contact(client, h)
        assert client.delete(f"{CONTACTS_URL}/{c['id']}", headers=h).status_code == 204
        assert client.get(CONTACTS_URL, headers=h).json() == []

    def test_ownership_isolation(self, client):
        alice = auth(client, "alice@test.com")
        bob = auth(client, "bob@test.com")
        c = _create_contact(client, alice)
        assert client.patch(f"{CONTACTS_URL}/{c['id']}", json={"name": "Hijacked"}, headers=bob).status_code == 404
        assert client.delete(f"{CONTACTS_URL}/{c['id']}", headers=bob).status_code == 404

    def test_reused_across_invoices(self, client):
        h = auth(client)
        c = _create_contact(client, h, name="Recurring Brand")
        inv1 = _create_invoice(client, h, c["id"])
        inv2 = _create_invoice(client, h, c["id"])
        assert inv1["contact"]["id"] == inv2["contact"]["id"] == c["id"]

    def test_inline_added_contact_persists(self, client):
        """Simulates the 'add a new contact inline' UX: the frontend calls
        POST /contacts first, then references it — confirm that contact then
        shows up in the reusable list for a later invoice."""
        h = auth(client)
        new_contact = _create_contact(client, h, name="New Inline Brand")
        assert new_contact["id"] in [c["id"] for c in client.get(CONTACTS_URL, headers=h).json()]
        inv = _create_invoice(client, h, new_contact["id"])
        assert inv["contact"]["name"] == "New Inline Brand"


# ---------------------------------------------------------------------------
# Invoice creation — line items, subtotal, VAT, numbering
# ---------------------------------------------------------------------------

class TestInvoiceCreation:
    def test_subtotal_is_sum_of_line_totals(self, client):
        h = auth(client)
        c = _create_contact(client, h)
        inv = _create_invoice(client, h, c["id"], line_items=[
            {"description": "A", "quantity": 2, "unit_price": 50.0},
            {"description": "B", "quantity": 1, "unit_price": 30.0},
        ])
        assert inv["subtotal"] == pytest.approx(130.0)
        assert inv["line_items"][0]["line_total"] == pytest.approx(100.0)
        assert inv["line_items"][1]["line_total"] == pytest.approx(30.0)

    def test_vat_registered_adds_20_percent_and_total(self, client):
        h = auth(client)
        _set_business_profile(client, h, vat_registered=True, vat_number="GB123456789")
        c = _create_contact(client, h)
        inv = _create_invoice(client, h, c["id"], line_items=[{"description": "X", "quantity": 1, "unit_price": 1000.0}])
        assert inv["vat_registered"] is True
        assert inv["subtotal"] == pytest.approx(1000.0)
        assert inv["vat_amount"] == pytest.approx(200.0)
        assert inv["total"] == pytest.approx(1200.0)

    def test_non_vat_registered_no_vat(self, client):
        h = auth(client)
        _set_business_profile(client, h, vat_registered=False)
        c = _create_contact(client, h)
        inv = _create_invoice(client, h, c["id"], line_items=[{"description": "X", "quantity": 1, "unit_price": 1000.0}])
        assert inv["vat_registered"] is False
        assert inv["vat_amount"] == 0.0
        assert inv["total"] == pytest.approx(1000.0)

    def test_invoice_number_sequential_per_user(self, client):
        h = auth(client)
        c = _create_contact(client, h)
        numbers = [_create_invoice(client, h, c["id"])["invoice_number"] for _ in range(3)]
        assert numbers == ["INV-001", "INV-002", "INV-003"]

    def test_invoice_numbering_isolated_per_user(self, client):
        alice = auth(client, "alice@test.com")
        bob = auth(client, "bob@test.com")
        c_alice = _create_contact(client, alice)
        c_bob = _create_contact(client, bob)
        assert _create_invoice(client, alice, c_alice["id"])["invoice_number"] == "INV-001"
        assert _create_invoice(client, bob, c_bob["id"])["invoice_number"] == "INV-001"

    def test_deleted_invoice_number_not_reused(self, client):
        h = auth(client)
        c = _create_contact(client, h)
        inv1 = _create_invoice(client, h, c["id"])
        assert inv1["invoice_number"] == "INV-001"
        client.delete(f"{INVOICES_URL}/{inv1['id']}", headers=h)
        inv2 = _create_invoice(client, h, c["id"])
        assert inv2["invoice_number"] == "INV-002"

    def test_at_least_one_line_item_required(self, client):
        h = auth(client)
        c = _create_contact(client, h)
        r = client.post(INVOICES_URL, json={
            "contact_id": c["id"], "issue_date": TODAY.isoformat(), "due_date": TODAY.isoformat(),
            "line_items": [], "status": "draft",
        }, headers=h)
        assert r.status_code == 400

    def test_quantity_must_be_positive(self, client):
        h = auth(client)
        c = _create_contact(client, h)
        r = client.post(INVOICES_URL, json={
            "contact_id": c["id"], "issue_date": TODAY.isoformat(), "due_date": TODAY.isoformat(),
            "line_items": [{"description": "X", "quantity": 0, "unit_price": 10.0}], "status": "draft",
        }, headers=h)
        assert r.status_code == 400

    def test_contact_must_belong_to_user(self, client):
        alice = auth(client, "alice@test.com")
        bob = auth(client, "bob@test.com")
        c_alice = _create_contact(client, alice)
        r = client.post(INVOICES_URL, json={
            "contact_id": c_alice["id"], "issue_date": TODAY.isoformat(), "due_date": TODAY.isoformat(),
            "line_items": _line_items(), "status": "draft",
        }, headers=bob)
        assert r.status_code == 404

    def test_create_with_status_sent_creates_upcoming_income_immediately(self, client):
        h = auth(client)
        c = _create_contact(client, h)
        due = TODAY + timedelta(days=10)
        inv = _create_invoice(client, h, c["id"], status="sent", due_date=due)
        assert inv["status"] == "sent"
        upcoming = client.get(UPCOMING_URL, headers=h).json()
        assert any(i["date_received"] == due.isoformat() for i in upcoming["income"])


# ---------------------------------------------------------------------------
# Status flow — draft -> sent -> paid, overdue derivation, edit/delete guards
# ---------------------------------------------------------------------------

class TestInvoiceStatusFlow:
    def test_draft_to_sent_to_paid(self, client):
        h = auth(client)
        c = _create_contact(client, h)
        inv = _create_invoice(client, h, c["id"])
        assert inv["status"] == inv["effective_status"] == "draft"

        sent = client.post(f"{INVOICES_URL}/{inv['id']}/send", headers=h).json()
        assert sent["status"] == "sent"

        paid = client.post(f"{INVOICES_URL}/{inv['id']}/paid", json={}, headers=h).json()
        assert paid["status"] == paid["effective_status"] == "paid"
        assert paid["paid_date"] == TODAY.isoformat()

    def test_overdue_derived_when_sent_and_past_due(self, client):
        h = auth(client)
        c = _create_contact(client, h)
        past_due = TODAY - timedelta(days=5)
        inv = _create_invoice(client, h, c["id"], status="sent", issue_date=past_due - timedelta(days=14), due_date=past_due)
        assert inv["status"] == "sent"
        assert inv["effective_status"] == "overdue"

    def test_not_overdue_when_paid_even_if_past_due(self, client):
        h = auth(client)
        c = _create_contact(client, h)
        past_due = TODAY - timedelta(days=5)
        inv = _create_invoice(client, h, c["id"], status="sent", issue_date=past_due - timedelta(days=14), due_date=past_due)
        paid = client.post(f"{INVOICES_URL}/{inv['id']}/paid", json={}, headers=h).json()
        assert paid["effective_status"] == "paid"

    def test_not_overdue_while_draft_even_if_past_due(self, client):
        h = auth(client)
        c = _create_contact(client, h)
        past_due = TODAY - timedelta(days=5)
        inv = _create_invoice(client, h, c["id"], status="draft", due_date=past_due)
        assert inv["effective_status"] == "draft"

    def test_mark_paid_directly_from_draft_skips_send(self, client):
        h = auth(client)
        c = _create_contact(client, h)
        inv = _create_invoice(client, h, c["id"])
        paid = client.post(f"{INVOICES_URL}/{inv['id']}/paid", json={}, headers=h).json()
        assert paid["status"] == "paid"

    def test_cannot_edit_paid_invoice(self, client):
        h = auth(client)
        c = _create_contact(client, h)
        inv = _create_invoice(client, h, c["id"])
        client.post(f"{INVOICES_URL}/{inv['id']}/paid", json={}, headers=h)
        r = client.patch(f"{INVOICES_URL}/{inv['id']}", json={"notes": "changed"}, headers=h)
        assert r.status_code == 400

    def test_cannot_delete_paid_invoice(self, client):
        h = auth(client)
        c = _create_contact(client, h)
        inv = _create_invoice(client, h, c["id"])
        client.post(f"{INVOICES_URL}/{inv['id']}/paid", json={}, headers=h)
        r = client.delete(f"{INVOICES_URL}/{inv['id']}", headers=h)
        assert r.status_code == 400

    def test_delete_sent_invoice_deactivates_linked_income(self, client, db):
        from app.models import BusinessIncome
        h = auth(client)
        c = _create_contact(client, h)
        inv = _create_invoice(client, h, c["id"], status="sent")
        income = db.query(BusinessIncome).filter_by(invoice_id=inv["id"]).first()
        assert income is not None and income.is_active is True

        client.delete(f"{INVOICES_URL}/{inv['id']}", headers=h)
        db.refresh(income)
        assert income.is_active is False

    def test_editing_due_date_of_sent_invoice_updates_linked_income_date(self, client, db):
        from app.models import BusinessIncome
        h = auth(client)
        c = _create_contact(client, h)
        inv = _create_invoice(client, h, c["id"], status="sent", due_date=TODAY + timedelta(days=10))
        new_due = TODAY + timedelta(days=20)
        client.patch(f"{INVOICES_URL}/{inv['id']}", json={"due_date": new_due.isoformat()}, headers=h)
        income = db.query(BusinessIncome).filter_by(invoice_id=inv["id"]).first()
        assert income.date_received == new_due

    def test_list_and_get_invoice(self, client):
        h = auth(client)
        c = _create_contact(client, h)
        inv = _create_invoice(client, h, c["id"])
        listed = client.get(INVOICES_URL, headers=h).json()
        assert any(i["id"] == inv["id"] for i in listed)
        got = client.get(f"{INVOICES_URL}/{inv['id']}", headers=h).json()
        assert got["id"] == inv["id"]

    def test_deleted_invoice_not_in_list(self, client):
        h = auth(client)
        c = _create_contact(client, h)
        inv = _create_invoice(client, h, c["id"])
        client.delete(f"{INVOICES_URL}/{inv['id']}", headers=h)
        assert inv["id"] not in [i["id"] for i in client.get(INVOICES_URL, headers=h).json()]

    def test_ownership_isolation(self, client):
        alice = auth(client, "alice@test.com")
        bob = auth(client, "bob@test.com")
        c = _create_contact(client, alice)
        inv = _create_invoice(client, alice, c["id"])
        assert client.get(f"{INVOICES_URL}/{inv['id']}", headers=bob).status_code == 404
        assert client.post(f"{INVOICES_URL}/{inv['id']}/send", headers=bob).status_code == 404


# ---------------------------------------------------------------------------
# Integration with business income — Upcoming, confirmed income, no double
# counting, ex-VAT income, and the bidirectional approve-income <-> invoice
# status sync.
# ---------------------------------------------------------------------------

class TestInvoiceIncomeIntegration:
    def test_sent_invoice_appears_in_upcoming_as_expected_income(self, client):
        h = auth(client)
        c = _create_contact(client, h)
        due = TODAY + timedelta(days=7)
        inv = _create_invoice(client, h, c["id"], status="sent", due_date=due)

        upcoming = client.get(UPCOMING_URL, headers=h).json()
        matches = [i for i in upcoming["income"] if i.get("invoice_id") == inv["id"]]
        assert len(matches) == 1
        assert matches[0]["date_received"] == due.isoformat()
        assert matches[0]["is_approved"] is False
        assert matches[0]["amount"] == pytest.approx(inv["subtotal"])

    def test_paid_invoice_becomes_confirmed_income(self, client):
        h = auth(client)
        c = _create_contact(client, h)
        inv = _create_invoice(client, h, c["id"], status="sent", due_date=TODAY - timedelta(days=1))
        client.post(f"{INVOICES_URL}/{inv['id']}/paid", json={}, headers=h)

        confirmed = client.get(INCOME_URL, headers=h).json()
        matches = [i for i in confirmed if i.get("invoice_id") == inv["id"]]
        assert len(matches) == 1
        assert matches[0]["is_approved"] is True

    def test_paid_invoice_counts_in_summary_revenue_exactly_once(self, client):
        h = auth(client)
        c = _create_contact(client, h)
        inv = _create_invoice(client, h, c["id"], status="sent", due_date=TODAY - timedelta(days=1),
                               line_items=[{"description": "X", "quantity": 1, "unit_price": 500.0}])
        client.post(f"{INVOICES_URL}/{inv['id']}/paid", json={}, headers=h)

        summary = client.get(SUMMARY_URL, headers=h).json()
        assert summary["revenue_ytd"] == pytest.approx(500.0)

        # No double counting: there is exactly one BusinessIncome row for this invoice.
        all_income = client.get(INCOME_URL, headers=h).json()
        assert len([i for i in all_income if i.get("invoice_id") == inv["id"]]) == 1

    def test_no_double_counting_when_marked_paid_twice(self, client):
        """Calling /paid again (e.g. accidental double-click) must not create
        a second income row or inflate revenue."""
        h = auth(client)
        c = _create_contact(client, h)
        inv = _create_invoice(client, h, c["id"], status="sent", due_date=TODAY - timedelta(days=1),
                               line_items=[{"description": "X", "quantity": 1, "unit_price": 500.0}])
        client.post(f"{INVOICES_URL}/{inv['id']}/paid", json={}, headers=h)
        client.post(f"{INVOICES_URL}/{inv['id']}/paid", json={}, headers=h)

        all_income = client.get(INCOME_URL, headers=h).json()
        assert len([i for i in all_income if i.get("invoice_id") == inv["id"]]) == 1
        summary = client.get(SUMMARY_URL, headers=h).json()
        assert summary["revenue_ytd"] == pytest.approx(500.0)

    def test_income_from_paid_invoice_is_ex_vat_subtotal(self, client):
        h = auth(client)
        _set_business_profile(client, h, vat_registered=True, vat_number="GB123456789")
        c = _create_contact(client, h)
        inv = _create_invoice(client, h, c["id"], status="sent", due_date=TODAY - timedelta(days=1),
                               line_items=[{"description": "X", "quantity": 1, "unit_price": 1000.0}])
        assert inv["subtotal"] == pytest.approx(1000.0)
        assert inv["total"] == pytest.approx(1200.0)  # VAT-inclusive

        client.post(f"{INVOICES_URL}/{inv['id']}/paid", json={}, headers=h)
        confirmed = client.get(INCOME_URL, headers=h).json()
        match = next(i for i in confirmed if i.get("invoice_id") == inv["id"])
        assert match["amount"] == pytest.approx(1000.0)  # ex-VAT, not 1200

        summary = client.get(SUMMARY_URL, headers=h).json()
        assert summary["revenue_ytd"] == pytest.approx(1000.0)

    def test_approving_from_upcoming_also_marks_invoice_paid(self, client):
        """The reverse direction of the sync: a user approving the linked
        income row directly from the Upcoming page (not via the invoice's own
        'Mark as paid' button) must still flip the invoice to paid."""
        h = auth(client)
        c = _create_contact(client, h)
        past_due = TODAY - timedelta(days=1)
        inv = _create_invoice(client, h, c["id"], status="sent", due_date=past_due)

        upcoming = client.get(UPCOMING_URL, headers=h).json()
        income_row = next(i for i in upcoming["income"] if i.get("invoice_id") == inv["id"])

        r = client.post(f"{INCOME_URL}/{income_row['id']}/approve", json={}, headers=h)
        assert r.status_code == 200
        assert r.json()["is_approved"] is True

        updated_invoice = client.get(f"{INVOICES_URL}/{inv['id']}", headers=h).json()
        assert updated_invoice["status"] == "paid"
        assert updated_invoice["paid_date"] == past_due.isoformat()


# ---------------------------------------------------------------------------
# PDF generation
# ---------------------------------------------------------------------------

class TestInvoicePdf:
    def _pdf_text(self, client, h, invoice_id):
        r = client.get(f"{INVOICES_URL}/{invoice_id}/pdf", headers=h)
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"
        assert r.content[:4] == b"%PDF"
        reader = PdfReader(BytesIO(r.content))
        return "\n".join(page.extract_text() for page in reader.pages)

    def test_pdf_contains_all_required_sections_vat_registered(self, client):
        h = auth(client)
        _set_business_profile(client, h, vat_registered=True, vat_number="GB123456789")
        c = _create_contact(client, h, name="Glow Cosmetics Ltd", address="1 Brand Ave\nLondon")
        inv = _create_invoice(client, h, c["id"], line_items=[
            {"description": "6 Instagram pictures", "quantity": 1, "unit_price": 200.0},
            {"description": "TikTok video", "quantity": 1, "unit_price": 1000.0},
        ])
        text = self._pdf_text(client, h, inv["id"])

        assert "INVOICE" in text
        assert inv["invoice_number"] in text
        assert "Alex Rivera Creative" in text          # sender
        assert "Manchester" in text                    # sender address
        assert "GB123456789" in text                   # VAT number
        assert "Glow Cosmetics Ltd" in text             # bill to
        assert "6 Instagram pictures" in text
        assert "TikTok video" in text
        assert "Subtotal" in text
        assert "VAT" in text
        assert "1,200.00" in text                       # total (1000 + 200 VAT)
        assert "A Rivera" in text                       # bank account name
        assert "12-34-56" in text                       # sort code
        assert "12345678" in text                       # account number

    def test_pdf_non_vat_registered_has_no_vat_content(self, client):
        h = auth(client)
        _set_business_profile(client, h, vat_registered=False)
        c = _create_contact(client, h, name="Sunny Snacks Co")
        inv = _create_invoice(client, h, c["id"], line_items=[{"description": "Product review", "quantity": 1, "unit_price": 350.0}])
        text = self._pdf_text(client, h, inv["id"])

        assert "VAT" not in text
        assert "350.00" in text

    def test_pdf_requires_ownership(self, client):
        alice = auth(client, "alice@test.com")
        bob = auth(client, "bob@test.com")
        c = _create_contact(client, alice)
        inv = _create_invoice(client, alice, c["id"])
        assert client.get(f"{INVOICES_URL}/{inv['id']}/pdf", headers=bob).status_code == 404


# ---------------------------------------------------------------------------
# Profile — new invoicing fields
# ---------------------------------------------------------------------------

class TestProfileInvoicingFields:
    def test_round_trip_business_and_bank_fields(self, client):
        h = auth(client)
        updated = _set_business_profile(client, h, vat_registered=False)
        assert updated["business_name"] == "Alex Rivera Creative"
        assert updated["bank_sort_code"] == "12-34-56"
        assert updated["vat_registered"] is False
        assert updated["vat_number"] is None

        fetched = client.get(PROFILE_URL, headers=h).json()
        assert fetched["business_name"] == "Alex Rivera Creative"
        assert fetched["bank_account_number"] == "12345678"

    def test_vat_number_required_when_vat_registered(self, client):
        h = auth(client)
        r = client.patch(PROFILE_URL, json={"vat_registered": True}, headers=h)
        assert r.status_code == 400

    def test_vat_registered_with_number_succeeds(self, client):
        h = auth(client)
        r = client.patch(PROFILE_URL, json={"vat_registered": True, "vat_number": "GB123456789"}, headers=h)
        assert r.status_code == 200
        assert r.json()["vat_registered"] is True
        assert r.json()["vat_number"] == "GB123456789"

    def test_bank_details_default_to_null(self, client):
        h = auth(client)
        client.post(REGISTER, json={"email": "fresh@test.com", "password": "testpass123!"})
        fresh_h = {"Authorization": f"Bearer {client.post(LOGIN, data={'username': 'fresh@test.com', 'password': 'testpass123!'}).json()['access_token']}"}
        p = client.get(PROFILE_URL, headers=fresh_h).json()
        assert p["bank_account_name"] is None
        assert p["bank_sort_code"] is None
        assert p["bank_account_number"] is None
        assert p["vat_registered"] is False
