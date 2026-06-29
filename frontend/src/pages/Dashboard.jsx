import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import NavBar from '../components/NavBar';
import { useAuth } from '../context/AuthContext';

const gbp = n =>
  new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' }).format(n);

export default function Dashboard() {
  const { apiFetch } = useAuth();
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    apiFetch('/api/finance/summary')
      .then(res => {
        if (!res.ok) return res.json().then(b => Promise.reject(new Error(b.detail || 'Error')));
        return res.json();
      })
      .then(setSummary)
      .catch(err => setError(err.message));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

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
    total_savings_balance, pension_pot_balance, total_debt_balance, net_worth,
  } = summary;
  const hasIncome = t.gross_annual > 0;
  const totalOutgoings = monthly_expenses + monthly_debt_payments + monthly_savings_contributions;

  return (
    <>
      <NavBar />
      <main className="dashboard">
        {!hasIncome ? (
          <div className="empty-state">
            <h2>Welcome to FinanceApp</h2>
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
            {/* ── Hero: disposable income ── */}
            <div className="hero">
              <p className="hero-label">Monthly Disposable Income</p>
              <p className={`hero-amount ${monthly_disposable >= 0 ? 'positive' : 'negative'}`}>
                {gbp(monthly_disposable)}
              </p>
              <p className="hero-sub">after tax, deductions &amp; outgoings</p>
            </div>

            <div className="cards-grid">
              {/* ── Net Worth ── */}
              <div className="card net-worth-card">
                <p className="card-title">Net Worth</p>
                <p className={`net-worth-amount ${net_worth >= 0 ? 'nw-positive' : 'nw-negative'}`}>
                  {gbp(net_worth)}
                </p>
                <table className="breakdown">
                  <tbody>
                    <tr>
                      <td>Savings</td>
                      <td>{gbp(total_savings_balance)}</td>
                    </tr>
                    <tr>
                      <td>Pension pot</td>
                      <td>{gbp(pension_pot_balance)}</td>
                    </tr>
                    <tr className="row-muted">
                      <td>Total debt</td>
                      <td>−{gbp(total_debt_balance)}</td>
                    </tr>
                    <tr className="row-total">
                      <td>Net worth</td>
                      <td style={{ color: net_worth >= 0 ? '#0f766e' : 'var(--color-negative)' }}>
                        {gbp(net_worth)}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              {/* ── Income & deductions ── */}
              <div className="card">
                <p className="card-title">Income &amp; Deductions</p>
                <table className="breakdown">
                  <tbody>
                    <tr>
                      <td>Gross annual salary</td>
                      <td>{gbp(t.gross_annual)}</td>
                    </tr>
                    <tr className="row-muted">
                      <td>Income tax</td>
                      <td>−{gbp(t.income_tax)}</td>
                    </tr>
                    <tr className="row-muted">
                      <td>National Insurance</td>
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
                        <td>Pension (employee)</td>
                        <td>−{gbp(t.pension_employee)}</td>
                      </tr>
                    )}
                    <tr className="row-total">
                      <td>Net monthly income</td>
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
                      <td>Net monthly income</td>
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
          </>
        )}
      </main>
    </>
  );
}
