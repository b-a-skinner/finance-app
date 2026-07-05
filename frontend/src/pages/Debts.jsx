import { useCallback, useEffect, useState } from 'react';
import NavBar from '../components/NavBar';
import { useAuth } from '../context/AuthContext';
import { useResource } from '../hooks/useResource';
import { API_BASE } from '../utils/config';

const EMPTY = {
  debt_type: 'credit_card',
  balance: '',
  interest_rate: '',
  min_payment: '',
  student_loan_plan_id: '',
  graduation_year: '',
};

const DEBT_TYPE_LABEL = {
  student_loan: 'Student loan',
  credit_card: 'Credit card',
  mortgage: 'Mortgage',
  other: 'Other',
};

import { gbp } from '../utils/format';
const pct = n => `${n}%`;

function formatDuration(months) {
  const years = Math.floor(months / 12);
  const rem = months % 12;
  if (years === 0) return `${months} ${months === 1 ? 'month' : 'months'}`;
  if (rem === 0) return `${years} ${years === 1 ? 'year' : 'years'}`;
  return `${years} ${years === 1 ? 'year' : 'years'}, ${rem} ${rem === 1 ? 'month' : 'months'}`;
}

function ageInMonths(dob, monthsFromNow) {
  if (!dob) return null;
  const today = new Date();
  const target = new Date(today);
  target.setMonth(target.getMonth() + monthsFromNow);
  const birth = new Date(dob);
  let age = target.getFullYear() - birth.getFullYear();
  const m = target.getMonth() - birth.getMonth();
  if (m < 0 || (m === 0 && target.getDate() < birth.getDate())) age--;
  return age;
}

