import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

// ---------------------------------------------------------------------------
// Registration no longer collects or requires income. No component-rendering
// library is set up in this project, so — matching the existing source-scan
// convention used elsewhere in this suite — these assert against the actual
// page source rather than a rendered tree.
// ---------------------------------------------------------------------------

describe('Register.jsx no longer captures income', () => {
  const src = readFileSync(resolve(__dirname, '../pages/Register.jsx'), 'utf-8');

  it('has no salary input or salary state', () => {
    expect(src).not.toMatch(/salary/i);
  });

  it('never calls the income-creation endpoint', () => {
    expect(src).not.toMatch(/\/api\/income/);
  });

  it('registration form only collects email and password (no salary field)', () => {
    expect(src).toMatch(/id="email"/);
    expect(src).toMatch(/id="password"/);
    expect(src).not.toMatch(/id="salary"/);
  });

  it('lands on the business dashboard by default after registering, like login', () => {
    expect(src).toMatch(/navigate\(mode === 'personal' \? '\/personal' : '\/'/);
  });
});

// ---------------------------------------------------------------------------
// The mandatory income gate lives on first entry to the personal dashboard.
// ---------------------------------------------------------------------------

describe('Dashboard.jsx gates on missing income', () => {
  const src = readFileSync(resolve(__dirname, '../pages/Dashboard.jsx'), 'utf-8');

  it('defines an IncomeGate component', () => {
    expect(src).toMatch(/function IncomeGate\(/);
  });

  it('IncomeGate auto-creates the first income source via POST /api/income', () => {
    const gateMatch = src.match(/function IncomeGate\([^)]*\)\s*\{([\s\S]*?)\n}\n/);
    expect(gateMatch).not.toBeNull();
    const body = gateMatch[1];
    expect(body).toMatch(/apiFetch\('\/api\/income'/);
    expect(body).toMatch(/method:\s*'POST'/);
    expect(body).toMatch(/gross_annual_salary/);
  });

  it('the dashboard body returns the gate, not the dashboard, when hasIncome is false', () => {
    const gateGuard = src.match(/if \(!hasIncome\)\s*\{([\s\S]*?)\n {2}\}/);
    expect(gateGuard).not.toBeNull();
    expect(gateGuard[1]).toMatch(/<IncomeGate/);
  });

  it('the gate guard runs before the main dashboard JSX is returned', () => {
    const gateIndex = src.indexOf('if (!hasIncome)');
    const heroIndex = src.indexOf('Monthly Disposable Income');
    expect(gateIndex).toBeGreaterThan(-1);
    expect(heroIndex).toBeGreaterThan(-1);
    expect(gateIndex).toBeLessThan(heroIndex);
  });
});
