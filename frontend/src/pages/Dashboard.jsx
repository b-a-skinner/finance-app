import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import NavBar from '../components/NavBar';
import InfoTip from '../components/InfoTip';
import OnboardingWizard from '../components/OnboardingWizard';
import ChecklistPanel from '../components/ChecklistPanel';
import BenchmarkCarousel from '../components/BenchmarkCarousel';
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
  return (
    <span className="change-indicator">
      {arrow} {absolute_change >= 0 ? '+' : ''}{gbp(Math.abs(absolute_change))}
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
  return (
    <span className={cls}>
      {direction === 'up' ? '↑' : '↓'} {label}
      <span className="change-indicator-period"> ({elapsed_days}d ago)</span>
    </span>
  );
}

/* Row that is a dashed add button when value=0, or a clickable link row when non-zero */
function NwRow({ label, addLabel, to, value, displayValue, metric, className }) {
  const navigate = useNavigate();

  if (value === 0) {
    return (
      <tr className="nw-row-add">
        <td colSpan="2">
          <button className="nw-add-btn" onClick={() => navigate(to)}>
            + {addLabel}
          </button>
        </td>
      </tr>
    );
  }

  return (
    <tr
      className={`nw-row-link${className ? ` ${className}` : ''}`}
      onClick={() => navigate(to)}
    >
      <td>{label}</td>
      <td>
        {displayValue ?? gbp(value)}
        {metric && <ChangeIndicator metric={metric} />}
        <span className="nw-row-chevron" aria-hidden="true">›</span>
      </td>
    </tr>
  );
}

/* Dashed add row for the Monthly Outgoings table */
function OutgoingsAddRow({ addLabel, to }) {
  const navigate = useNavigate();
  return (
    <tr className="nw-row-add">
      <td colSpan="2">
        <button className="nw-add-btn" onClick={() => navigate(to)}>
          + {addLabel}
        </button>
      </td>
    </tr>
  );
}

function DashPrompt({ to, children }) {
  return <Link to={to} className="dash-prompt">{children}</Link>;
}

