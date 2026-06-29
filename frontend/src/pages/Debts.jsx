import { useEffect, useState } from 'react';
import NavBar from '../components/NavBar';
import { useResource } from '../hooks/useResource';

const EMPTY = {
  debt_type: 'credit_card',
  balance: '',
  interest_rate: '',
  min_payment: '',
  student_loan_plan_id: '',
};

const DEBT_TYPE_LABEL = {
  student_loan: 'Student loan',
  credit_card: 'Credit card',
  other: 'Other',
};

const gbp = n => new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' }).format(n);
const pct = n => `${n}%`;

export default function Debts() {
  const { items, loading, error, create, update, remove } = useResource('/api/debts');
  const [loanPlans, setLoanPlans] = useState([]);
  const [form, setForm] = useState(EMPTY);
  const [editingId, setEditingId] = useState(null);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');
  const [actionError, setActionError] = useState('');

  useEffect(() => {
    fetch('/api/config/student-loan-plans')
      .then(r => r.json())
      .then(setLoanPlans)
      .catch(() => {});
  }, []);

  function field(key, val) {
    setForm(prev => ({ ...prev, [key]: val }));
  }

  function startEdit(item) {
    setEditingId(item.id);
    setForm({
      debt_type: item.debt_type,
      balance: item.balance,
      interest_rate: item.interest_rate,
      min_payment: item.min_payment,
      student_loan_plan_id: item.student_loan_plan_id ?? '',
    });
    setFormError('');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function cancelEdit() {
    setEditingId(null);
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
    } catch (err) {
      setFormError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id) {
    setActionError('');
    try { await remove(id); } catch (err) { setActionError(err.message); }
  }

  function planName(id) {
    const plan = loanPlans.find(p => p.id === id);
    return plan ? plan.plan_name : `Plan ${id}`;
  }

  return (
    <>
      <NavBar />
      <main className="resource-page">
        <h1 className="page-title">Debts</h1>
        {error && <div className="page-error">{error}</div>}
        {actionError && <div className="error-banner">{actionError}</div>}
        <div className="resource-layout">

          <div className="card resource-form-card">
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
                  <option value="student_loan">Student loan</option>
                  <option value="other">Other</option>
                </select>
              </div>
              {form.debt_type === 'student_loan' && (
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
                      </span>
                      <span className="item-detail">
                        {gbp(item.balance)} balance · {pct(item.interest_rate)} · {gbp(item.min_payment)}/mo minimum
                      </span>
                    </div>
                    <div className="item-actions">
                      <button className="btn-sm" onClick={() => startEdit(item)}>Edit</button>
                      <button className="btn-sm btn-danger" onClick={() => handleDelete(item.id)}>Delete</button>
                    </div>
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
