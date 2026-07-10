// Pure functions — no React dependency, safe to import in Node test environment.

/**
 * Returns a plain-English education snippet keyed off class2_status.
 * All monetary figures (NI rates, thresholds) are read from taxConfig.
 * Never shows a specific State Pension amount.
 */
export function class2EducationSnippet(status, taxConfig) {
  if (!taxConfig) return '';

  const spt        = taxConfig.class2_small_profits_threshold;
  const lowerLimit = taxConfig.class4_lower_limit;
  const rate       = taxConfig.class2_weekly_rate;

  // These fields were added to the API schema later; guard against null/undefined
  // so an unseeded or older DB row silently shows nothing rather than crashing.
  if (spt == null || lowerLimit == null || rate == null) return '';

  const annualRate = Math.round(rate * 52);
  const fmtSpt   = spt.toLocaleString('en-GB');
  const fmtLimit = lowerLimit.toLocaleString('en-GB');

  if (status === 'covered') {
    return (
      "Because you're paying Class 4 National Insurance, this tax year automatically " +
      "counts towards your State Pension — there's nothing extra to pay."
    );
  }

  if (status === 'covered_no_class4') {
    return (
      `You're in a good position: your profit is above £${fmtSpt} but below £${fmtLimit}, ` +
      "so you pay no National Insurance, yet this year still counts towards your State Pension."
    );
  }

  if (status === 'below_threshold') {
    return (
      `Your profit is below £${fmtSpt}, so this tax year won't automatically count towards ` +
      `your State Pension. You can pay voluntary Class 2 National Insurance of ` +
      `£${rate}/week (about £${annualRate} a year) to protect it. ` +
      "Whether that's worth it depends on your wider National Insurance record."
    );
  }

  return '';
}

/**
 * Collapsible "What does this mean for my State Pension?" explainer.
 * The 35 and 10 year figures are stable structural rules.
 * Does NOT state a specific State Pension £ amount — see gov.uk for a personal forecast.
 */
export const CLASS2_PENSION_EXPLAINER =
  "The State Pension is built from 'qualifying years' on your National Insurance record. " +
  "You currently need 35 qualifying years for the full new State Pension, and at least 10 to get any of it. " +
  "Each year you contribute or are credited is one building block — gaps can permanently reduce what you " +
  "eventually receive. To see your own forecast based on your actual record, check the official " +
  "State Pension forecast at gov.uk/check-state-pension.";
