// Pure helpers for invoicing. No React deps — fully unit-testable.

// Mirrors backend VAT_RATE (app/schemas.py) — kept in sync manually since
// it's a UK-statutory constant, not user- or year-configurable in v1.
export const VAT_RATE = 0.20;

// Client-side totals preview while editing an invoice, before the backend
// has computed anything — must match backend/app/routes/invoices.py exactly.
export function computeTotals(lineItems, vatRegistered) {
  const subtotal = round2(lineItems.reduce((sum, li) => sum + (Number(li.quantity) || 0) * (Number(li.unit_price) || 0), 0));
  const vatAmount = vatRegistered ? round2(subtotal * VAT_RATE) : 0;
  const total = round2(subtotal + vatAmount);
  return { subtotal, vatAmount, total };
}

function round2(n) {
  return Math.round((n + Number.EPSILON) * 100) / 100;
}

export const STATUS_LABELS = {
  draft: 'Draft',
  sent: 'Sent',
  paid: 'Paid',
  overdue: 'Overdue',
};

export function statusLabel(effectiveStatus) {
  return STATUS_LABELS[effectiveStatus] ?? effectiveStatus;
}

// Whole days between dueDate (YYYY-MM-DD) and todayStr (YYYY-MM-DD). Assumes
// dueDate is in the past (caller should already know effective_status === 'overdue').
export function daysOverdue(dueDate, todayStr) {
  const due = new Date(dueDate + 'T00:00:00Z');
  const today = new Date(todayStr + 'T00:00:00Z');
  return Math.max(0, Math.round((today - due) / 86400000));
}

// Plain-English, friendly, professional reminder the user can copy and send
// themselves — this app never sends anything to the client on its own.
export function chaseMessage(invoice, todayStr) {
  const days = daysOverdue(invoice.due_date, todayStr);
  const dueDateLabel = formatDateForMessage(invoice.due_date);
  return `Hi ${invoice.contact.name},

I hope you're well! Just a friendly reminder that invoice ${invoice.invoice_number} ` +
    `(${gbp(invoice.total)}) was due on ${dueDateLabel}${days > 0 ? ` and is now ${days} day${days === 1 ? '' : 's'} overdue` : ''}.

Could you let me know when I might expect payment? Happy to resend the invoice or answer any questions.

Thanks so much,`;
}

function formatDateForMessage(iso) {
  return new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'long', year: 'numeric' }).format(new Date(iso));
}

function gbp(n) {
  return new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' }).format(n);
}

// Whether the invoice-creation "add your bank details" nudge should show —
// a soft prompt, not a hard block (bank details are optional at the profile
// level, but an invoice without them can't actually be paid).
export function isBankDetailsIncomplete(profile) {
  if (!profile) return false;
  return !(profile.bank_account_name && profile.bank_sort_code && profile.bank_account_number);
}
