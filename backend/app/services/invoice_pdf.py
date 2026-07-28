"""
Generates a clean, professional invoice PDF using ReportLab (pure Python,
no system dependencies — safe to deploy anywhere with no extra buildpack
config). This is a document a user sends to a real client with their name on
it, so the layout is deliberately conventional: sender top-left, invoice
number/dates top-right, "Bill to" below, a line-items table, totals aligned
under the table, then payment details. Built-in Helvetica only — no external
font files to ship or go missing at deploy time.
"""
from datetime import date
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Matches the web app's design tokens (frontend/src/index.css :root) so the
# PDF feels like part of the same product, not a bolted-on afterthought.
COLOR_PRIMARY = colors.HexColor("#1a3a5c")
COLOR_TEXT = colors.HexColor("#111827")
COLOR_MUTED = colors.HexColor("#6b7280")
COLOR_BORDER = colors.HexColor("#e5e7eb")
COLOR_HEADER_TEXT = colors.white

_STYLES = {
    "invoice_title": ParagraphStyle(
        "invoice_title", fontName="Helvetica-Bold", fontSize=22, textColor=COLOR_PRIMARY, leading=26,
    ),
    "meta_label": ParagraphStyle(
        "meta_label", fontName="Helvetica", fontSize=9, textColor=COLOR_MUTED, leading=13,
    ),
    "meta_value": ParagraphStyle(
        "meta_value", fontName="Helvetica-Bold", fontSize=9, textColor=COLOR_TEXT, leading=13, alignment=2,
    ),
    "block_heading": ParagraphStyle(
        "block_heading", fontName="Helvetica-Bold", fontSize=8, textColor=COLOR_MUTED, leading=11, spaceAfter=4,
    ),
    "body": ParagraphStyle(
        "body", fontName="Helvetica", fontSize=10, textColor=COLOR_TEXT, leading=14,
    ),
    "body_bold": ParagraphStyle(
        "body_bold", fontName="Helvetica-Bold", fontSize=10.5, textColor=COLOR_TEXT, leading=14,
    ),
    "muted": ParagraphStyle(
        "muted", fontName="Helvetica", fontSize=9, textColor=COLOR_MUTED, leading=13,
    ),
    "table_header": ParagraphStyle(
        "table_header", fontName="Helvetica-Bold", fontSize=9, textColor=COLOR_HEADER_TEXT, leading=12,
    ),
    "table_cell": ParagraphStyle(
        "table_cell", fontName="Helvetica", fontSize=9.5, textColor=COLOR_TEXT, leading=13,
    ),
    "table_cell_right": ParagraphStyle(
        "table_cell_right", fontName="Helvetica", fontSize=9.5, textColor=COLOR_TEXT, leading=13, alignment=2,
    ),
    "totals_label": ParagraphStyle(
        "totals_label", fontName="Helvetica", fontSize=9.5, textColor=COLOR_MUTED, leading=14, alignment=2,
    ),
    "totals_value": ParagraphStyle(
        "totals_value", fontName="Helvetica", fontSize=9.5, textColor=COLOR_TEXT, leading=14, alignment=2,
    ),
    "totals_label_final": ParagraphStyle(
        "totals_label_final", fontName="Helvetica-Bold", fontSize=11, textColor=COLOR_TEXT, leading=16, alignment=2,
    ),
    "totals_value_final": ParagraphStyle(
        "totals_value_final", fontName="Helvetica-Bold", fontSize=11, textColor=COLOR_PRIMARY, leading=16, alignment=2,
    ),
}


def _gbp(amount: float) -> str:
    return f"£{amount:,.2f}"


def _fmt_date(d: date) -> str:
    return d.strftime("%-d %b %Y")


def _p(text: str, style_key: str) -> Paragraph:
    return Paragraph(text, _STYLES[style_key])


def _address_lines(address: str | None) -> list[str]:
    if not address:
        return []
    return [line.strip() for line in address.replace("\r\n", "\n").split("\n") if line.strip()]


