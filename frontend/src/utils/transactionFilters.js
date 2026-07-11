// Pure filter helpers for the Transactions list. No React deps — fully unit-testable.

// Mirrors backend _tax_year_start / _tax_year_end: UK tax year runs 6 Apr – 5 Apr.
export function taxYearRange() {
  const now = new Date();
  const y = now.getFullYear();
  const m = now.getMonth() + 1; // 1-indexed
  const d = now.getDate();
  const startYear = (m > 4 || (m === 4 && d >= 6)) ? y : y - 1;
  return { start: `${startYear}-04-06`, end: `${startYear + 1}-04-05` };
}

export function thisMonthRange() {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, '0');
  const last = String(new Date(y, now.getMonth() + 1, 0).getDate()).padStart(2, '0');
  return { start: `${y}-${m}-01`, end: `${y}-${m}-${last}` };
}

export function getDateBounds(filters) {
  if (filters.dateRange === 'tax_year')   return taxYearRange();
  if (filters.dateRange === 'this_month') return thisMonthRange();
  if (filters.dateRange === 'custom')     return { start: filters.dateFrom || '', end: filters.dateTo || '' };
  return { start: '', end: '' }; // all_time
}

export const FILTER_DEFAULTS = {
  type:      'all',
  dateRange: 'all_time',
  dateFrom:  '',
  dateTo:    '',
  category:  '',
  allowable: 'all',
};

// Applies all four filters to an array of transaction entries (AND logic).
// Entries must have: _type ('income'|'expense'), _date (YYYY-MM-DD),
// category (expenses), is_allowable (expenses).
export function applyFilters(entries, filters) {
  let result = entries;

  // 1. Type
  if (filters.type !== 'all') {
    result = result.filter(e =>
      filters.type === 'income' ? e._type === 'income' : e._type === 'expense'
    );
  }

  // 2. Date range
  const { start, end } = getDateBounds(filters);
  if (start) result = result.filter(e => e._date >= start);
  if (end)   result = result.filter(e => e._date <= end);

  // 3. Category (only narrows expense entries; income passes through)
  if (filters.category && filters.type !== 'income') {
    result = result.filter(e => e._type === 'income' || e.category === filters.category);
  }

  // 4. Allowable (only narrows expense entries; income passes through)
  if (filters.allowable !== 'all' && filters.type !== 'income') {
    result = result.filter(e => {
      if (e._type === 'income') return true;
      return filters.allowable === 'allowable' ? e.is_allowable : !e.is_allowable;
    });
  }

  return result;
}

// True when any filter differs from its default value.
export function isFiltered(filters) {
  return (
    filters.type      !== FILTER_DEFAULTS.type      ||
    filters.dateRange !== FILTER_DEFAULTS.dateRange  ||
    filters.category  !== FILTER_DEFAULTS.category   ||
    filters.allowable !== FILTER_DEFAULTS.allowable
  );
}
