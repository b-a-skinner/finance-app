import { useEffect, useState } from 'react';
import NavBar from '../components/NavBar';
import { useAuth } from '../context/AuthContext';
import { useResource } from '../hooks/useResource';
import { gbp } from '../utils/format';

const EMPTY = { name: '', current_balance: '', target_amount: '', monthly_contribution: '', account_type: '' };

const ACCOUNT_TYPE_OPTIONS = [
  { value: 'cash_savings',       label: 'Cash savings' },
  { value: 'stocks_shares_isa',  label: 'Stocks & Shares ISA' },
  { value: 'lifetime_isa',       label: 'Lifetime ISA' },
  { value: 'investment_account', label: 'Investment account' },
  { value: 'trading_account',    label: 'Trading account' },
  { value: 'other',              label: 'Other' },
];

const ACCOUNT_TYPE_LABEL = Object.fromEntries(ACCOUNT_TYPE_OPTIONS.map(o => [o.value, o.label]));

const INVESTMENT_TYPES = new Set(['stocks_shares_isa', 'lifetime_isa', 'investment_account', 'trading_account']);

function formatDuration(months) {
  const years = Math.floor(months / 12);
  const remainingMonths = months % 12;
  if (years === 0) return `${months} ${months === 1 ? 'month' : 'months'}`;
  if (remainingMonths === 0) return `${years} ${years === 1 ? 'year' : 'years'}`;
  return `${years} ${years === 1 ? 'year' : 'years'}, ${remainingMonths} ${remainingMonths === 1 ? 'month' : 'months'}`;
}

function ageAtGoal(dateOfBirth, monthsToGoal) {
  if (!dateOfBirth) return null;
  const today = new Date();
  const goalDate = new Date(today);
  goalDate.setMonth(goalDate.getMonth() + monthsToGoal);
  const dob = new Date(dateOfBirth);
  let age = goalDate.getFullYear() - dob.getFullYear();
  const m = goalDate.getMonth() - dob.getMonth();
  if (m < 0 || (m === 0 && goalDate.getDate() < dob.getDate())) age--;
  return age;
}

function ProgressBar({ current, target }) {
  const pct = target > 0 ? Math.min(100, (current / target) * 100) : 0;
  return (
    <div className="progress-bar-track" title={`${pct.toFixed(1)}%`}>
      <div className="progress-bar-fill" style={{ width: `${pct}%` }} />
    </div>
  );
}

function ProjectionBlock({ item, projection, dateOfBirth }) {
  if (INVESTMENT_TYPES.has(item.account_type)) {
    return (
      <p className="projection-prompt">
        Projections aren't shown for investment accounts as returns vary with the market.
      </p>
    );
  }

  const hasTarget = item.target_amount != null && item.target_amount > 0;
  if (!hasTarget) return null;

  if (item.current_balance >= item.target_amount) {
    return (
      <div className="projection-block projection-block--good">
        <p className="projection-headline">You've already reached this target 🎉</p>
      </div>
    );
  }

  if (item.monthly_contribution <= 0) {
    return (
      <p className="projection-prompt">
        Add a monthly contribution to see when you'll reach your target.
      </p>
    );
  }

  if (!projection) return null;

  const months = projection.months_to_goal;
  const duration = formatDuration(months);
  const age = ageAtGoal(dateOfBirth, months);

  return (
    <div className="projection-block projection-block--neutral">
      <p className="projection-headline">
        At your current contribution of {gbp(item.monthly_contribution)}/month, you'll reach your
        target in <strong>{duration}</strong> — by <strong>{projection.projected_date}</strong>
        {age !== null ? ` (when you'll be ${age})` : ''}.
      </p>
    </div>
  );
}

