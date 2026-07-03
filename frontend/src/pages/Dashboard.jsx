import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import NavBar from '../components/NavBar';
import InfoTip from '../components/InfoTip';
import OnboardingWizard from '../components/OnboardingWizard';
import ChecklistPanel from '../components/ChecklistPanel';
import { useAuth } from '../context/AuthContext';

import { gbp } from '../utils/format';

function formatMonthDelta(monthDelta) {
  const totalDays = Math.round(Math.abs(monthDelta) * 30.44);
  if (totalDays < 1) return null;
  const whole = Math.floor(Math.abs(monthDelta));
  const days  = Math.round((Math.abs(monthDelta) - whole) * 30.44);
  const mo = n => `${n} ${n === 1 ? 'month' : 'months'}`;
  const dy = n => `${n} ${n === 1 ? 'day' : 'days'}`;
  if (whole === 0) return dy(days);
  if (days === 0)  return mo(whole);
  return `${mo(whole)}, ${dy(days)}`;
}

function ChangeIndicator({ metric }) {
  if (!metric) return null;
  const { direction, absolute_change, elapsed_days } = metric;
  if (direction === 'unchanged') return null;

  const arrow = direction === 'up' ? '↑' : '↓';
  const sign  = absolute_change >= 0 ? '+' : '';

  return (
    <span className="change-indicator">
      {arrow} {sign}{gbp(Math.abs(absolute_change))}
      <span className="change-indicator-period"> ({elapsed_days}d ago)</span>
    </span>
  );
}

function RunwayChangeIndicator({ metric }) {
  if (!metric) return null;
  const { direction, absolute_change, elapsed_days, current_value } = metric;
  if (direction === 'unchanged') return null;

  const label = formatMonthDelta(absolute_change);
  if (!label) return null;

  const warn = current_value < 3 && direction === 'down';
  const cls  = `change-indicator${warn ? ' change-indicator--warn' : ''}`;
  const arrow = direction === 'up' ? '↑' : '↓';

  return (
    <span className={cls}>
      {arrow} {label}
      <span className="change-indicator-period"> ({elapsed_days}d ago)</span>
    </span>
  );
}

