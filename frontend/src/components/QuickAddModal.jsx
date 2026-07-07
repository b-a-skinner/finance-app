import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { API_BASE } from '../utils/config';

const ACCOUNT_TYPE_OPTIONS = [
  { value: 'cash_savings',       label: 'Cash savings' },
  { value: 'stocks_shares_isa',  label: 'Stocks & Shares ISA' },
  { value: 'lifetime_isa',       label: 'Lifetime ISA' },
  { value: 'investment_account', label: 'Investment account' },
  { value: 'trading_account',    label: 'Trading account' },
  { value: 'other',              label: 'Other' },
];

function ModalShell({ title, moreHref, onClose, children }) {
  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = prev; };
  }, []);

  function handleBackdrop(e) {
    if (e.target === e.currentTarget) onClose();
  }

  return (
    <div className="qa-overlay" onClick={handleBackdrop}>
      <div className="qa-modal" role="dialog" aria-modal="true">
        <div className="qa-handle" />
        <div className="qa-modal-header">
          <h2 className="qa-modal-title">{title}</h2>
          <button className="qa-close" onClick={onClose} aria-label="Close">×</button>
        </div>
        {children}
        {moreHref && (
          <p className="qa-more-link">
            <Link to={moreHref} onClick={onClose}>More options →</Link>
          </p>
        )}
      </div>
    </div>
  );
}