export default function Debts() {
  const { apiFetch } = useAuth();
  const { items, loading, error, create, update, remove } = useResource('/api/debts');
  const [loanPlans, setLoanPlans] = useState([]);
  const [projections, setProjections] = useState({});
  const [repaymentProjections, setRepaymentProjections] = useState({});
  const [dob, setDob] = useState(null);
  const [form, setForm] = useState(EMPTY);
  const [editingId, setEditingId] = useState(null);
  const [formOpen, setFormOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');
  const [actionError, setActionError] = useState('');

  useEffect(() => {
    fetch(`${API_BASE}/api/config/student-loan-plans`)
      .then(r => r.json())
      .then(setLoanPlans)
      .catch(() => {});
  }, []);

  // Fetch user's date_of_birth for age display in projection
  useEffect(() => {
    apiFetch('/api/profile')
      .then(r => r.json())
      .then(data => setDob(data.date_of_birth || null))
      .catch(() => {});
  }, [apiFetch]);

  // Fetch student loan projections
  useEffect(() => {
    const eligible = items.filter(
      d => d.debt_type === 'student_loan' && d.graduation_year
    );
    eligible.forEach(debt => {
      apiFetch(`/api/debts/${debt.id}/projection`)
        .then(r => r.ok ? r.json() : null)
        .then(data => {
          if (data) setProjections(prev => ({ ...prev, [debt.id]: data }));
        })
        .catch(() => {});
    });
  }, [items, apiFetch]); // eslint-disable-line react-hooks/exhaustive-deps

  // Fetch repayment projections for non-student-loan debts
  useEffect(() => {
    const eligible = items.filter(
      d => d.debt_type !== 'student_loan' && d.balance > 0 && d.min_payment > 0
    );
    eligible.forEach(debt => {
      apiFetch(`/api/debts/${debt.id}/repayment-projection`)
        .then(r => r.ok ? r.json() : null)
        .then(data => {
          if (data) setRepaymentProjections(prev => ({ ...prev, [debt.id]: data }));
        })
        .catch(() => {});
    });
  }, [items, apiFetch]); // eslint-disable-line react-hooks/exhaustive-deps

  function field(key, val) {
    setForm(prev => ({ ...prev, [key]: val }));
  }

  function startEdit(item) {
    setEditingId(item.id);
    setFormOpen(true);
    setForm({
      debt_type: item.debt_type,
      balance: item.balance,
      interest_rate: item.interest_rate,
      min_payment: item.min_payment,
      student_loan_plan_id: item.student_loan_plan_id ?? '',
      graduation_year: item.graduation_year ?? '',
    });
    setFormError('');
    if (window.innerWidth >= 768) window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function cancelEdit() {
    setEditingId(null);
    setFormOpen(false);
    setForm(EMPTY);
    setFormError('');
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setFormError('');
    const balance = parseFloat(form.balance);
    const rate = parseFloat(form.interest_rate);
    const minPay = parseFloat(form.min_payment);

    if (isNaN(balance) || balance < 0) { setFormError('Enter a valid balance.'); return; }
    if (isNaN(rate) || rate < 0) { setFormError('Enter a valid interest rate.'); return; }
    if (isNaN(minPay) || minPay < 0) { setFormError('Enter a valid minimum payment.'); return; }
    if (form.debt_type === 'student_loan' && !form.student_loan_plan_id) {
      setFormError('Select a student loan plan.'); return;
    }

    const data = {
      debt_type: form.debt_type,
      balance,
      interest_rate: rate,
      min_payment: minPay,
      student_loan_plan_id: form.debt_type === 'student_loan'
        ? parseInt(form.student_loan_plan_id, 10)
        : null,
      graduation_year: form.debt_type === 'student_loan' && form.graduation_year
        ? parseInt(form.graduation_year, 10)
        : null,
    };
    setSaving(true);
    try {
      if (editingId) {
        await update(editingId, data);
        setEditingId(null);
      } else {
        await create(data);
      }
      setForm(EMPTY);
      setFormOpen(false);
    } catch (err) {
      setFormError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id) {
    setActionError('');
    setProjections(prev => { const n = { ...prev }; delete n[id]; return n; });
    setRepaymentProjections(prev => { const n = { ...prev }; delete n[id]; return n; });
    try { await remove(id); } catch (err) { setActionError(err.message); }
  }

  function DebtRepaymentProjectionBlock({ debt }) {
    if (debt.debt_type === 'student_loan') return null;

    if (debt.balance <= 0) {
      return (
        <div className="projection-block projection-block--good">
          <p className="projection-headline">This debt is cleared 🎉</p>
        </div>
      );
    }

    if (!debt.min_payment || debt.min_payment <= 0) {
      return (
        <p className="projection-prompt">
          Add a minimum payment amount to see your payoff projection.
        </p>
      );
    }

    const p = repaymentProjections[debt.id];
    if (!p) return null;

    if (!p.payment_covers_interest) {
      const monthlyInterest = (debt.balance * (debt.interest_rate / 100)) / 12;
      return (
        <div className="projection-block projection-block--warn">
          <p className="projection-headline">
            ⚠️ Your current payment of {gbp(debt.min_payment)}/month doesn't cover the monthly
            interest of {gbp(monthlyInterest)}. Your balance will increase over time — consider
            increasing your payment.
          </p>
        </div>
      );
    }

    if (p.months_to_payoff == null) return null;

    const duration = formatDuration(p.months_to_payoff);
    const age = ageInMonths(dob, p.months_to_payoff);

    return (
      <div className="projection-block projection-block--neutral">
        <p className="projection-headline">
          At your current payment of {gbp(debt.min_payment)}/month, you'll pay off this debt in{' '}
          <strong>{duration}</strong> — by <strong>{p.projected_payoff_date}</strong>
          {age !== null ? ` (when you'll be ${age})` : ''}.
        </p>
        {p.total_interest_to_pay != null && p.total_interest_to_pay > 0 && (
          <p className="projection-note">
            You'll pay {gbp(p.total_interest_to_pay)} in interest.
          </p>
        )}
      </div>
    );
  }

  function planName(id) {
    const plan = loanPlans.find(p => p.id === id);
    return plan ? plan.plan_name : `Plan ${id}`;
  }

  function ageAt(dateStr) {
    if (!dob || !dateStr) return null;
    const birth = new Date(dob);
    const target = new Date(dateStr);
    let age = target.getFullYear() - birth.getFullYear();
    const m = target.getMonth() - birth.getMonth();
    if (m < 0 || (m === 0 && target.getDate() < birth.getDate())) age--;
    return age;
  }

  function ProjectionBlock({ debt }) {
    const p = projections[debt.id];
    if (!p) return null;

    if (p.outcome === 'paid_off') {
      const payoffYear = new Date(p.payoff_date).getFullYear();
      const age = ageAt(p.payoff_date);
      return (
        <div className="projection-block projection-block--good">
          <p className="projection-headline">
            Based on your current salary, you'll clear this loan around{' '}
            <strong>{payoffYear}</strong>
            {age != null ? ` (when you'll be ${age})` : ''}.
          </p>
          <p className="projection-assumption">
            Estimate assumes your current salary ({gbp(p.annual_salary_assumption)}/yr) stays the same
            and today's interest rate doesn't change — your real result will vary.
          </p>
        </div>
      );
    }

    const writeOffYear = new Date(p.write_off_date).getFullYear();
    return (
      <div className="projection-block projection-block--neutral">
        <p className="projection-headline">
          On your current salary, you're unlikely to clear this loan before it's written off
          in <strong>{writeOffYear}</strong>. Estimated remaining balance at that point:{' '}
          <strong>{gbp(p.remaining_balance_at_writeoff)}</strong>.
        </p>
        <p className="projection-note">
          This isn't necessarily bad news — many borrowers are in this position, and the
          remaining balance is simply cancelled with no further action needed.
        </p>
        <p className="projection-assumption">
          Estimate assumes your current salary ({gbp(p.annual_salary_assumption)}/yr) stays the same
          and today's interest rate doesn't change — your real result will vary.
        </p>
      </div>
    );
  }

  return (
    <>
      <NavBar />
      <main className="resource-page">
        <h1 className="page-title">Debts</h1>
        {error && <div className="page-error">{error}</div>}
        {actionError && <div className="error-banner">{actionError}</div>}
        <div className="resource-layout">

          <div className={`card resource-form-card${!formOpen && !editingId ? ' resource-form-card--closed' : ''}`}>
            <button type="button" className="resource-mobile-add-btn" onClick={() => setFormOpen(true)}>+ Add debt</button>
            <p className="card-title">{editingId ? 'Edit debt' : 'Add debt'}</p>
            {formError && <div className="error-banner">{formError}</div>}
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label htmlFor="debt-type">Type</label>
                <select
                  id="debt-type"
                  value={form.debt_type}
                  onChange={e => field('debt_type', e.target.value)}
                >
                  <option value="credit_card">Credit card</option>
                  <option value="mortgage">Mortgage</option>
                  <option value="student_loan">Student loan</option>
                  <option value="other">Other</option>
                </select>
              </div>
              {form.debt_type === 'student_loan' && (
                <>
                  <div className="form-group">
                    <label htmlFor="debt-plan">Student loan plan</label>
                    <select
                      id="debt-plan"
                      value={form.student_loan_plan_id}
                      onChange={e => field('student_loan_plan_id', e.target.value)}
                    >
                      <option value="">Select plan…</option>
                      {loanPlans.map(p => (
                        <option key={p.id} value={p.id}>{p.plan_name}</option>
                      ))}
                    </select>
                  </div>
                  <p className="projection-link">
                    <a href="https://www.gov.uk/sign-in-to-manage-your-student-loan-balance" target="_blank" rel="noopener noreferrer">
                      Sign in to view your student loan balance on <span style={{ whiteSpace: 'nowrap' }}>gov.uk →</span>
                    </a>
                  </p>
                  <div className="form-group">
                    <label htmlFor="debt-grad-year">Year you graduated (or left university)</label>
                    <input
                      id="debt-grad-year"
                      type="number"
                      min="1990"
                      max="2050"
                      step="1"
                      value={form.graduation_year}
                      onChange={e => field('graduation_year', e.target.value)}
                      placeholder="e.g. 2019"
                    />
                    <span className="form-hint">
                      Used to calculate your projected repayment period. Repayments begin April 6 the following year.
                    </span>
                  </div>
                </>
              )}
              <div className="form-group">
                <label htmlFor="debt-balance">Outstanding balance (£)</label>
                <input
                  id="debt-balance"
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.balance}
                  onChange={e => field('balance', e.target.value)}
                  placeholder="e.g. 25000"
                />
              </div>
              <div className="form-group">
                <label htmlFor="debt-rate">Interest rate (%)</label>
                <input
                  id="debt-rate"
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.interest_rate}
                  onChange={e => field('interest_rate', e.target.value)}
                  placeholder="e.g. 7.3"
                />
              </div>
              <div className="form-group">
                <label htmlFor="debt-payment">Monthly minimum payment (£)</label>
                <input
                  id="debt-payment"
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.min_payment}
                  onChange={e => field('min_payment', e.target.value)}
                  placeholder="e.g. 150"
                />
                {form.debt_type === 'student_loan' && (
                  <span className="form-hint">
                    Student loan repayments are calculated automatically from your salary — enter 0 here.
                  </span>
                )}
              </div>
              <div className="form-actions">
                <button type="submit" className="btn-primary" disabled={saving}>
                  {saving ? 'Saving…' : editingId ? 'Save changes' : 'Add debt'}
                </button>
                {editingId && (
                  <button type="button" className="btn-secondary" onClick={cancelEdit}>
                    Cancel
                  </button>
                )}
              </div>
            </form>
          </div>

          <div className="card resource-list-card">
            <p className="card-title">Your debts</p>
            {loading ? (
              <p className="list-empty">Loading…</p>
            ) : items.length === 0 ? (
              <p className="list-empty">No debts recorded.</p>
            ) : (
              <ul className="item-list">
                {items.map(item => (
                  <li key={item.id} className={`item-row${editingId === item.id ? ' item-row--editing' : ''}`}>
                    <div className="item-info">
                      <span className="item-name">
                        {DEBT_TYPE_LABEL[item.debt_type] || item.debt_type}
                        {item.debt_type === 'student_loan' && item.student_loan_plan_id && (
                          <span className="badge badge-neutral">{planName(item.student_loan_plan_id)}</span>
                        )}
                        {item.debt_type === 'student_loan' && item.graduation_year && (
                          <span className="badge badge-neutral">Graduated {item.graduation_year}</span>
                        )}
                      </span>
                      <span className="item-detail">
                        {gbp(item.balance)} balance · {pct(item.interest_rate)} ·{' '}
                        {item.debt_type === 'student_loan' ? 'income-contingent' : `${gbp(item.min_payment)}/mo minimum`}
                      </span>
                    </div>
                    <div className="item-actions">
                      <button className="btn-sm" onClick={() => startEdit(item)}>Edit</button>
                      <button className="btn-sm btn-danger" onClick={() => handleDelete(item.id)}>Delete</button>
                    </div>
                    {item.debt_type === 'student_loan' && item.graduation_year && (
                      <ProjectionBlock debt={item} />
                    )}
                    {item.debt_type === 'student_loan' && !item.graduation_year && (
                      <p className="projection-prompt">
                        Add your graduation year above to see a repayment projection.
                      </p>
                    )}
                    {item.debt_type !== 'student_loan' && (
                      <DebtRepaymentProjectionBlock debt={item} />
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>

        </div>
      </main>
    </>
  );
}
