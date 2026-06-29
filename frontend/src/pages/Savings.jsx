import { useState } from 'react';
import NavBar from '../components/NavBar';
import { useResource } from '../hooks/useResource';

const EMPTY = { name: '', current_balance: '', target_amount: '', monthly_contribution: '' };

const gbp = n => new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' }).format(n);

function ProgressBar({ current, target }) {
  const pct = target > 0 ? Math.min(100, (current / target) * 100) : 0;
  return (
    <div className="progress-bar-track" title={`${pct.toFixed(1)}%`}>
      <div className="progress-bar-fill" style={{ width: `${pct}%` }} />
    </div>
  );
}

export default function Savings() {
  const { items, loading, error, create, update, remove } = useResource('/api/savings');
  const [form, setForm] = useState(EMPTY);
  const [editingId, setEditingId] = useState(null);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');
  const [actionError, setActionError] = useState('');

  function field(key, val) {
    setForm(prev => ({ ...prev, [key]: val }));
  }

  function startEdit(item) {
    setEditingId(item.id);
    setForm({
      name: item.name,
      current_balance: item.current_balance,
      target_amount: item.target_amount,
      monthly_contribution: item.monthly_contribution,
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
    const current = parseFloat(form.current_balance);
    const target = parseFloat(form.target_amount);
    const contrib = parseFloat(form.monthly_contribution);

    if (!form.name.trim()) { setFormError('Name is required.'); return; }
    if (isNaN(current) || current < 0) { setFormError('Enter a valid current balance.'); return; }
    if (isNaN(target) || target <= 0) { setFormError('Enter a valid target amount.'); return; }
    if (isNaN(contrib) || contrib < 0) { setFormError('Enter a valid monthly contribution.'); return; }

    const data = {
      name: form.name.trim(),
      current_balance: current,
      target_amount: target,
      monthly_contribution: contrib,
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

  return (
    <>
      <NavBar />
      <main className="resource-page">
        <h1 className="page-title">Savings Goals</h1>
        {error && <div className="page-error">{error}</div>}
        {actionError && <div className="error-banner">{actionError}</div>}
        <div className="resource-layout">

          <div className="card resource-form-card">
            <p className="card-title">{editingId ? 'Edit savings goal' : 'Add savings goal'}</p>
            {formError && <div className="error-banner">{formError}</div>}
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label htmlFor="sav-name">Goal name</label>
                <input
                  id="sav-name"
                  type="text"
                  value={form.name}
                  onChange={e => field('name', e.target.value)}
                  placeholder="e.g. Emergency fund, House deposit"
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
                <label htmlFor="sav-target">Target amount (£)</label>
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
                  {saving ? 'Saving…' : editingId ? 'Save changes' : 'Add savings goal'}
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
            <p className="card-title">Your savings goals</p>
            {loading ? (
              <p className="list-empty">Loading…</p>
            ) : items.length === 0 ? (
              <p className="list-empty">No savings goals yet.</p>
            ) : (
              <ul className="item-list">
                {items.map(item => {
                  const pct = item.target_amount > 0
                    ? Math.min(100, (item.current_balance / item.target_amount) * 100)
                    : 0;
                  return (
                    <li key={item.id} className={`item-row item-row--savings${editingId === item.id ? ' item-row--editing' : ''}`}>
                      <div className="item-info">
                        <span className="item-name">{item.name}</span>
                        <span className="item-detail">
                          {gbp(item.current_balance)} of {gbp(item.target_amount)} · {gbp(item.monthly_contribution)}/mo
                        </span>
                        <div className="savings-progress">
                          <ProgressBar current={item.current_balance} target={item.target_amount} />
                          <span className="savings-pct">{pct.toFixed(1)}%</span>
                        </div>
                      </div>
                      <div className="item-actions">
                        <button className="btn-sm" onClick={() => startEdit(item)}>Edit</button>
                        <button className="btn-sm btn-danger" onClick={() => handleDelete(item.id)}>Delete</button>
                      </div>
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