function SavingsModal({ onClose, onSuccess }) {
  const { apiFetch } = useAuth();
  const [form, setForm] = useState({ account_type: '', name: '', current_balance: '', monthly_contribution: '', target_amount: '' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  function field(k, v) { setForm(p => ({ ...p, [k]: v })); }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    const balance = parseFloat(form.current_balance);
    const contrib = form.monthly_contribution !== '' ? parseFloat(form.monthly_contribution) : 0;
    const target  = form.target_amount !== '' ? parseFloat(form.target_amount) : null;
    if (!form.name.trim()) { setError('Name is required.'); return; }
    if (isNaN(balance) || balance < 0) { setError('Enter a valid balance.'); return; }
    if (!isNaN(contrib) && contrib < 0) { setError('Enter a valid monthly contribution.'); return; }
    setSaving(true);
    try {
      const res = await apiFetch('/api/savings', {
        method: 'POST',
        body: JSON.stringify({
          name: form.name.trim(),
          current_balance: balance,
          monthly_contribution: isNaN(contrib) ? 0 : contrib,
          target_amount: target !== null && !isNaN(target) && target >= 0 ? target : null,
          account_type: form.account_type || null,
        }),
      });
      if (!res.ok) { const b = await res.json().catch(() => ({})); throw new Error(b.detail || 'Failed to save.'); }
      onSuccess();
    } catch (err) {
      setError(err.message);
      setSaving(false);
    }
  }

  return (
    <ModalShell title="Add savings account" moreHref="/savings" onClose={onClose}>
      <form onSubmit={handleSubmit} className="qa-form">
        {error && <p className="qa-error">{error}</p>}
        <div className="form-group">
          <label htmlFor="qa-sav-type">Account type</label>
          <select id="qa-sav-type" value={form.account_type} onChange={e => field('account_type', e.target.value)}>
            <option value="">Select type…</option>
            {ACCOUNT_TYPE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
        <div className="form-group">
          <label htmlFor="qa-sav-name">Name</label>
          <input id="qa-sav-name" type="text" value={form.name} onChange={e => field('name', e.target.value)} placeholder="e.g. Emergency fund" autoFocus />
        </div>
        <div className="form-group">
          <label htmlFor="qa-sav-balance">Current balance (£)</label>
          <input id="qa-sav-balance" type="number" min="0" step="0.01" value={form.current_balance} onChange={e => field('current_balance', e.target.value)} placeholder="e.g. 2000" />
        </div>
        <div className="form-group">
          <label htmlFor="qa-sav-contrib">Monthly contribution (£) <span className="form-hint-inline">(optional)</span></label>
          <input id="qa-sav-contrib" type="number" min="0" step="0.01" value={form.monthly_contribution} onChange={e => field('monthly_contribution', e.target.value)} placeholder="e.g. 200" />
        </div>
        <div className="form-group">
          <label htmlFor="qa-sav-target">Target amount (£) <span className="form-hint-inline">(optional)</span></label>
          <input id="qa-sav-target" type="number" min="0" step="0.01" value={form.target_amount} onChange={e => field('target_amount', e.target.value)} placeholder="e.g. 10000" />
        </div>
        <button type="submit" className="btn-primary" disabled={saving}>{saving ? 'Adding…' : 'Add account'}</button>
      </form>
    </ModalShell>
  );
}

function PensionModal({ onClose, onSuccess }) {
  const { apiFetch } = useAuth();
  const [form, setForm] = useState({ name: '', current_balance: '', employee_contribution_pct: '', employer_contribution_pct: '' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  function field(k, v) { setForm(p => ({ ...p, [k]: v })); }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    const balance = parseFloat(form.current_balance);
    const emp = parseFloat(form.employee_contribution_pct);
    const er  = parseFloat(form.employer_contribution_pct);
    if (isNaN(balance) || balance < 0) { setError('Enter a valid balance.'); return; }
    if (isNaN(emp) || emp < 0 || emp > 100) { setError('Employee contribution must be 0–100%.'); return; }
    if (isNaN(er)  || er  < 0 || er  > 100) { setError('Employer contribution must be 0–100%.'); return; }
    setSaving(true);
    try {
      const res = await apiFetch('/api/pension', {
        method: 'POST',
        body: JSON.stringify({ name: form.name.trim() || null, current_balance: balance, employee_contribution_pct: emp, employer_contribution_pct: er }),
      });
      if (!res.ok) { const b = await res.json().catch(() => ({})); throw new Error(b.detail || 'Failed to save.'); }
      onSuccess();
    } catch (err) {
      setError(err.message);
      setSaving(false);
    }
  }

  return (
    <ModalShell title="Add pension" moreHref="/pension" onClose={onClose}>
      <form onSubmit={handleSubmit} className="qa-form">
        {error && <p className="qa-error">{error}</p>}
        <div className="form-group">
          <label htmlFor="qa-pen-name">Name <span className="form-hint-inline">(optional)</span></label>
          <input id="qa-pen-name" type="text" value={form.name} onChange={e => field('name', e.target.value)} placeholder="e.g. Aviva workplace pension" autoFocus />
        </div>
        <div className="form-group">
          <label htmlFor="qa-pen-balance">Current pot value (£)</label>
          <input id="qa-pen-balance" type="number" min="0" step="0.01" value={form.current_balance} onChange={e => field('current_balance', e.target.value)} placeholder="e.g. 15000" />
        </div>
        <div className="form-group">
          <label htmlFor="qa-pen-ee">Your contribution (%)</label>
          <input id="qa-pen-ee" type="number" min="0" max="100" step="0.1" value={form.employee_contribution_pct} onChange={e => field('employee_contribution_pct', e.target.value)} placeholder="e.g. 5" />
        </div>
        <div className="form-group">
          <label htmlFor="qa-pen-er">Employer contribution (%)</label>
          <input id="qa-pen-er" type="number" min="0" max="100" step="0.1" value={form.employer_contribution_pct} onChange={e => field('employer_contribution_pct', e.target.value)} placeholder="e.g. 3" />
        </div>
        <button type="submit" className="btn-primary" disabled={saving}>{saving ? 'Adding…' : 'Add pension'}</button>
      </form>
    </ModalShell>
  );
}

function AssetModal({ onClose, onSuccess }) {
  const { apiFetch } = useAuth();
  const [form, setForm] = useState({ asset_type: 'property', name: '', current_value: '' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  function field(k, v) { setForm(p => ({ ...p, [k]: v })); }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    const value = parseFloat(form.current_value);
    if (!form.name.trim()) { setError('Name is required.'); return; }
    if (isNaN(value) || value < 0) { setError('Enter a valid value.'); return; }
    setSaving(true);
    try {
      const res = await apiFetch('/api/assets', {
        method: 'POST',
        body: JSON.stringify({ name: form.name.trim(), asset_type: form.asset_type, current_value: value }),
      });
      if (!res.ok) { const b = await res.json().catch(() => ({})); throw new Error(b.detail || 'Failed to save.'); }
      onSuccess();
    } catch (err) {
      setError(err.message);
      setSaving(false);
    }
  }

  return (
    <ModalShell title="Add asset" moreHref="/assets" onClose={onClose}>
      <form onSubmit={handleSubmit} className="qa-form">
        {error && <p className="qa-error">{error}</p>}
        <div className="form-group">
          <label htmlFor="qa-asset-type">Type</label>
          <select id="qa-asset-type" value={form.asset_type} onChange={e => field('asset_type', e.target.value)}>
            <option value="property">Property</option>
            <option value="vehicle">Vehicle</option>
            <option value="other">Other</option>
          </select>
        </div>
        <div className="form-group">
          <label htmlFor="qa-asset-name">Name</label>
          <input id="qa-asset-name" type="text" value={form.name} onChange={e => field('name', e.target.value)} placeholder="e.g. Home, Car" autoFocus />
        </div>
        <div className="form-group">
          <label htmlFor="qa-asset-value">Current value (£)</label>
          <input id="qa-asset-value" type="number" min="0" step="1" value={form.current_value} onChange={e => field('current_value', e.target.value)} placeholder="e.g. 250000" />
        </div>
        <button type="submit" className="btn-primary" disabled={saving}>{saving ? 'Adding…' : 'Add asset'}</button>
      </form>
    </ModalShell>
  );
}

function DebtModal({ onClose, onSuccess }) {
  const { apiFetch } = useAuth();
  const [loanPlans, setLoanPlans] = useState([]);
  const [form, setForm] = useState({ debt_type: 'credit_card', balance: '', interest_rate: '', min_payment: '', student_loan_plan_id: '', graduation_year: '' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    fetch(`${API_BASE}/api/config/student-loan-plans`)
      .then(r => r.json())
      .then(setLoanPlans)
      .catch(() => {});
  }, []);

  function field(k, v) { setForm(p => ({ ...p, [k]: v })); }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    const balance = parseFloat(form.balance);
    const rate    = parseFloat(form.interest_rate);
    const minPay  = parseFloat(form.min_payment);
    if (isNaN(balance) || balance < 0) { setError('Enter a valid balance.'); return; }
    if (isNaN(rate) || rate < 0)       { setError('Enter a valid interest rate.'); return; }
    if (isNaN(minPay) || minPay < 0)   { setError('Enter a valid minimum payment.'); return; }
    if (form.debt_type === 'student_loan' && !form.student_loan_plan_id) { setError('Select your student loan plan.'); return; }
    setSaving(true);
    try {
      const res = await apiFetch('/api/debts', {
        method: 'POST',
        body: JSON.stringify({
          debt_type: form.debt_type,
          balance,
          interest_rate: rate,
          min_payment: minPay,
          student_loan_plan_id: form.debt_type === 'student_loan' && form.student_loan_plan_id ? parseInt(form.student_loan_plan_id, 10) : null,
          graduation_year:      form.debt_type === 'student_loan' && form.graduation_year      ? parseInt(form.graduation_year, 10)      : null,
        }),
      });
      if (!res.ok) { const b = await res.json().catch(() => ({})); throw new Error(b.detail || 'Failed to save.'); }
      onSuccess();
    } catch (err) {
      setError(err.message);
      setSaving(false);
    }
  }

  return (
    <ModalShell title="Add debt" moreHref="/debts" onClose={onClose}>
      <form onSubmit={handleSubmit} className="qa-form">
        {error && <p className="qa-error">{error}</p>}
        <div className="form-group">
          <label htmlFor="qa-debt-type">Type</label>
          <select id="qa-debt-type" value={form.debt_type} onChange={e => field('debt_type', e.target.value)}>
            <option value="credit_card">Credit card</option>
            <option value="mortgage">Mortgage</option>
            <option value="student_loan">Student loan</option>
            <option value="other">Other</option>
          </select>
        </div>
        {form.debt_type === 'student_loan' && (
          <>
            <div className="form-group">
              <label htmlFor="qa-debt-plan">Student loan plan</label>
              <select id="qa-debt-plan" value={form.student_loan_plan_id} onChange={e => field('student_loan_plan_id', e.target.value)}>
                <option value="">Select plan…</option>
                {loanPlans.map(p => <option key={p.id} value={p.id}>{p.plan_name}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label htmlFor="qa-debt-grad">Year you graduated (or left university)</label>
              <input id="qa-debt-grad" type="number" min="1990" max="2050" step="1" value={form.graduation_year} onChange={e => field('graduation_year', e.target.value)} placeholder="e.g. 2019" />
            </div>
            <p className="qa-gov-link">
              <a href="https://www.gov.uk/sign-in-to-manage-your-student-loan-balance" target="_blank" rel="noopener noreferrer">
                View your balance on gov.uk →
              </a>
            </p>
          </>
        )}
        <div className="form-group">
          <label htmlFor="qa-debt-balance">Outstanding balance (£)</label>
          <input id="qa-debt-balance" type="number" min="0" step="0.01" value={form.balance} onChange={e => field('balance', e.target.value)} placeholder="e.g. 5000" />
        </div>
        <div className="form-group">
          <label htmlFor="qa-debt-rate">Interest rate (%)</label>
          <input id="qa-debt-rate" type="number" min="0" step="0.01" value={form.interest_rate} onChange={e => field('interest_rate', e.target.value)} placeholder="e.g. 19.9" />
        </div>
        <div className="form-group">
          <label htmlFor="qa-debt-payment">Monthly minimum payment (£)</label>
          <input id="qa-debt-payment" type="number" min="0" step="0.01" value={form.min_payment} onChange={e => field('min_payment', e.target.value)} placeholder="e.g. 50" />
          {form.debt_type === 'student_loan' && (
            <span className="form-hint">Student loan repayments are income-contingent — enter 0 here.</span>
          )}
        </div>
        <button type="submit" className="btn-primary" disabled={saving}>{saving ? 'Adding…' : 'Add debt'}</button>
      </form>
    </ModalShell>
  );
}

function ExpenseModal({ onClose, onSuccess }) {
  const { apiFetch } = useAuth();
  const [form, setForm] = useState({ category: '', amount: '', frequency: 'monthly' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  function field(k, v) { setForm(p => ({ ...p, [k]: v })); }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    const amount = parseFloat(form.amount);
    if (!form.category.trim()) { setError('Category is required.'); return; }
    if (isNaN(amount) || amount <= 0) { setError('Enter a valid amount.'); return; }
    setSaving(true);
    try {
      const res = await apiFetch('/api/expenses', {
        method: 'POST',
        body: JSON.stringify({ category: form.category.trim(), amount, frequency: form.frequency, is_fixed: true }),
      });
      if (!res.ok) { const b = await res.json().catch(() => ({})); throw new Error(b.detail || 'Failed to save.'); }
      onSuccess();
    } catch (err) {
      setError(err.message);
      setSaving(false);
    }
  }

  return (
    <ModalShell title="Add expense" moreHref="/expenses" onClose={onClose}>
      <form onSubmit={handleSubmit} className="qa-form">
        {error && <p className="qa-error">{error}</p>}
        <div className="form-group">
          <label htmlFor="qa-exp-cat">Name</label>
          <input id="qa-exp-cat" type="text" value={form.category} onChange={e => field('category', e.target.value)} placeholder="e.g. Rent, Groceries" autoFocus />
        </div>
        <div className="form-group">
          <label htmlFor="qa-exp-amount">Amount (£)</label>
          <input id="qa-exp-amount" type="number" min="0" step="0.01" value={form.amount} onChange={e => field('amount', e.target.value)} placeholder="e.g. 1200" />
        </div>
        <div className="form-group">
          <label htmlFor="qa-exp-freq">Frequency</label>
          <select id="qa-exp-freq" value={form.frequency} onChange={e => field('frequency', e.target.value)}>
            <option value="monthly">Monthly</option>
            <option value="weekly">Weekly</option>
            <option value="annual">Annual</option>
          </select>
        </div>
        <button type="submit" className="btn-primary" disabled={saving}>{saving ? 'Adding…' : 'Add expense'}</button>
      </form>
    </ModalShell>
  );
}

const MODAL_COMPONENTS = {
  savings: SavingsModal,
  pension: PensionModal,
  asset:   AssetModal,
  debt:    DebtModal,
  expense: ExpenseModal,
};

export default function QuickAddModal({ type, onClose, onSuccess }) {
  const ModalComponent = MODAL_COMPONENTS[type];
  if (!ModalComponent) return null;
  return <ModalComponent onClose={onClose} onSuccess={onSuccess} />;
}
