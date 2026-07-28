"""
Invoicing: contacts (saved brands/clients) and invoices (with line items, PDF
generation, and status tracking that flows into business income).

Design notes:
- Stored invoice status is only ever draft/sent/paid. "Overdue" is derived
  (sent + due_date in the past + not paid), never stored, so it can't go stale.
- A sent or paid invoice has exactly ONE linked BusinessIncome row
  (BusinessIncome.invoice_id) — that row IS the invoice's income, not a
  separate thing alongside it, so it can never be double-counted. It starts
  unapproved (is_approved=False) when sent — this is what makes it appear in
  Upcoming as expected income via the existing /business/upcoming query — and
  becomes approved (confirmed) when the invoice is marked paid, via the exact
  same approve_income endpoint used for any other income entry (see
  app/routes/business.py: approve_income's invoice-sync block). Whichever path
  confirms it — the invoice's own "Mark as paid" action, or approving it
  directly from the Upcoming page — both converge on that one row.
- The income amount is always the ex-VAT subtotal, never the VAT-inclusive
  total: VAT collected isn't the user's income, it's owed to HMRC.
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import BusinessIncome, Contact, Invoice, InvoiceLineItem, User
from app.routes.auth import get_current_user
from app.schemas import (
    VAT_RATE,
    ContactCreate,
    ContactOut,
    ContactUpdate,
    InvoiceCreate,
    InvoiceLineItemOut,
    InvoiceOut,
    InvoiceUpdate,
    MarkPaidBody,
)
from app.services.invoice_pdf import generate_invoice_pdf
from app.utils import get_owned_or_404

router = APIRouter(prefix="/business", tags=["invoices"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _next_invoice_number(db: Session, user_id: int) -> str:
    """Sequential per user (INV-001, INV-002, ...). Scans ALL of the user's
    invoices regardless of is_active, so a deleted invoice's number is never
    reused — self-healing without needing a separate counter column."""
    rows = db.query(Invoice.invoice_number).filter_by(user_id=user_id).all()
    max_n = 0
    for (num,) in rows:
        try:
            max_n = max(max_n, int(num.rsplit("-", 1)[-1]))
        except (ValueError, IndexError):
            continue
    return f"INV-{max_n + 1:03d}"


def _compute_subtotal(line_items) -> float:
    return round(sum(li.quantity * li.unit_price for li in line_items), 2)


def _compute_totals(line_items, vat_registered: bool) -> tuple[float, float, float]:
    subtotal = _compute_subtotal(line_items)
    vat_amount = round(subtotal * VAT_RATE, 2) if vat_registered else 0.0
    total = round(subtotal + vat_amount, 2)
    return subtotal, vat_amount, total


def _effective_status(invoice: Invoice) -> str:
    if invoice.status == "sent" and invoice.due_date < date.today():
        return "overdue"
    return invoice.status


def _to_invoice_out(invoice: Invoice) -> InvoiceOut:
    subtotal, vat_amount, total = _compute_totals(invoice.line_items, invoice.vat_registered)
    return InvoiceOut(
        id=invoice.id,
        invoice_number=invoice.invoice_number,
        contact=ContactOut.model_validate(invoice.contact),
        issue_date=invoice.issue_date,
        due_date=invoice.due_date,
        status=invoice.status,
        effective_status=_effective_status(invoice),
        paid_date=invoice.paid_date,
        notes=invoice.notes,
        vat_registered=invoice.vat_registered,
        line_items=[InvoiceLineItemOut.model_validate(li) for li in invoice.line_items],
        subtotal=subtotal,
        vat_amount=vat_amount,
        total=total,
    )


def _get_or_create_invoice_income(
    db: Session, invoice: Invoice, amount: float, date_received: date, is_approved: bool,
) -> BusinessIncome:
    """The single source of truth for this invoice's income — reactivates and
    updates the existing linked row if one exists (e.g. re-sending after a
    dismiss, or editing a sent invoice's due date) rather than ever creating
    a second one for the same invoice."""
    income = db.query(BusinessIncome).filter_by(invoice_id=invoice.id).first()
    description = f"Invoice {invoice.invoice_number} — {invoice.contact.name}"
    if income is None:
        income = BusinessIncome(
            user_id=invoice.user_id,
            amount=amount,
            date_received=date_received,
            description=description,
            is_active=True,
            is_approved=is_approved,
            recurrence_freq=None,
            invoice_id=invoice.id,
        )
        db.add(income)
    else:
        income.amount = amount
        income.date_received = date_received
        income.is_approved = is_approved
        income.is_active = True
        income.description = description
    return income


def _mark_sent(db: Session, invoice: Invoice, current_user: User) -> None:
    invoice.status = "sent"
    invoice.vat_registered = current_user.vat_registered  # snapshot at send time
    subtotal = _compute_subtotal(invoice.line_items)
    _get_or_create_invoice_income(db, invoice, amount=subtotal, date_received=invoice.due_date, is_approved=False)


def _mark_paid(db: Session, invoice: Invoice, paid_date: date) -> None:
    invoice.status = "paid"
    invoice.paid_date = paid_date
    subtotal = _compute_subtotal(invoice.line_items)
    _get_or_create_invoice_income(db, invoice, amount=subtotal, date_received=paid_date, is_approved=True)


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------

@router.get("/contacts", response_model=list[ContactOut])
def list_contacts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return (
        db.query(Contact)
        .filter_by(user_id=current_user.id, is_active=True)
        .order_by(Contact.name)
        .all()
    )


@router.post("/contacts", response_model=ContactOut, status_code=status.HTTP_201_CREATED)
def create_contact(
    body: ContactCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    contact = Contact(user_id=current_user.id, name=body.name, address=body.address, email=body.email)
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


@router.patch("/contacts/{contact_id}", response_model=ContactOut)
def update_contact(
    contact_id: int, body: ContactUpdate,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    contact = get_owned_or_404(db, Contact, contact_id, current_user.id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(contact, field, value)
    db.commit()
    db.refresh(contact)
    return contact


@router.delete("/contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact(
    contact_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    contact = get_owned_or_404(db, Contact, contact_id, current_user.id)
    contact.is_active = False
    db.commit()


# ---------------------------------------------------------------------------
# Invoices
# ---------------------------------------------------------------------------

@router.get("/invoices", response_model=list[InvoiceOut])
def list_invoices(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    invoices = (
        db.query(Invoice)
        .filter_by(user_id=current_user.id, is_active=True)
        .order_by(Invoice.issue_date.desc(), Invoice.id.desc())
        .all()
    )
    return [_to_invoice_out(inv) for inv in invoices]


@router.post("/invoices", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
def create_invoice(
    body: InvoiceCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    if not body.line_items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one line item is required.")
    for li in body.line_items:
        if li.quantity <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Line item quantity must be greater than zero.")
        if li.unit_price < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Line item unit price cannot be negative.")

    get_owned_or_404(db, Contact, body.contact_id, current_user.id)  # validate ownership

    invoice = Invoice(
        user_id=current_user.id,
        contact_id=body.contact_id,
        invoice_number=_next_invoice_number(db, current_user.id),
        issue_date=body.issue_date,
        due_date=body.due_date,
        notes=body.notes,
        status="draft",
        vat_registered=current_user.vat_registered,
    )
    db.add(invoice)
    db.flush()

    for li in body.line_items:
        db.add(InvoiceLineItem(invoice_id=invoice.id, description=li.description, quantity=li.quantity, unit_price=li.unit_price))
    db.flush()
    db.refresh(invoice)

    if body.status == "sent":
        _mark_sent(db, invoice, current_user)

    db.commit()
    db.refresh(invoice)
    return _to_invoice_out(invoice)


@router.get("/invoices/{invoice_id}", response_model=InvoiceOut)
def get_invoice(
    invoice_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    invoice = get_owned_or_404(db, Invoice, invoice_id, current_user.id)
    return _to_invoice_out(invoice)


@router.patch("/invoices/{invoice_id}", response_model=InvoiceOut)
def update_invoice(
    invoice_id: int, body: InvoiceUpdate,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    invoice = get_owned_or_404(db, Invoice, invoice_id, current_user.id)
    if invoice.status == "paid":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot edit a paid invoice.")

    updates = body.model_dump(exclude_unset=True, exclude={"line_items"})
    if "contact_id" in updates:
        get_owned_or_404(db, Contact, updates["contact_id"], current_user.id)
    for field, value in updates.items():
        setattr(invoice, field, value)

    if body.line_items is not None:
        if not body.line_items:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one line item is required.")
        for li in list(invoice.line_items):
            db.delete(li)
        db.flush()
        for li in body.line_items:
            db.add(InvoiceLineItem(invoice_id=invoice.id, description=li.description, quantity=li.quantity, unit_price=li.unit_price))

    db.commit()
    db.refresh(invoice)

    # Already sent (awaiting payment) — keep the linked income forecast's
    # amount/date in sync with whatever just changed.
    if invoice.status == "sent":
        subtotal = _compute_subtotal(invoice.line_items)
        _get_or_create_invoice_income(db, invoice, amount=subtotal, date_received=invoice.due_date, is_approved=False)
        db.commit()
        db.refresh(invoice)

    return _to_invoice_out(invoice)


@router.delete("/invoices/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_invoice(
    invoice_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    invoice = get_owned_or_404(db, Invoice, invoice_id, current_user.id)
    if invoice.status == "paid":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a paid invoice — it's part of your confirmed income record.",
        )
    invoice.is_active = False
    linked_income = db.query(BusinessIncome).filter_by(invoice_id=invoice.id).first()
    if linked_income is not None:
        linked_income.is_active = False
    db.commit()


@router.post("/invoices/{invoice_id}/send", response_model=InvoiceOut)
def send_invoice(
    invoice_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    invoice = get_owned_or_404(db, Invoice, invoice_id, current_user.id)
    if invoice.status == "paid":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This invoice has already been paid.")
    _mark_sent(db, invoice, current_user)
    db.commit()
    db.refresh(invoice)
    return _to_invoice_out(invoice)


@router.post("/invoices/{invoice_id}/paid", response_model=InvoiceOut)
def mark_invoice_paid(
    invoice_id: int, body: MarkPaidBody,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    invoice = get_owned_or_404(db, Invoice, invoice_id, current_user.id)
    _mark_paid(db, invoice, body.paid_date or date.today())
    db.commit()
    db.refresh(invoice)
    return _to_invoice_out(invoice)


@router.get("/invoices/{invoice_id}/pdf")
def get_invoice_pdf(
    invoice_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    invoice = get_owned_or_404(db, Invoice, invoice_id, current_user.id)
    subtotal, vat_amount, total = _compute_totals(invoice.line_items, invoice.vat_registered)
    pdf_bytes = generate_invoice_pdf(
        invoice=invoice, contact=invoice.contact, user=current_user,
        subtotal=subtotal, vat_amount=vat_amount, total=total,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{invoice.invoice_number}.pdf"'},
    )