export default function Savings() {
  const { apiFetch } = useAuth();
  const { items, loading, error, create, update, remove } = useResource('/api/savings');
  const [projections, setProjections] = useState({});
  const [dateOfBirth, setDateOfBirth] = useState(null);
  const [form, setForm] = useState(EMPTY);
  const [editingId, setEditingId] = useState(null);
  const [formOpen, setFormOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');
  const [actionError, setActionError] = useState('');

  useEffect(() => {
    apiFetch('/api/profile')
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data?.date_of_birth) setDateOfBirth(data.date_of_birth); })
      .catch(() => {});
  }, [apiFetch]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const eligible = items.filter(
      item =>
        !INVESTMENT_TYPES.has(item.account_type) &&
        item.target_amount != null &&
        item.target_amount > 0 &&
        item.monthly_contribution > 0 &&
        item.current_balance < item.target_amount,
    );
    eligible.forEach(item => {
      apiFetch(`/api/savings/${item.id}/projection`)
        .then(r => r.ok ? r.json() : null)
        .then(data => {
          if (data) setProjections(prev => ({ ...prev, [item.id]: data }));
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
      name: item.name,
      current_balance: item.current_balance,
      target_amount: item.target_amount ?? '',
      monthly_contribution: item.monthly_contribution,
      account_type: item.account_type ?? '',
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
    const current = parseFloat(form.current_balance);
    const target = form.target_amount !== '' ? parseFloat(form.target_amount) : null;
    const contrib = parseFloat(form.monthly_contribution);

    if (!form.name.trim()) { setFormError('Name is required.'); return; }
    if (isNaN(current) || current < 0) { setFormError('Enter a valid current balance.'); return; }
    if (target !== null && (isNaN(target) || target < 0)) { setFormError('Enter a valid target amount.'); return; }
    if (isNaN(contrib) || contrib < 0) { setFormError('Enter a valid monthly contribution.'); return; }

    const data = {
      name: form.name.trim(),
      current_balance: current,
      target_amount: target,
      monthly_contribution: contrib,
      account_type: form.account_type || null,
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
    try { await remove(id); } catch (err) { setActionError(err.message); }
  }

  return (
    <>
      <NavBar />
      <main className="resource-page">
        <h1 className="page-title">Savings &amp; Investments</h1>
        {error && <div className="page-error">{error}</div>}
        {actionError && <div className="error-banner">{actionError}</div>}
        <div className="resource-layout">

          <div className={`card resource-form-card${!formOpen && !editingId ? ' resource-form-card--closed' : ''}`}>
            <button type="button" className="resource-mobile-add-btn" onClick={() => setFormOpen(true)}>+ Add account</button>
            <p className="card-title">{editingId ? 'Edit account' : 'Add an account'}</p>
            {formError && <div className="error-banner">{formError}</div>}
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label htmlFor="sav-type">Account type</label>
                <select
                  id="sav-type"
                  value={form.account_type}
                  onChange={e => field('account_type', e.target.value)}
                >
                  <option value="">Select type…</option>
                  {ACCOUNT_TYPE_OPTIONS.map(o => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label htmlFor="sav-name">Name</label>
                <input
                  id="sav-name"
                  type="text"
                  value={form.name}
                  onChange={e => field('name', e.target.value)}
                  placeholder="e.g. Emergency fund, Stocks &amp; Shares ISA"
                />
              </div>
              <div className="form-group">
                <label htmlFor="sav-balance">Current balance (£)</label>
                <input
                  id="sav-balance"
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.current_balance}
                  onChange={e => field('current_balance', e.target.value)}
                  placeholder="e.g. 2500"
                />
              </div>
              <div className="form-group">
                <label htmlFor="sav-target">Target amount (£) <span className="form-hint-inline">(optional)</span></label>
                <input
                  id="sav-target"
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.target_amount}
                  onChange={e => field('target_amount', e.target.value)}
                  placeholder="e.g. 10000"
                />
              </div>
              <div className="form-group">
                <label htmlFor="sav-contrib">Monthly contribution (£)</label>
                <input
                  id="sav-contrib"
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.monthly_contribution}
                  onChange={e => field('monthly_contribution', e.target.value)}
                  placeholder="e.g. 300"
                />
              </div>
              <div className="form-actions">
                <button type="submit" className="btn-primary" disabled={saving}>
                  {saving ? 'Saving…' : editingId ? 'Save changes' : 'Add account'}
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
            <p className="card-title">Your savings &amp; investments</p>
            {loading ? (
              <p className="list-empty">Loading…</p>
            ) : items.length === 0 ? (
              <p className="list-empty">No savings or investment accounts added yet.</p>
            ) : (
              <ul className="item-list">
                {items.map(item => {
                  const hasTarget = item.target_amount != null && item.target_amount > 0;
                  const pct = hasTarget
                    ? Math.min(100, (item.current_balance / item.target_amount) * 100)
                    : 0;
                  return (
                    <li key={item.id} className={`item-row item-row--savings${editingId === item.id ? ' item-row--editing' : ''}`}>
                      <div className="item-info">
                        <span className="item-name">
                          {item.name}
                          {item.account_type && (
                            <span className="badge badge-neutral">{ACCOUNT_TYPE_LABEL[item.account_type] ?? item.account_type}</span>
                          )}
                        </span>
                        <span className="item-detail">
                          {hasTarget
                            ? `${gbp(item.current_balance)} of ${gbp(item.target_amount)} · ${gbp(item.monthly_contribution)}/mo`
                            : `${gbp(item.current_balance)} saved · ${gbp(item.monthly_contribution)}/mo`}
                        </span>
                        {hasTarget && (
                          <div className="savings-progress">
                            <ProgressBar current={item.current_balance} target={item.target_amount} />
                            <span className="savings-pct">{pct.toFixed(1)}%</span>
                          </div>
                        )}
                      </div>
                      <div className="item-actions">
                        <button className="btn-sm" onClick={() => startEdit(item)}>Edit</button>
                        <button className="btn-sm btn-danger" onClick={() => handleDelete(item.id)}>Delete</button>
                      </div>
                      <ProjectionBlock item={item} projection={projections[item.id]} dateOfBirth={dateOfBirth} />
                    </li>
                  );
                })}
              </ul>
            )}
          </div>

        </div>
      </main>
    </>
  );
}
