import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';
import {
  nextOccurrence, getTaxDeadlines, visibleItems, LIST_CAP, TAX_DEADLINE_RULES,
  attachPoaFigures, poaExplanation, currentTaxYearLabel, mostRecentlyEndedTaxYearLabel,
} from '../utils/upcoming';

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

// ---------------------------------------------------------------------------
// currentTaxYearLabel / mostRecentlyEndedTaxYearLabel
// ---------------------------------------------------------------------------

describe('currentTaxYearLabel', () => {
  it('returns the current tax year on/after 6 April', () => {
    expect(currentTaxYearLabel('2026-04-06')).toBe('2026/27');
    expect(currentTaxYearLabel('2026-07-12')).toBe('2026/27');
  });

  it('returns the prior tax year before 6 April', () => {
    expect(currentTaxYearLabel('2026-04-05')).toBe('2025/26');
    expect(currentTaxYearLabel('2026-01-15')).toBe('2025/26');
  });
});

describe('mostRecentlyEndedTaxYearLabel', () => {
  it('is one year before the current tax year', () => {
    expect(mostRecentlyEndedTaxYearLabel('2026-07-12')).toBe('2025/26');
    expect(mostRecentlyEndedTaxYearLabel('2026-01-15')).toBe('2024/25');
  });
});

// ---------------------------------------------------------------------------
// attachPoaFigures
// ---------------------------------------------------------------------------

describe('attachPoaFigures', () => {
  const baseDeadlines = getTaxDeadlines('2026-03-01');

  it('leaves rows unchanged when poa is null (not yet fetched)', () => {
    const result = attachPoaFigures(baseDeadlines, null);
    expect(result).toEqual(baseDeadlines);
  });

  it('leaves rows unchanged when poa.available is false', () => {
    const poa = { available: false, reason: 'no_completed_year' };
    const result = attachPoaFigures(baseDeadlines, poa);
    expect(result).toEqual(baseDeadlines);
  });

  describe('when POAs are triggered', () => {
    const poa = {
      available: true, last_completed_year: '2025/26', next_year: '2026/27',
      poa_threshold: 1000, bill_lcy: 4531.80, poa_triggered: true,
      poa_instalment: 2265.90, balancing_payment: 4531.80,
      january_total: 6797.70, july_total: 2265.90,
    };
    const result = attachPoaFigures(baseDeadlines, poa);
    const jan = result.find(d => d.key === 'self-assessment-filing');
    const jul = result.find(d => d.key === 'payment-on-account-2');

    it('January shows the combined total', () => {
      expect(jan.amount).toBe(6797.70);
    });

    it('January label names both components', () => {
      expect(jan.label).toContain('Balancing payment for 2025/26');
      expect(jan.label).toContain('first payment on account for 2026/27');
    });

    it('January breaks out the two components with their own amounts', () => {
      expect(jan.breakdown).toEqual([
        { label: 'Balancing payment for 2025/26', amount: 4531.80 },
        { label: 'First payment on account for 2026/27', amount: 2265.90 },
      ]);
    });

    it('July shows the second instalment', () => {
      expect(jul.label).toContain('Second payment on account for 2026/27');
      expect(jul.amount).toBe(2265.90);
    });
  });

  describe('when the bill is under threshold (no POAs)', () => {
    const poa = {
      available: true, last_completed_year: '2025/26', next_year: '2026/27',
      poa_threshold: 1000, bill_lcy: 800, poa_triggered: false,
      poa_instalment: 0, balancing_payment: 800,
      january_total: 800, july_total: 0,
    };
    const result = attachPoaFigures(baseDeadlines, poa);
    const jan = result.find(d => d.key === 'self-assessment-filing');
    const jul = result.find(d => d.key === 'payment-on-account-2');

    it('January shows just the balancing payment, no breakdown', () => {
      expect(jan.amount).toBe(800);
      expect(jan.breakdown).toBeNull();
      expect(jan.label).not.toContain('payment on account');
    });

    it('July shows zero — nothing due', () => {
      expect(jul.amount).toBe(0);
    });
  });
});

// ---------------------------------------------------------------------------
// poaExplanation
// ---------------------------------------------------------------------------

describe('poaExplanation', () => {
  it('returns null when poa has not been fetched yet', () => {
    expect(poaExplanation(null, '2026-07-12')).toBeNull();
  });

  it('explains no-completed-year honestly, naming a target year, without inventing figures', () => {
    const text = poaExplanation({ available: false, reason: 'no_completed_year' }, '2026-07-12');
    expect(text).toContain('2025/26');
    expect(text).toContain("We need a full tax year");
    expect(text).not.toMatch(/£\d/); // no invented amount
  });

  it('explains missing config for a known LCY', () => {
    const text = poaExplanation({ available: false, reason: 'config_missing', last_completed_year: '2025/26' }, '2026-07-12');
    expect(text).toContain('2025/26');
  });

  it('explains the January total plainly when POAs are triggered', () => {
    const poa = {
      available: true, last_completed_year: '2025/26', next_year: '2026/27',
      poa_threshold: 1000, poa_triggered: true, poa_instalment: 2265.90, balancing_payment: 4531.80,
    };
    const text = poaExplanation(poa, '2026-07-12');
    expect(text).toContain('2025/26');
    expect(text).toContain('2026/27');
    expect(text).toContain('Payments on account');
    expect(text).toContain("Based on the 2025/26 income and expenses you've entered.");
  });

  it('explains the under-£1,000 case without showing nothing', () => {
    const poa = {
      available: true, last_completed_year: '2025/26', next_year: '2026/27',
      poa_threshold: 1000, poa_triggered: false, poa_instalment: 0, balancing_payment: 800,
    };
    const text = poaExplanation(poa, '2026-07-12');
    expect(text).toContain('under');
    expect(text).toContain("you don't need to make payments on account");
    expect(text).toContain('2026/27');
    expect(text).toContain("Based on the 2025/26 income and expenses you've entered.");
  });

  it('always includes the partial-data caveat whenever figures are shown', () => {
    const triggered = poaExplanation({
      available: true, last_completed_year: '2024/25', next_year: '2025/26',
      poa_threshold: 1000, poa_triggered: true, poa_instalment: 100, balancing_payment: 100,
    }, '2026-07-12');
    const underThreshold = poaExplanation({
      available: true, last_completed_year: '2024/25', next_year: '2025/26',
      poa_threshold: 1000, poa_triggered: false, poa_instalment: 0, balancing_payment: 100,
    }, '2026-07-12');
    expect(triggered).toContain('Based on the 2024/25 income and expenses');
    expect(underThreshold).toContain('Based on the 2024/25 income and expenses');
  });
});
