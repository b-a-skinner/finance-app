// Pure helpers for the Business dashboard's tax-year selector. No React deps — fully unit-testable.

// "Set aside" implies money still being accrued — wrong once a tax year has closed and
// the bill is simply owed, so completed years get a "due" label instead.
export function taxCardLabel(summary) {
  return summary.is_complete ? `Tax due for ${summary.tax_year}` : 'Set aside for your tax bill';
}

// The selector must always include whichever year is currently on screen, even if it
// has no confirmed entries yet (e.g. the current tax year, freshly started), while
// otherwise only offering years the user actually has data in.
export function yearSelectorOptions(selectedYear, years) {
  return Array.from(new Set([selectedYear, ...years].filter(Boolean)))
    .sort((a, b) => b.localeCompare(a));
}
