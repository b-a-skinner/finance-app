import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { nextOccurrence, getTaxDeadlines, visibleItems, LIST_CAP, TAX_DEADLINE_RULES } from '../utils/upcoming';

// ---------------------------------------------------------------------------
// nextOccurrence
// ---------------------------------------------------------------------------

describe('nextOccurrence', () => {
  it('returns this year when the date is still ahead', () => {
    expect(nextOccurrence(1, 31, '2026-01-15')).toBe('2026-01-31');
    expect(nextOccurrence(7, 31, '2026-02-01')).toBe('2026-07-31');
  });

  it('returns this year on the deadline day itself (not yet passed)', () => {
    expect(nextOccurrence(1, 31, '2026-01-31')).toBe('2026-01-31');
  });

  it('rolls to next year once the date has passed', () => {
    expect(nextOccurrence(1, 31, '2026-02-01')).toBe('2027-01-31');
    expect(nextOccurrence(7, 31, '2026-08-01')).toBe('2027-07-31');
  });

  it('rolls forward across a full year once passed, regardless of starting year', () => {
    expect(nextOccurrence(1, 31, '2027-02-15')).toBe('2028-01-31');
  });
});

// ---------------------------------------------------------------------------
// getTaxDeadlines
// ---------------------------------------------------------------------------

describe('getTaxDeadlines', () => {
  it('returns exactly the filing and payment-on-account deadlines', () => {
    const deadlines = getTaxDeadlines('2026-03-01');
    expect(deadlines.map(d => d.key)).toEqual(['payment-on-account-2', 'self-assessment-filing']);
  });

  it('sorts soonest first', () => {
    const deadlines = getTaxDeadlines('2026-03-01');
    expect(deadlines[0].date).toBe('2026-07-31');
    expect(deadlines[1].date).toBe('2027-01-31');
    for (let i = 1; i < deadlines.length; i++) {
      expect(deadlines[i].date >= deadlines[i - 1].date).toBe(true);
    }
  });

  it('computes forward from the given date, not a hardcoded year', () => {
    expect(getTaxDeadlines('2026-01-01').find(d => d.key === 'self-assessment-filing').date).toBe('2026-01-31');
    expect(getTaxDeadlines('2030-01-01').find(d => d.key === 'self-assessment-filing').date).toBe('2030-01-31');
  });

  it('rolls the filing deadline to next year once 31 January passes', () => {
    expect(getTaxDeadlines('2026-02-01').find(d => d.key === 'self-assessment-filing').date).toBe('2027-01-31');
  });

  it('has plain-English labels and no amount yet (future hook stays null)', () => {
    const deadlines = getTaxDeadlines('2026-03-01');
    for (const d of deadlines) {
      expect(typeof d.label).toBe('string');
      expect(d.label.length).toBeGreaterThan(0);
      expect(d.amount).toBeNull();
    }
  });

  it('rule set is not hardcoded to exactly two — filtering is data-driven via appliesTo', () => {
    expect(TAX_DEADLINE_RULES.length).toBeGreaterThanOrEqual(2);
    expect(TAX_DEADLINE_RULES.every(r => typeof r.appliesTo === 'function')).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// visibleItems (list capping / "Show all (N)")
// ---------------------------------------------------------------------------

describe('visibleItems', () => {
  const items = Array.from({ length: 8 }, (_, i) => ({ id: i }));

  it('caps to LIST_CAP (5) by default', () => {
    const { visible, hasMore, total } = visibleItems(items, false);
    expect(visible).toHaveLength(LIST_CAP);
    expect(hasMore).toBe(true);
    expect(total).toBe(8);
  });

  it('reveals all items when showAll is true', () => {
    const { visible, hasMore } = visibleItems(items, true);
    expect(visible).toHaveLength(8);
    expect(hasMore).toBe(true); // total still exceeds cap; toggle just no longer needed by caller
  });

  it('does not report hasMore when under the cap', () => {
    const short = items.slice(0, 3);
    const { visible, hasMore, total } = visibleItems(short, false);
    expect(visible).toHaveLength(3);
    expect(hasMore).toBe(false);
    expect(total).toBe(3);
  });

  it('respects a custom cap', () => {
    const { visible, hasMore } = visibleItems(items, false, 2);
    expect(visible).toHaveLength(2);
    expect(hasMore).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Upcoming.jsx structure — tax deadlines stay read-only and out of the
// approval/analytics data flow (no component-rendering lib in this project,
// so this mirrors the source-scan convention used for CSS elsewhere in
// this test suite).
// ---------------------------------------------------------------------------

describe('Upcoming.jsx tax deadline rows', () => {
  const src = readFileSync(resolve(__dirname, '../pages/Upcoming.jsx'), 'utf-8');
  const rowMatch = src.match(/function TaxDeadlineRow\([^)]*\)\s*\{([\s\S]*?)\n}\n/);
  const rowBody = rowMatch ? rowMatch[1] : '';

  it('TaxDeadlineRow is found', () => {
    expect(rowBody).not.toBe('');
  });

  it('renders no interactive controls (no buttons, no click handlers)', () => {
    expect(rowBody).not.toMatch(/<button/);
    expect(rowBody).not.toMatch(/onClick/);
  });

  it('has no edit/delete/approve/dismiss affordances', () => {
    expect(rowBody).not.toMatch(/onEdit|onDelete|approve|dismiss|×|✕/i);
  });

  it('taxDeadlines are computed separately from income/expense entries feeding the approval queue', () => {
    const allEntriesMatch = src.match(/const allEntries = \[([\s\S]*?)\];/);
    expect(allEntriesMatch).not.toBeNull();
    expect(allEntriesMatch[1]).not.toMatch(/taxDeadlines/);
  });

  it('Tax deadlines section always renders (not gated on emptiness)', () => {
    const sectionMatch = src.match(/<section className="upcoming-section tax-deadlines-section">/);
    expect(sectionMatch).not.toBeNull();
  });
});

describe('Upcoming.jsx capped section expanders', () => {
  const src = readFileSync(resolve(__dirname, '../pages/Upcoming.jsx'), 'utf-8');

  it('To approve and Scheduled sections are hidden entirely when empty', () => {
    expect(src).toMatch(/\{awaiting\.length > 0 && \(/);
    expect(src).toMatch(/\{scheduled\.length > 0 && \(/);
  });

  it('both sections render a ShowAllToggle guarded by hasMore', () => {
    const toggles = src.match(/hasMore && !showAll\w+ && \(\s*<ShowAllToggle/g) || [];
    expect(toggles.length).toBe(2);
  });
});

describe('.tax-deadline-row CSS', () => {
  const css = readFileSync(resolve(__dirname, '../index.css'), 'utf-8');
  const match = css.match(/\.tax-deadline-row\s*\{([^}]+)\}/);
  const block = match ? match[1] : '';

  it('CSS block is found', () => {
    expect(block).not.toBe('');
  });

  it('is visually distinct from approval/scheduled rows (dashed border, not solid)', () => {
    expect(block).toMatch(/border:\s*1px dashed/);
  });

  const approvalBlock = (css.match(/\.approval-item\s*\{([^}]+)\}/) || [])[1] || '';
  it('does not reuse the approval-item card shadow treatment', () => {
    expect(block).not.toMatch(/box-shadow/);
    expect(approvalBlock).toMatch(/box-shadow/);
  });
});
