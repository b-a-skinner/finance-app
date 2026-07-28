import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';
import {
  computeTotals, statusLabel, daysOverdue, chaseMessage, isBankDetailsIncomplete, VAT_RATE,
} from '../utils/invoices';

// ---------------------------------------------------------------------------
// computeTotals — mirrors the backend exactly (subtotal / VAT / total)
// ---------------------------------------------------------------------------

describe('computeTotals', () => {
  it('subtotal is the sum of quantity × unit_price across all line items', () => {
    const { subtotal } = computeTotals([
      { quantity: 1, unit_price: 200 },
      { quantity: 1, unit_price: 1000 },
    ], false);
    expect(subtotal).toBe(1200);
  });

  it('adds 20% VAT when vatRegistered is true', () => {
    const { subtotal, vatAmount, total } = computeTotals([{ quantity: 1, unit_price: 1000 }], true);
    expect(subtotal).toBe(1000);
    expect(vatAmount).toBe(200);
    expect(total).toBe(1200);
    expect(VAT_RATE).toBe(0.20);
  });

  it('no VAT line/amount when vatRegistered is false', () => {
    const { vatAmount, total, subtotal } = computeTotals([{ quantity: 1, unit_price: 1000 }], false);
    expect(vatAmount).toBe(0);
    expect(total).toBe(subtotal);
  });

  it('handles fractional quantities (e.g. hours)', () => {
    const { subtotal } = computeTotals([{ quantity: 1.5, unit_price: 100 }], false);
    expect(subtotal).toBe(150);
  });

  it('ignores non-numeric/blank rows gracefully (mid-edit state)', () => {
    const { subtotal } = computeTotals([{ quantity: '', unit_price: '' }, { quantity: 2, unit_price: 10 }], false);
    expect(subtotal).toBe(20);
  });

  it('rounds to 2dp', () => {
    const { subtotal, vatAmount } = computeTotals([{ quantity: 3, unit_price: 33.333 }], true);
    expect(subtotal).toBe(100);
    expect(vatAmount).toBe(20);
  });
});

// ---------------------------------------------------------------------------
// statusLabel / daysOverdue
// ---------------------------------------------------------------------------

describe('statusLabel', () => {
  it('capitalises each known status', () => {
    expect(statusLabel('draft')).toBe('Draft');
    expect(statusLabel('sent')).toBe('Sent');
    expect(statusLabel('paid')).toBe('Paid');
    expect(statusLabel('overdue')).toBe('Overdue');
  });
});

describe('daysOverdue', () => {
  it('computes whole days between due date and today', () => {
    expect(daysOverdue('2026-07-01', '2026-07-08')).toBe(7);
  });

  it('is zero when due today', () => {
    expect(daysOverdue('2026-07-08', '2026-07-08')).toBe(0);
  });
});

// ---------------------------------------------------------------------------
// chaseMessage — plain, professional, friendly reminder text. No auto-send:
// this is purely a string the user copies themselves.
// ---------------------------------------------------------------------------

