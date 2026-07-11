import { describe, it, expect } from 'vitest';
import {
  taxYearRange,
  thisMonthRange,
  getDateBounds,
  applyFilters,
  isFiltered,
  FILTER_DEFAULTS,
} from '../utils/transactionFilters';

// ---------------------------------------------------------------------------
// Helpers to build minimal entry objects
// ---------------------------------------------------------------------------

function income(date, amount = 100, overrides = {}) {
  return { _type: 'income', _date: date, amount, is_allowable: true, ...overrides };
}

function expense(date, category, isAllowable = true, overrides = {}) {
  return { _type: 'expense', _date: date, amount: 50, category, is_allowable: isAllowable, ...overrides };
}

// ---------------------------------------------------------------------------
// taxYearRange
// ---------------------------------------------------------------------------

describe('taxYearRange', () => {
  it('start is always 6 April', () => {
    const { start } = taxYearRange();
    expect(start).toMatch(/-04-06$/);
  });

  it('end is always 5 April of the following year', () => {
    const { start, end } = taxYearRange();
    const startYear = parseInt(start.split('-')[0], 10);
    expect(end).toBe(`${startYear + 1}-04-05`);
  });

  it('start year uses the 6 April boundary', () => {
    const { start } = taxYearRange();
    const startYear = parseInt(start.split('-')[0], 10);
    const now = new Date();
    const y = now.getFullYear();
    const m = now.getMonth() + 1;
    const d = now.getDate();
    const expectedStartYear = (m > 4 || (m === 4 && d >= 6)) ? y : y - 1;
    expect(startYear).toBe(expectedStartYear);
  });

  it('start and end differ by exactly one year', () => {
    const { start, end } = taxYearRange();
    const sy = parseInt(start.split('-')[0], 10);
    const ey = parseInt(end.split('-')[0], 10);
    expect(ey - sy).toBe(1);
  });
});

// ---------------------------------------------------------------------------
// thisMonthRange
// ---------------------------------------------------------------------------

describe('thisMonthRange', () => {
  it('start is the first of the current month', () => {
    const { start } = thisMonthRange();
    expect(start).toMatch(/-01$/);
    const y = new Date().getFullYear();
    const m = String(new Date().getMonth() + 1).padStart(2, '0');
    expect(start).toBe(`${y}-${m}-01`);
  });

  it('end year and month match start', () => {
    const { start, end } = thisMonthRange();
    expect(start.slice(0, 7)).toBe(end.slice(0, 7));
  });
});

// ---------------------------------------------------------------------------
// getDateBounds
// ---------------------------------------------------------------------------

describe('getDateBounds', () => {
  it('all_time returns empty strings', () => {
    expect(getDateBounds({ dateRange: 'all_time', dateFrom: '', dateTo: '' }))
      .toEqual({ start: '', end: '' });
  });

  it('tax_year delegates to taxYearRange', () => {
    const { start, end } = getDateBounds({ dateRange: 'tax_year', dateFrom: '', dateTo: '' });
    const expected = taxYearRange();
    expect(start).toBe(expected.start);
    expect(end).toBe(expected.end);
  });

  it('this_month delegates to thisMonthRange', () => {
    const { start, end } = getDateBounds({ dateRange: 'this_month', dateFrom: '', dateTo: '' });
    const expected = thisMonthRange();
    expect(start).toBe(expected.start);
    expect(end).toBe(expected.end);
  });

  it('custom uses dateFrom and dateTo', () => {
    expect(getDateBounds({ dateRange: 'custom', dateFrom: '2025-01-01', dateTo: '2025-03-31' }))
      .toEqual({ start: '2025-01-01', end: '2025-03-31' });
  });

  it('custom with empty dates returns empty strings', () => {
    expect(getDateBounds({ dateRange: 'custom', dateFrom: '', dateTo: '' }))
      .toEqual({ start: '', end: '' });
  });
});

// ---------------------------------------------------------------------------
// applyFilters — Type filter
// ---------------------------------------------------------------------------

const entries = [
  income('2025-06-01'),
  income('2025-07-01'),
  expense('2025-06-15', 'travel', true),
  expense('2025-07-10', 'equipment', false),
];