export default function Dashboard() {
  const { apiFetch } = useAuth();
  const navigate = useNavigate();
  const [summary,     setSummary]     = useState(null);
  const [changes,     setChanges]     = useState(null);
  const [onboarding,  setOnboarding]  = useState(null);
  const [showWizard,  setShowWizard]  = useState(false);
  const [firstName,   setFirstName]   = useState('');
  const [profileData, setProfileData] = useState(null);
  const [comparison,  setComparison]  = useState(null);
  const [error,       setError]       = useState('');

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
      .then(data => { if (data) setOnboarding(data); })
      .catch(() => {});

    apiFetch('/api/profile')
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (!data) return;
        if (data.first_name) setFirstName(data.first_name);
        setProfileData(data);
      })
      .catch(() => {});

    apiFetch('/api/profile/comparison')
      .then(res => res.ok ? res.json() : null)
      .then(data => { if (data) setComparison(data); })
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
  const period    = changes?.weekly ?? changes?.monthly ?? null;
  const cs        = summary?.completion_status ?? {};

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
          initialStep={0}
          dismissCount={onboarding?.onboarding_dismiss_count ?? 0}
          firstName={firstName}
          onFirstNameChange={setFirstName}
          onComplete={handleWizardComplete}
          onDismiss={handleWizardDismiss}
        />
      )}
      <div className="dashboard-wrapper">
        <main className="dashboard">
          {firstName && <p className="dashboard-greeting">Hi {firstName},</p>}

          {/* ── Hero: disposable income ── */}
          {hasIncome && (
            <div className="hero">
              <p className="hero-label">Monthly Disposable Income</p>
              <p className={`hero-amount ${monthly_disposable >= 0 ? 'positive' : 'negative'}`}>
                {gbp(monthly_disposable)}
              </p>
              <ChangeIndicator metric={period?.monthly_disposable_income} />
              <p className="hero-sub">after tax, deductions &amp; outgoings</p>
            </div>
          )}

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
                  <NwRow
                    label="Savings & investments"
                    addLabel="Add savings & investments"
                    to="/savings"
                    value={total_savings_balance}
                    metric={period?.total_savings_balance}
                  />
                  <NwRow
                    label="Pension pot"
                    addLabel="Add pension"
                    to="/pension"
                    value={pension_pot_balance}
                    metric={period?.pension_pot_balance}
                  />
                  <NwRow
                    label="Assets"
                    addLabel="Add assets"
                    to="/assets"
                    value={total_assets_value}
                  />
                  <NwRow
                    label="Total debt"
                    addLabel="Add debts"
                    to="/debts"
                    value={total_debt_balance}
                    displayValue={`−${gbp(total_debt_balance)}`}
                    metric={period?.total_debt_balance}
                    className="row-muted"
                  />
                  <tr className="row-total">
                    <td>Net worth</td>
                    <td style={{ color: net_worth >= 0 ? '#0f766e' : 'var(--color-negative)' }}>
                      {gbp(net_worth)}
                    </td>
                  </tr>
                </tbody>
              </table>
              {period?.label && <p className="change-period-label">{period.label}</p>}
            </div>

            {/* ── Income & deductions ── */}
            <div className="card">
              <p className="card-title">Income &amp; Deductions</p>
              {!hasIncome ? (
                <div className="dash-prompts" style={{ padding: '0.5rem 0' }}>
                  <DashPrompt to="/income">Add your salary to see your tax breakdown →</DashPrompt>
                </div>
              ) : (
                <>
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
                </>
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
                  {monthly_expenses > 0 ? (
                    <tr className="row-muted">
                      <td>Expenses</td>
                      <td>−{gbp(monthly_expenses)}</td>
                    </tr>
                  ) : (
                    <OutgoingsAddRow addLabel="Add expenses" to="/expenses" />
                  )}
                  {monthly_debt_payments > 0 ? (
                    <tr className="row-muted">
                      <td>Debt payments</td>
                      <td>−{gbp(monthly_debt_payments)}</td>
                    </tr>
                  ) : (
                    <OutgoingsAddRow addLabel="Add debts" to="/debts" />
                  )}
                  {monthly_savings_contributions > 0 ? (
                    <tr className="row-muted">
                      <td>Savings contributions</td>
                      <td>−{gbp(monthly_savings_contributions)}</td>
                    </tr>
                  ) : (
                    <OutgoingsAddRow addLabel="Add savings" to="/savings" />
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
            <div
              className="card runway-card runway-card--null"
              style={total_savings_balance === 0 ? { cursor: 'pointer' } : undefined}
              onClick={total_savings_balance === 0 ? () => navigate('/savings') : undefined}
            >
              <p className="card-title">
                <span className="label-with-tip">Emergency Fund Coverage<InfoTip text="How many months you could cover your essential expenses using your current savings if your income stopped. 3–6 months is generally considered a healthy buffer." /></span>
              </p>
              {total_savings_balance === 0 ? (
                <p className="runway-null-prompt">
                  Add your savings to calculate your financial runway →
                </p>
              ) : (
                <div className="dash-prompts">
                  <DashPrompt to="/expenses">Add your monthly expenses to see your financial runway →</DashPrompt>
                </div>
              )}
            </div>
          ) : (
            <div className={`card runway-card ${runwayTier(months_of_runway)}`}>
              <p className="card-title">
                <span className="label-with-tip">Emergency Fund Coverage<InfoTip text="How many months you could cover your essential expenses using your current savings if your income stopped. 3–6 months is generally considered a healthy buffer." /></span>
              </p>
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

          {/* ── Benchmark carousel — below emergency fund ── */}
          <BenchmarkCarousel comparison={comparison} profile={profileData} />

          {/* ── Setup checklist ── */}
          {completionStatus && (
            <ChecklistPanel
              status={completionStatus}
              onOpenWizard={() => setShowWizard(true)}
            />
          )}
        </main>
      </div>
    </>
  );
}