export default function Dashboard() {
  const { apiFetch } = useAuth();
  const [summary, setSummary] = useState(null);
  const [changes, setChanges] = useState(null);
  const [onboarding, setOnboarding] = useState(null);
  const [showWizard, setShowWizard] = useState(false);
  const [firstName, setFirstName] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    apiFetch('/api/finance/summary')
      .then(res => {
        if (!res.ok) return res.json().then(b => Promise.reject(new Error(b.detail || 'Error')));
        return res.json();
      })
      .then(setSummary)
      .catch(err => setError(err.message));

    apiFetch('/api/finance/changes')
      .then(res => res.ok ? res.json() : null)
      .then(data => data && setChanges(data))
      .catch(() => {});

    apiFetch('/api/profile/onboarding')
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (!data) return;
        setOnboarding(data);
        if (!data.onboarding_completed && data.onboarding_dismiss_count < 2) {
          setShowWizard(true);
        }
      })
      .catch(() => {});

    apiFetch('/api/profile')
      .then(res => res.ok ? res.json() : null)
      .then(data => { if (data?.first_name) setFirstName(data.first_name); })
      .catch(() => {});
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  function handleWizardComplete() {
    setShowWizard(false);
    setOnboarding(prev => prev ? { ...prev, onboarding_completed: true } : prev);
    apiFetch('/api/finance/summary')
      .then(res => res.ok ? res.json() : null)
      .then(data => data && setSummary(data))
      .catch(() => {});
  }

  function handleWizardDismiss() {
    setShowWizard(false);
    setOnboarding(prev => prev ? { ...prev, onboarding_dismiss_count: (prev.onboarding_dismiss_count ?? 0) + 1 } : prev);
  }

  if (error) {
    return (
      <>
        <NavBar />
        <div className="page-error">{error}</div>
      </>
    );
  }

  if (!summary) {
    return (
      <>
        <NavBar />
        <div className="page-loading">Loading your summary…</div>
      </>
    );
  }

  const {
    take_home: t,
    monthly_disposable, monthly_expenses, monthly_debt_payments, monthly_savings_contributions,
    total_savings_balance, pension_pot_balance, total_assets_value, total_debt_balance, net_worth,
    months_of_runway,
  } = summary;
  const hasIncome = t.gross_annual > 0;
  const totalOutgoings = monthly_expenses + monthly_debt_payments + monthly_savings_contributions;

  // Pick the most granular period available (weekly > monthly)
  const period = changes?.weekly ?? changes?.monthly ?? null;
  const periodLabel = period?.label ?? null;

  function formatRunway(months) {
    const whole = Math.floor(months);
    const days = Math.round((months - whole) * 30.44);
    const mo = n => `${n} ${n === 1 ? 'month' : 'months'}`;
    const dy = n => `${n} ${n === 1 ? 'day' : 'days'}`;
    if (whole === 0) return dy(days);
    if (days === 0) return mo(whole);
    return `${mo(whole)}, ${dy(days)}`;
  }

  function runwayTier(months) {
    if (months < 1) return 'runway-low';
    if (months < 3) return 'runway-mid';
    return 'runway-good';
  }

  function runwayContext(months) {
    if (months < 1) return "Less than a month's cover — your savings don't yet match a full month of expenses.";
    if (months < 3) return "Covers a short disruption — an unexpected repair, a month between jobs.";
    if (months < 6) return "A meaningful cushion. Enough to absorb several months of reduced or no income.";
    return "Over 6 months of cover — a strong position relative to your current spending.";
  }

  const completionStatus = summary?.completion_status ?? null;

  return (
    <>
      <NavBar />
      {showWizard && (
        <OnboardingWizard
          initialStep={onboarding?.current_onboarding_step ?? 0}
          dismissCount={onboarding?.onboarding_dismiss_count ?? 0}
          firstName={firstName}
          onFirstNameChange={setFirstName}
          onComplete={handleWizardComplete}
          onDismiss={handleWizardDismiss}
        />
      )}
      <div className="dashboard-wrapper">
      <main className="dashboard">
        {!hasIncome ? (
          <div className="empty-state">
            <h2>{firstName ? `Hi ${firstName}, welcome to fivera` : 'Welcome to fivera'}</h2>
            <p>
              You haven't added any income sources yet. Once you do, you'll see your full
              take-home breakdown, deductions, and monthly disposable income here.
            </p>
            <Link to="/income" className="btn-primary" style={{ display: 'inline-block', width: 'auto', textDecoration: 'none' }}>
              Add your first income source
            </Link>
          </div>
        ) : (
          <>
            {firstName && <p className="dashboard-greeting">Hi {firstName},</p>}
            {/* ── Hero: disposable income ── */}
            <div className="hero">
              <p className="hero-label">Monthly Disposable Income</p>
              <p className={`hero-amount ${monthly_disposable >= 0 ? 'positive' : 'negative'}`}>
                {gbp(monthly_disposable)}
              </p>
              <ChangeIndicator metric={period?.monthly_disposable_income} />
              <p className="hero-sub">after tax, deductions &amp; outgoings</p>
            </div>

            <div className="cards-grid">
              {/* ── Net Worth ── */}
              <div className="card net-worth-card">
                <p className="card-title">
                  <span className="label-with-tip">Net Worth<InfoTip text="Everything you own (savings, pension, property, vehicles) minus everything you owe (debts). A snapshot of your overall financial position." /></span>
                  <ChangeIndicator metric={period?.net_worth} />
                </p>
                <p className={`net-worth-amount ${net_worth >= 0 ? 'nw-positive' : 'nw-negative'}`}>
                  {gbp(net_worth)}
                </p>
                <table className="breakdown">
                  <tbody>
                    <tr>
                      <td>Savings &amp; investments</td>
                      <td>
                        {gbp(total_savings_balance)}
                        <ChangeIndicator metric={period?.total_savings_balance} />
                      </td>
                    </tr>
                    <tr>
                      <td>Pension pot</td>
                      <td>
                        {gbp(pension_pot_balance)}
                        <ChangeIndicator metric={period?.pension_pot_balance} />
                      </td>
                    </tr>
                    <tr>
                      <td>Assets</td>
                      <td>{gbp(total_assets_value)}</td>
                    </tr>
                    <tr className="row-muted">
                      <td>Total debt</td>
                      <td>
                        −{gbp(total_debt_balance)}
                        <ChangeIndicator metric={period?.total_debt_balance} />
                      </td>
                    </tr>
                    <tr className="row-total">
                      <td>Net worth</td>
                      <td style={{ color: net_worth >= 0 ? '#0f766e' : 'var(--color-negative)' }}>
                        {gbp(net_worth)}
                      </td>
                    </tr>
                  </tbody>
                </table>
                {periodLabel && (
                  <p className="change-period-label">{periodLabel}</p>
                )}
              </div>

              {/* ── Income & deductions ── */}
              <div className="card">
                <p className="card-title">Income &amp; Deductions</p>
                <table className="breakdown">
                  <tbody>
                    <tr>
                      <td>Gross annual <span className="label-with-tip">salary<InfoTip text="Your total salary before any tax, National Insurance, or other deductions are taken off." /></span></td>
                      <td>{gbp(t.gross_annual)}</td>
                    </tr>
                    <tr className="row-muted">
                      <td>Income tax</td>
                      <td>−{gbp(t.income_tax)}</td>
                    </tr>
                    <tr className="row-muted">
                      <td><span className="label-with-tip">National Insurance<InfoTip text="A tax on your earnings that funds the NHS, state pension, and other benefits. Taken directly from your pay before you receive it." /></span></td>
                      <td>−{gbp(t.national_insurance)}</td>
                    </tr>
                    {t.student_loan > 0 && (
                      <tr className="row-muted">
                        <td>Student loan</td>
                        <td>−{gbp(t.student_loan)}</td>
                      </tr>
                    )}
                    {t.pension_employee > 0 && (
                      <tr className="row-muted">
                        <td><span className="label-with-tip">Pension (employee)<InfoTip text="The amount deducted from your salary each month and paid into your pension pot. Your employer usually adds on top of this separately." /></span></td>
                        <td>−{gbp(t.pension_employee)}</td>
                      </tr>
                    )}
                    <tr className="row-total">
                      <td>Net monthly <span className="label-with-tip">income<InfoTip text="What actually lands in your bank account each month after all deductions have been taken off." /></span></td>
                      <td>{gbp(t.net_monthly)}</td>
                    </tr>
                  </tbody>
                </table>
                {t.pension_employer > 0 && (
                  <p style={{ marginTop: '0.875rem', fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
                    + {gbp(t.pension_employer)} employer pension (on top of your pay)
                  </p>
                )}
              </div>

              {/* ── Monthly outgoings ── */}
              <div className="card">
                <p className="card-title">Monthly Outgoings</p>
                <table className="breakdown">
                  <tbody>
                    <tr>
                      <td>Net monthly <span className="label-with-tip">income<InfoTip text="What actually lands in your bank account each month after all deductions have been taken off." /></span></td>
                      <td>{gbp(t.net_monthly)}</td>
                    </tr>
                    {monthly_expenses > 0 && (
                      <tr className="row-muted">
                        <td>Expenses</td>
                        <td>−{gbp(monthly_expenses)}</td>
                      </tr>
                    )}
                    {monthly_debt_payments > 0 && (
                      <tr className="row-muted">
                        <td>Debt payments</td>
                        <td>−{gbp(monthly_debt_payments)}</td>
                      </tr>
                    )}
                    {monthly_savings_contributions > 0 && (
                      <tr className="row-muted">
                        <td>Savings contributions</td>
                        <td>−{gbp(monthly_savings_contributions)}</td>
                      </tr>
                    )}
                    {totalOutgoings === 0 && (
                      <tr className="row-muted">
                        <td colSpan={2} style={{ color: 'var(--color-text-muted)', fontStyle: 'italic' }}>
                          No expenses, debts, or savings set up yet
                        </td>
                      </tr>
                    )}
                    <tr className="row-total">
                      <td>Disposable income</td>
                      <td style={{ color: monthly_disposable >= 0 ? 'var(--color-positive)' : 'var(--color-negative)' }}>
                        {gbp(monthly_disposable)}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            {/* ── Emergency fund runway ── */}
            {months_of_runway === null ? (
              <div className="card runway-card runway-card--null">
                <p className="card-title"><span className="label-with-tip">Emergency Fund Coverage<InfoTip text="How many months you could cover your essential expenses using your current savings if your income stopped. 3–6 months is generally considered a healthy buffer." /></span></p>
                <p className="runway-prompt">
                  Add your <Link to="/expenses" className="runway-link">monthly expenses</Link> to see how long your savings would last.
                </p>
              </div>
            ) : (
              <div className={`card runway-card ${runwayTier(months_of_runway)}`}>
                <p className="card-title"><span className="label-with-tip">Emergency Fund Coverage<InfoTip text="How many months you could cover your essential expenses using your current savings if your income stopped. 3–6 months is generally considered a healthy buffer." /></span></p>
                <div className="runway-header">
                  <span className={`runway-months ${runwayTier(months_of_runway)}`}>
                    {formatRunway(months_of_runway)}
                  </span>
                  <span className="runway-sub">of expenses covered by savings</span>
                  <RunwayChangeIndicator metric={period?.months_of_runway} />
                </div>
                <p className="runway-supporting">
                  based on {gbp(monthly_expenses + monthly_debt_payments)}/month in expenses
                  {monthly_debt_payments > 0 && ` (includes ${gbp(monthly_debt_payments)} debt payments)`}
                </p>
                <p className="runway-context">{runwayContext(months_of_runway)}</p>
              </div>
            )}
          </>
        )}
      </main>
      {completionStatus && <ChecklistPanel status={completionStatus} />}
      </div>
    </>
  );
}