describe('chaseMessage', () => {
  const invoice = {
    invoice_number: 'INV-003', contact: { name: 'Glow Cosmetics' },
    due_date: '2026-07-01', total: 1200,
  };

  it('names the invoice, the client, and the amount', () => {
    const text = chaseMessage(invoice, '2026-07-10');
    expect(text).toContain('INV-003');
    expect(text).toContain('Glow Cosmetics');
    expect(text).toContain('£1,200.00');
  });

  it('mentions how many days overdue', () => {
    const text = chaseMessage(invoice, '2026-07-10');
    expect(text).toContain('9 days overdue');
  });

  it('reads as polite and professional, not demanding', () => {
    const text = chaseMessage(invoice, '2026-07-10');
    expect(text).toMatch(/hi|hope you're well/i);
    expect(text).not.toMatch(/pay now|overdue notice|final demand/i);
  });

  it('is just a string — never triggers any network call itself', () => {
    // Purely a formatting function; the module has no fetch/apiFetch usage at all.
    const src = readFileSync(resolve(__dirname, '../utils/invoices.js'), 'utf-8');
    expect(src).not.toMatch(/fetch\(/);
  });
});

// ---------------------------------------------------------------------------
// isBankDetailsIncomplete — drives the "add your bank details" nudge
// ---------------------------------------------------------------------------

describe('isBankDetailsIncomplete', () => {
  it('true when profile is null (not yet loaded)', () => {
    expect(isBankDetailsIncomplete(null)).toBe(false);
  });

  it('true when any of the three bank fields is missing', () => {
    expect(isBankDetailsIncomplete({ bank_account_name: 'A', bank_sort_code: null, bank_account_number: '123' })).toBe(true);
  });

  it('false only when all three bank fields are present', () => {
    expect(isBankDetailsIncomplete({ bank_account_name: 'A', bank_sort_code: '12-34-56', bank_account_number: '123' })).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// Source-scan checks — wiring that a pure-function test can't cover directly.
// ---------------------------------------------------------------------------

describe('InvoiceForm.jsx never auto-sends the chase message', () => {
  const src = readFileSync(resolve(__dirname, '../pages/InvoiceForm.jsx'), 'utf-8');

  it('renders the reminder as a read-only textarea with a copy button, not a send action', () => {
    expect(src).toMatch(/chaseMessage/);
    expect(src).toMatch(/Copy message/);
    expect(src).not.toMatch(/send.{0,20}chase|chase.{0,20}send/i);
  });
});

describe('Invoices.jsx surfaces overdue invoices with a chase prompt', () => {
  const src = readFileSync(resolve(__dirname, '../pages/Invoices.jsx'), 'utf-8');

  it('filters for effective_status overdue', () => {
    expect(src).toMatch(/effective_status === 'overdue'/);
  });

  it('renders a Chase action', () => {
    expect(src).toMatch(/Chase/);
  });
});

describe('Business.jsx dashboard surfaces overdue invoices', () => {
  const src = readFileSync(resolve(__dirname, '../pages/Business.jsx'), 'utf-8');

  it('fetches invoices and filters for overdue', () => {
    expect(src).toMatch(/\/api\/business\/invoices/);
    expect(src).toMatch(/effective_status === 'overdue'/);
  });

  it('links through to the invoices page', () => {
    expect(src).toMatch(/to="\/invoices"/);
  });
});

describe('InvoiceForm.jsx nudges for missing bank details without hard-blocking', () => {
  const src = readFileSync(resolve(__dirname, '../pages/InvoiceForm.jsx'), 'utf-8');

  it('shows a banner when bank details are incomplete', () => {
    expect(src).toMatch(/isBankDetailsIncomplete/);
    expect(src).toMatch(/bank details/i);
  });

  it('does not disable the save buttons based on bank details', () => {
    const saveButtonsBlock = src.match(/Save as draft[\s\S]{0,400}/)?.[0] ?? '';
    expect(saveButtonsBlock).not.toMatch(/bankMissing/);
  });
});

describe('BusinessProfile.jsx VAT number only required when VAT registered', () => {
  const src = readFileSync(resolve(__dirname, '../pages/BusinessProfile.jsx'), 'utf-8');

  it('VAT number field is conditionally rendered on vat_registered', () => {
    expect(src).toMatch(/invoicing\.vat_registered\s*&&[\s\S]{0,80}inv-vat-number/);
  });

  it('client-side validation blocks saving VAT-registered without a number', () => {
    expect(src).toMatch(/vat_registered[\s\S]{0,60}!invoicing\.vat_number/);
  });
});

describe('.badge-invoice-* CSS reflects each status distinctly', () => {
  const css = readFileSync(resolve(__dirname, '../index.css'), 'utf-8');

  it('draft, sent, paid, and overdue each have a distinct rule', () => {
    for (const status of ['draft', 'sent', 'paid', 'overdue']) {
      expect(css).toMatch(new RegExp(`\\.badge-invoice-${status}\\s*\\{`));
    }
  });

  it('paid uses the positive/green token and overdue uses the negative/red token', () => {
    const paidBlock = css.match(/\.badge-invoice-paid\s*\{([^}]+)\}/)[1];
    const overdueBlock = css.match(/\.badge-invoice-overdue\s*\{([^}]+)\}/)[1];
    expect(paidBlock).toMatch(/--color-positive/);
    expect(overdueBlock).toMatch(/--color-negative/);
  });
});
