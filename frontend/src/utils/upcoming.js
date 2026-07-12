// Pure helpers for the Upcoming page. No React deps — fully unit-testable.

// ---------------------------------------------------------------------------
// Tax deadlines
// ---------------------------------------------------------------------------
// Fixed-calendar UK Self Assessment deadlines. Each rule is date-only for now;
// `amount` stays null until payment-on-account figures are wired up later.
// `appliesTo` is a hook for future conditional deadlines (e.g. the 5 October
// registration deadline, which only applies in a user's first year of
// self-employment) — always true today, so every rule below applies to
// everyone.
export const TAX_DEADLINE_RULES = [
  {
    key: 'self-assessment-filing',
    month: 1,
    day: 31,
    label: 'Self Assessment: file your return and pay your tax bill',
    appliesTo: () => true,
  },
  {
    key: 'payment-on-account-2',
    month: 7,
    day: 31,
    label: 'Self Assessment: second payment on account due',
    appliesTo: () => true,
  },
];

// Next YYYY-MM-DD occurrence of an annual month/day, on or after fromDate (YYYY-MM-DD).
export function nextOccurrence(month, day, fromDate) {
  const [fy, fm, fd] = fromDate.split('-').map(Number);
  const isPast = fm > month || (fm === month && fd > day);
  const year = isPast ? fy + 1 : fy;
  return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
}

// Returns the next occurrence of every applicable deadline rule, sorted soonest first.
// `context` is passed to each rule's `appliesTo` so future conditional rules (e.g. based
// on a user's self-employment start date) can filter without changing this function.
export function getTaxDeadlines(fromDate, context = {}) {
  return TAX_DEADLINE_RULES
    .filter(rule => rule.appliesTo(context))
    .map(rule => ({
      key: rule.key,
      date: nextOccurrence(rule.month, rule.day, fromDate),
      label: rule.label,
      amount: null, // hook for future payment-on-account figures
    }))
    .sort((a, b) => a.date.localeCompare(b.date));
}

// ---------------------------------------------------------------------------
// List capping ("Show all (N)")
// ---------------------------------------------------------------------------

export const LIST_CAP = 5;

// Items to actually render for a capped section, plus whether a "Show all" toggle is needed.
export function visibleItems(items, showAll, cap = LIST_CAP) {
  return {
    visible: showAll ? items : items.slice(0, cap),
    hasMore: items.length > cap,
    total: items.length,
  };
}
