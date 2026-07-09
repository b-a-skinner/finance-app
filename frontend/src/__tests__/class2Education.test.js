import { describe, it, expect } from 'vitest';
import { class2EducationSnippet, CLASS2_PENSION_EXPLAINER } from '../utils/class2Education';

const BASE_CONFIG = {
  class2_small_profits_threshold: 7105,
  class2_weekly_rate: 3.65,
  class4_lower_limit: 12570,
  class4_upper_limit: 50270,
  class4_main_rate: 0.06,
  class4_upper_rate: 0.02,
};

// ---------------------------------------------------------------------------
// Per-status snippets
// ---------------------------------------------------------------------------

describe('class2EducationSnippet — covered', () => {
  const text = class2EducationSnippet('covered', BASE_CONFIG);

  it('mentions Class 4', () => {
    expect(text).toContain('Class 4');
  });

  it('says the year counts towards State Pension', () => {
    expect(text).toContain('State Pension');
    expect(text).toContain('counts towards');
  });

  it('says nothing extra to pay', () => {
    expect(text).toContain("nothing extra to pay");
  });
});

describe('class2EducationSnippet — covered_no_class4', () => {
  const text = class2EducationSnippet('covered_no_class4', BASE_CONFIG);

  it('shows the small profits threshold from config', () => {
    expect(text).toContain('7,105');
  });

  it('shows the Class 4 lower limit from config', () => {
    expect(text).toContain('12,570');
  });

  it('says the year still counts towards State Pension', () => {
    expect(text).toContain('State Pension');
    expect(text).toContain('still counts');
  });

  it('updates thresholds when config changes', () => {
    const customCfg = { ...BASE_CONFIG, class2_small_profits_threshold: 8000, class4_lower_limit: 13000 };
    const custom = class2EducationSnippet('covered_no_class4', customCfg);
    expect(custom).toContain('8,000');
    expect(custom).toContain('13,000');
    expect(custom).not.toContain('7,105');
    expect(custom).not.toContain('12,570');
  });
});

describe('class2EducationSnippet — below_threshold', () => {
  const text = class2EducationSnippet('below_threshold', BASE_CONFIG);

  it('shows the small profits threshold from config', () => {
    expect(text).toContain('7,105');
  });

  it('shows weekly rate from config', () => {
    expect(text).toContain('3.65/week');
  });

  it('annual figure = round(class2_weekly_rate × 52)', () => {
    const expected = Math.round(3.65 * 52); // 190
    expect(text).toContain(`£${expected} a year`);
  });

  it('annual figure changes when config changes — no hardcoded 190 or 3.65', () => {
    const customCfg = { ...BASE_CONFIG, class2_weekly_rate: 4.00 };
    const custom = class2EducationSnippet('below_threshold', customCfg);
    const expectedAnnual = Math.round(4.00 * 52); // 208
    expect(custom).toContain(`£${expectedAnnual} a year`);
    expect(custom).toContain('4/week');
    expect(custom).not.toContain('190');
    expect(custom).not.toContain('3.65');
  });

  it('says the year won\'t automatically count', () => {
    expect(text).toContain("won't automatically count");
    expect(text).toContain('State Pension');
  });

  it('mentions voluntary Class 2', () => {
    expect(text).toContain('voluntary Class 2');
  });
});

describe('class2EducationSnippet — null/missing config', () => {
  it('returns empty string when taxConfig is null', () => {
    expect(class2EducationSnippet('covered', null)).toBe('');
  });

  it('returns empty string for unknown status', () => {
    expect(class2EducationSnippet('unknown_status', BASE_CONFIG)).toBe('');
  });
});

// ---------------------------------------------------------------------------
// Pension explainer
// ---------------------------------------------------------------------------

describe('CLASS2_PENSION_EXPLAINER', () => {
  it('contains 35 qualifying years', () => {
    expect(CLASS2_PENSION_EXPLAINER).toContain('35 qualifying years');
  });

  it('contains 10 year minimum', () => {
    expect(CLASS2_PENSION_EXPLAINER).toContain('10');
  });

  it('references the official gov.uk forecast', () => {
    expect(CLASS2_PENSION_EXPLAINER).toContain('gov.uk/check-state-pension');
  });

  it('contains no specific State Pension £ amount — pension described in qualifying-year terms only', () => {
    // No £ values: the State Pension amount changes every April and we don't state it
    expect(CLASS2_PENSION_EXPLAINER).not.toMatch(/£[\d]/);
  });
});

// ---------------------------------------------------------------------------
// No State Pension amount in any snippet
// ---------------------------------------------------------------------------

describe('No State Pension £ amount in any snippet', () => {
  // The snippets may contain NI contribution rates (Class 2 rates) but must
  // not contain a specific pension payout amount. Since we only embed NI
  // rates (which come from config) and qualifying-year language, we assert
  // the explainer — which is the pension-focused text — is free of all £.
  it('CLASS2_PENSION_EXPLAINER is free of all £ figures', () => {
    expect(CLASS2_PENSION_EXPLAINER).not.toMatch(/£/);
  });

  // For the status snippets: any £ values present are NI contribution rates
  // (explicitly labelled "/week" or "a year"), not pension payout amounts.
  // We verify "State Pension" is never followed by a £ amount.
  it('no snippet says "State Pension of £..."', () => {
    const statuses = ['covered', 'covered_no_class4', 'below_threshold'];
    for (const status of statuses) {
      const text = class2EducationSnippet(status, BASE_CONFIG);
      expect(text).not.toMatch(/State Pension[^.]*£[\d]/);
    }
  });
});