describe('applyFilters — type', () => {
  it('all returns every entry', () => {
    expect(applyFilters(entries, { ...FILTER_DEFAULTS })).toHaveLength(4);
  });

  it('income returns only income entries', () => {
    const result = applyFilters(entries, { ...FILTER_DEFAULTS, type: 'income' });
    expect(result).toHaveLength(2);
    expect(result.every(e => e._type === 'income')).toBe(true);
  });

  it('expense returns only expense entries', () => {
    const result = applyFilters(entries, { ...FILTER_DEFAULTS, type: 'expense' });
    expect(result).toHaveLength(2);
    expect(result.every(e => e._type === 'expense')).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// applyFilters — Date range
// ---------------------------------------------------------------------------

describe('applyFilters — date range', () => {
  const mixed = [
    income('2020-01-01'),
    income('2025-06-01'),
    expense('2024-12-31', 'equipment'),
  ];

  it('all_time shows everything', () => {
    expect(applyFilters(mixed, { ...FILTER_DEFAULTS })).toHaveLength(3);
  });

  it('custom date range narrows by start and end', () => {
    const result = applyFilters(mixed, {
      ...FILTER_DEFAULTS,
      dateRange: 'custom',
      dateFrom: '2024-01-01',
      dateTo: '2025-12-31',
    });
    expect(result).toHaveLength(2);
    expect(result.map(e => e._date)).toEqual(['2025-06-01', '2024-12-31']);
  });

  it('custom with only start date filters lower bound', () => {
    const result = applyFilters(mixed, {
      ...FILTER_DEFAULTS,
      dateRange: 'custom',
      dateFrom: '2024-01-01',
      dateTo: '',
    });
    expect(result).toHaveLength(2);
  });

  it('tax_year preset uses 6 Apr boundary (not hardcoded)', () => {
    const { start, end } = taxYearRange();
    const inYear  = income(start);           // first day of tax year
    const outYear = income('2000-01-01');    // ancient, definitely outside
    const result = applyFilters([inYear, outYear], {
      ...FILTER_DEFAULTS, dateRange: 'tax_year',
    });
    expect(result).toContain(inYear);
    expect(result).not.toContain(outYear);
  });

  it('this_month preset includes a date from today\'s month', () => {
    const { start } = thisMonthRange();
    const thisMonth = income(start);
    const old = income('2000-06-01');
    const result = applyFilters([thisMonth, old], {
      ...FILTER_DEFAULTS, dateRange: 'this_month',
    });
    expect(result).toContain(thisMonth);
    expect(result).not.toContain(old);
  });
});

// ---------------------------------------------------------------------------
// applyFilters — Category filter
// ---------------------------------------------------------------------------

describe('applyFilters — category', () => {
  const travelExp = expense('2025-06-01', 'travel');
  const equipExp  = expense('2025-06-02', 'equipment');
  const inc       = income('2025-06-03');

  it('filters expenses by category', () => {
    const result = applyFilters([travelExp, equipExp, inc], {
      ...FILTER_DEFAULTS, category: 'travel',
    });
    expect(result).toContain(travelExp);
    expect(result).not.toContain(equipExp);
  });

  it('income entries pass through when category is set and type=all', () => {
    const result = applyFilters([travelExp, equipExp, inc], {
      ...FILTER_DEFAULTS, category: 'travel',
    });
    expect(result).toContain(inc);
  });

  it('category filter is ignored when type=income', () => {
    const result = applyFilters([travelExp, equipExp, inc], {
      ...FILTER_DEFAULTS, type: 'income', category: 'travel',
    });
    expect(result).toEqual([inc]);
  });

  it('all categories (empty string) shows all expenses', () => {
    const result = applyFilters([travelExp, equipExp], {
      ...FILTER_DEFAULTS, category: '',
    });
    expect(result).toHaveLength(2);
  });
});

// ---------------------------------------------------------------------------
// applyFilters — Allowable filter
// ---------------------------------------------------------------------------

describe('applyFilters — allowable', () => {
  const allowExp    = expense('2025-06-01', 'equipment', true);
  const nonAllowExp = expense('2025-06-02', 'personal', false);
  const inc         = income('2025-06-03');

  it('allowable shows only is_allowable=true expenses', () => {
    const result = applyFilters([allowExp, nonAllowExp, inc], {
      ...FILTER_DEFAULTS, allowable: 'allowable',
    });
    expect(result).toContain(allowExp);
    expect(result).not.toContain(nonAllowExp);
  });

  it('non_allowable shows only is_allowable=false expenses', () => {
    const result = applyFilters([allowExp, nonAllowExp, inc], {
      ...FILTER_DEFAULTS, allowable: 'non_allowable',
    });
    expect(result).toContain(nonAllowExp);
    expect(result).not.toContain(allowExp);
  });

  it('income passes through regardless of allowable filter', () => {
    const result = applyFilters([allowExp, nonAllowExp, inc], {
      ...FILTER_DEFAULTS, allowable: 'allowable',
    });
    expect(result).toContain(inc);
  });

  it('allowable filter ignored when type=income', () => {
    const result = applyFilters([allowExp, nonAllowExp, inc], {
      ...FILTER_DEFAULTS, type: 'income', allowable: 'allowable',
    });
    expect(result).toEqual([inc]);
  });
});

// ---------------------------------------------------------------------------
// Mileage and home office entries filter as allowable expenses
// ---------------------------------------------------------------------------

describe('mileage and home office entries', () => {
  const mileage = expense('2025-06-01', 'travel', true, {
    expense_method: 'mileage', business_miles: 100,
  });
  const flatHO = expense('2025-06-02', 'home_office', true, {
    expense_method: 'home_office_flat',
  });

  it('appear under Type=expense', () => {
    const result = applyFilters([mileage, flatHO], { ...FILTER_DEFAULTS, type: 'expense' });
    expect(result).toHaveLength(2);
  });

  it('appear under category=travel (mileage) and category=home_office (flat)', () => {
    expect(applyFilters([mileage, flatHO], { ...FILTER_DEFAULTS, category: 'travel' }))
      .toContain(mileage);
    expect(applyFilters([mileage, flatHO], { ...FILTER_DEFAULTS, category: 'home_office' }))
      .toContain(flatHO);
  });

  it('appear under allowable=allowable (is_allowable=true)', () => {
    const result = applyFilters([mileage, flatHO], { ...FILTER_DEFAULTS, allowable: 'allowable' });
    expect(result).toHaveLength(2);
  });

  it('excluded by allowable=non_allowable', () => {
    const result = applyFilters([mileage, flatHO], { ...FILTER_DEFAULTS, allowable: 'non_allowable' });
    expect(result).toHaveLength(0);
  });
});

// ---------------------------------------------------------------------------
// Combined filters (AND logic)
// ---------------------------------------------------------------------------

describe('applyFilters — combined (AND logic)', () => {
  const travelAllowable    = expense('2025-06-01', 'travel', true);
  const travelNonAllowable = expense('2025-06-02', 'travel', false);
  const personalAllowable  = expense('2025-06-03', 'personal', false); // personal is always non-allowable
  const inc                = income('2025-06-04');
  const oldTravel          = expense('2018-06-01', 'travel', true);

  it('type=expense + category=travel + allowable=allowable', () => {
    const result = applyFilters(
      [travelAllowable, travelNonAllowable, personalAllowable, inc],
      { ...FILTER_DEFAULTS, type: 'expense', category: 'travel', allowable: 'allowable' },
    );
    expect(result).toEqual([travelAllowable]);
  });

  it('type=expense + custom date range + category', () => {
    const result = applyFilters(
      [travelAllowable, oldTravel, inc],
      {
        ...FILTER_DEFAULTS,
        type: 'expense',
        dateRange: 'custom',
        dateFrom: '2025-01-01',
        dateTo: '2025-12-31',
        category: 'travel',
      },
    );
    expect(result).toEqual([travelAllowable]);
  });

  it('returns empty array when no entries match', () => {
    const result = applyFilters(entries, {
      ...FILTER_DEFAULTS,
      type: 'income',
      dateRange: 'custom',
      dateFrom: '2000-01-01',
      dateTo: '2000-12-31',
    });
    expect(result).toHaveLength(0);
  });
});

// ---------------------------------------------------------------------------
// isFiltered / reset
// ---------------------------------------------------------------------------

describe('isFiltered', () => {
  it('false when all defaults', () => {
    expect(isFiltered({ ...FILTER_DEFAULTS })).toBe(false);
  });

  it('true when type changed', () => {
    expect(isFiltered({ ...FILTER_DEFAULTS, type: 'income' })).toBe(true);
  });

  it('true when dateRange changed', () => {
    expect(isFiltered({ ...FILTER_DEFAULTS, dateRange: 'tax_year' })).toBe(true);
  });

  it('true when category changed', () => {
    expect(isFiltered({ ...FILTER_DEFAULTS, category: 'travel' })).toBe(true);
  });

  it('true when allowable changed', () => {
    expect(isFiltered({ ...FILTER_DEFAULTS, allowable: 'allowable' })).toBe(true);
  });

  it('resetting to FILTER_DEFAULTS makes isFiltered false', () => {
    const active = { ...FILTER_DEFAULTS, type: 'income', category: 'travel' };
    expect(isFiltered(active)).toBe(true);
    expect(isFiltered({ ...FILTER_DEFAULTS })).toBe(false);
  });
});
