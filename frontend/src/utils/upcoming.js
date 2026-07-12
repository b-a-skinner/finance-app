// Pure helpers for the Upcoming page. No React deps — fully unit-testable.
import { gbp } from './format';

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
// Payments on account / balancing payment — real figures attached to the two
// date rows above once a completed tax year's finalised bill is known. The
// arithmetic itself lives entirely in the backend (reusing the year-aware tax
// engine); this module only shapes the numbers for display.
// ---------------------------------------------------------------------------

// The UK tax year (6 April – 5 April) that `fromDate` (YYYY-MM-DD) falls in, as "YYYY/YY".
export function currentTaxYearLabel(fromDate) {
  const [y, m, d] = fromDate.split('-').map(Number);
  const startYear = (m > 4 || (m === 4 && d >= 6)) ? y : y - 1;
  return `${startYear}/${String(startYear + 1).slice(2)}`;
}

// The most recently ENDED tax year as of fromDate — used to name a target year in the
// "add your figures" prompt even when the user has no completed-year data yet.
export function mostRecentlyEndedTaxYearLabel(fromDate) {
  const priorStart = Number(currentTaxYearLabel(fromDate).split('/')[0]) - 1;
  return `${priorStart}/${String(priorStart + 1).slice(2)}`;
}

// Attaches POA/balancing figures (from GET /api/business/tax-deadlines) to the January
// and July deadline rows produced by getTaxDeadlines(). Rows for any other/future
// conditional deadline (e.g. 5 October) pass through unchanged.
export function attachPoaFigures(deadlines, poa) {
  return deadlines.map(d => {
    if (d.key === 'self-assessment-filing') return _attachJanuaryFigures(d, poa);
    if (d.key === 'payment-on-account-2')    return _attachJulyFigures(d, poa);
    return d;
  });
}

function _attachJanuaryFigures(deadline, poa) {
  if (!poa || !poa.available) return deadline;
  const label = poa.poa_triggered
    ? `Balancing payment for ${poa.last_completed_year} + first payment on account for ${poa.next_year}`
    : `Balancing payment for ${poa.last_completed_year}`;
  const breakdown = poa.poa_triggered
    ? [
        { label: `Balancing payment for ${poa.last_completed_year}`, amount: poa.balancing_payment },
        { label: `First payment on account for ${poa.next_year}`, amount: poa.poa_instalment },
      ]
    : null;
  return { ...deadline, label, amount: poa.january_total, breakdown };
}

function _attachJulyFigures(deadline, poa) {
  if (!poa || !poa.available) return deadline;
  return { ...deadline, label: `Second payment on account for ${poa.next_year}`, amount: poa.july_total };
}

// Plain-English paragraph shown under the Tax deadlines rows. Returns null when there's
// nothing informative to add (no poa object fetched yet).
export function poaExplanation(poa, fromDate) {
  if (!poa) return null;

  if (!poa.available) {
    if (poa.reason === 'no_completed_year') {
      const targetYear = mostRecentlyEndedTaxYearLabel(fromDate);
      return `We need a full tax year of your income and expenses to work out what you owe in January. Add your ${targetYear} figures to see your tax bill and payments on account.`;
    }
    if (poa.reason === 'config_missing') {
      return `We don't have tax rates for ${poa.last_completed_year} yet, so we can't calculate your tax bill.`;
    }
    return null;
  }

  const caveat = `Based on the ${poa.last_completed_year} income and expenses you've entered.`;
  const threshold = gbp(poa.poa_threshold);

  if (poa.poa_triggered) {
    return `This January you'll pay your ${poa.last_completed_year} tax bill of ${gbp(poa.balancing_payment)}, plus `
      + `${gbp(poa.poa_instalment)} as an advance payment towards ${poa.next_year}. Payments on account are how HMRC `
      + `collects next year's tax in advance — they catch a lot of people out in their first year. ${caveat}`;
  }

  return `Your ${poa.last_completed_year} tax bill is under ${threshold}, so you don't need to make payments on `
    + `account. You'll just pay your bill in January. If ${poa.next_year}'s bill exceeds ${threshold}, payments on `
    + `account will start then. ${caveat}`;
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
