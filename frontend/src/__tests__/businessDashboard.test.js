import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { taxCardLabel, yearSelectorOptions } from '../utils/businessDashboard';

describe('taxCardLabel', () => {
  it('uses "Set aside for your tax bill" for the current (in-progress) tax year', () => {
    expect(taxCardLabel({ is_complete: false, tax_year: '2026/27' })).toBe('Set aside for your tax bill');
  });

  it('uses "Tax due for {year}" once the tax year has ended', () => {
    expect(taxCardLabel({ is_complete: true, tax_year: '2025/26' })).toBe('Tax due for 2025/26');
  });
});

describe('yearSelectorOptions', () => {
  it('lists exactly the data-derived years when the selected year is among them', () => {
    expect(yearSelectorOptions('2026/27', ['2026/27', '2025/26'])).toEqual(['2026/27', '2025/26']);
  });

  it('sorts most recent first', () => {
    expect(yearSelectorOptions('2024/25', ['2024/25', '2026/27', '2025/26'])).toEqual(['2026/27', '2025/26', '2024/25']);
  });

  it('includes the selected year even if it has no confirmed entries yet', () => {
    expect(yearSelectorOptions('2026/27', ['2025/26'])).toEqual(['2026/27', '2025/26']);
  });

  it('shows only one year for a user with data in only one tax year', () => {
    expect(yearSelectorOptions('2025/26', ['2025/26'])).toEqual(['2025/26']);
  });

  it('de-duplicates if the selected year is already in the data-derived list', () => {
    const result = yearSelectorOptions('2025/26', ['2025/26']);
    expect(result).toHaveLength(1);
  });

  it('ignores an empty/unset selected year', () => {
    expect(yearSelectorOptions('', ['2026/27'])).toEqual(['2026/27']);
  });
});

// ---------------------------------------------------------------------------
// Business.jsx wiring — the "add new entry" modals must always use the
// CURRENT tax year's rates (they default to today's date), never whichever
// past year happens to be selected on the dashboard.
// ---------------------------------------------------------------------------

describe('Business.jsx add-entry modals use current-year config, not the selected dashboard year', () => {
  const src = readFileSync(resolve(__dirname, '../pages/Business.jsx'), 'utf-8');
  const expenseModalUses = [...src.matchAll(/<ExpenseModal\b[^/]*taxConfig=\{(\w+)\}/g)].map(m => m[1]);

  it('ExpenseModal is wired up at least once', () => {
    expect(expenseModalUses.length).toBeGreaterThan(0);
  });

  it('every ExpenseModal instance uses currentTaxConfig, not the year-scoped taxConfig', () => {
    for (const propValue of expenseModalUses) {
      expect(propValue).toBe('currentTaxConfig');
    }
  });

  it('fetches a dedicated current-year tax-config (no query string) alongside the selected-year one', () => {
    expect(src).toMatch(/apiFetch\('\/api\/business\/tax-config'\)/);
  });
});

describe('.tax-year-select and .tax-config-missing-banner CSS', () => {
  const css = readFileSync(resolve(__dirname, '../index.css'), 'utf-8');

  it('.tax-year-select is found', () => {
    expect(css).toMatch(/\.tax-year-select\s*\{/);
  });

  it('.tax-config-missing-banner is found and uses the warning palette', () => {
    const match = css.match(/\.tax-config-missing-banner\s*\{([^}]+)\}/);
    expect(match).not.toBeNull();
    expect(match[1]).toMatch(/#fef3c7|#fde68a/);
  });
});