def generate_invoice_pdf(invoice, contact, user, subtotal: float, vat_amount: float, total: float) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=20 * mm, bottomMargin=20 * mm, leftMargin=20 * mm, rightMargin=20 * mm,
        title=f"Invoice {invoice.invoice_number}",
    )
    story = []

    # ---- Header: sender (left) + INVOICE title & meta (right) ----
    sender_lines = []
    if user.business_name:
        sender_lines.append(_p(user.business_name, "body_bold"))
    elif user.first_name:
        sender_lines.append(_p(user.first_name, "body_bold"))
    for line in _address_lines(user.business_address):
        sender_lines.append(_p(line, "body"))
    if user.vat_registered and user.vat_number:
        sender_lines.append(Spacer(1, 3))
        sender_lines.append(_p(f"VAT registration: {user.vat_number}", "muted"))
    if not sender_lines:
        sender_lines = [_p(user.email, "body")]

    meta_rows = [
        [_p("Invoice number", "meta_label"), _p(invoice.invoice_number, "meta_value")],
        [_p("Issue date", "meta_label"), _p(_fmt_date(invoice.issue_date), "meta_value")],
        [_p("Due date", "meta_label"), _p(_fmt_date(invoice.due_date), "meta_value")],
    ]
    meta_table = Table(meta_rows, colWidths=[28 * mm, 32 * mm])
    meta_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
    ]))

    right_col = [_p("INVOICE", "invoice_title"), Spacer(1, 8), meta_table]

    header_table = Table([[sender_lines, right_col]], colWidths=[95 * mm, 60 * mm])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 10 * mm))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_BORDER))
    story.append(Spacer(1, 8 * mm))

    # ---- Bill to ----
    story.append(_p("BILL TO", "block_heading"))
    story.append(_p(contact.name, "body_bold"))
    for line in _address_lines(contact.address):
        story.append(_p(line, "body"))
    story.append(Spacer(1, 8 * mm))

    # ---- Line items table ----
    header_row = [
        _p("Description", "table_header"), _p("Qty", "table_header"),
        _p("Unit price", "table_header"), _p("Total", "table_header"),
    ]
    rows = [header_row]
    for item in invoice.line_items:
        line_total = round(item.quantity * item.unit_price, 2)
        qty_str = f"{item.quantity:g}"
        rows.append([
            _p(item.description, "table_cell"),
            _p(qty_str, "table_cell_right"),
            _p(_gbp(item.unit_price), "table_cell_right"),
            _p(_gbp(line_total), "table_cell_right"),
        ])

    items_table = Table(rows, colWidths=[80 * mm, 20 * mm, 27.5 * mm, 27.5 * mm], repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRIMARY),
        ("TOPPADDING", (0, 0), (-1, 0), 7),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 7),
        ("TOPPADDING", (0, 1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 1), (-1, -2), 0.5, COLOR_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    items_table.setStyle(TableStyle(style))
    story.append(items_table)
    story.append(Spacer(1, 6 * mm))

    # ---- Totals ----
    totals_rows = [[_p("Subtotal", "totals_label"), _p(_gbp(subtotal), "totals_value")]]
    if invoice.vat_registered:
        totals_rows.append([_p("VAT (20%)", "totals_label"), _p(_gbp(vat_amount), "totals_value")])
    totals_rows.append([_p("Total due", "totals_label_final"), _p(_gbp(total), "totals_value_final")])

    totals_table = Table(totals_rows, colWidths=[100 * mm, 55 * mm])
    totals_table.setStyle(TableStyle([
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEABOVE", (0, -1), (-1, -1), 0.75, COLOR_BORDER),
        ("TOPPADDING", (0, -1), (-1, -1), 6),
    ]))
    story.append(totals_table)
    story.append(Spacer(1, 10 * mm))

    # ---- Payment details ----
    has_bank_details = user.bank_account_name or user.bank_sort_code or user.bank_account_number
    if has_bank_details:
        story.append(HRFlowable(width="100%", thickness=1, color=COLOR_BORDER))
        story.append(Spacer(1, 6 * mm))
        story.append(_p("PAYMENT DETAILS", "block_heading"))
        if user.bank_account_name:
            story.append(_p(f"Account name: {user.bank_account_name}", "body"))
        if user.bank_sort_code:
            story.append(_p(f"Sort code: {user.bank_sort_code}", "body"))
        if user.bank_account_number:
            story.append(_p(f"Account number: {user.bank_account_number}", "body"))
        story.append(Spacer(1, 8 * mm))

    # ---- Notes ----
    if invoice.notes:
        story.append(_p("NOTES", "block_heading"))
        for line in _address_lines(invoice.notes):
            story.append(_p(line, "body"))

    doc.build(story)
    return buf.getvalue()
