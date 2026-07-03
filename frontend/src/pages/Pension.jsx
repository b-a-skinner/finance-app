import { useState } from 'react';
import NavBar from '../components/NavBar';
import { useResource } from '../hooks/useResource';

const EMPTY = { current_balance: '', employee_contribution_pct: '', employer_contribution_pct: '' };

import { gbp } from '../utils/format';

export default function Pension() {
  const { items, loading, error, create, update, remove } = useResource('/api/pension');
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
      current_balance: item.current_balance,
      employee_contribution_pct: item.employee_contribution_pct,
      employer_contribution_pct: item.employer_contribution_pct,
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
    const balance = parseFloat(form.current_balance);
    const empEe = parseFloat(form.employee_contribution_pct);
    const empEr = parseFloat(form.employer_contribution_pct);

    if (isNaN(balance) || balance < 0) { setFormError('Enter a valid pension balance.'); return; }
    if (isNaN(empEe) || empEe < 0 || empEe > 100) { setFormError('Employee contribution must be 0–100%.'); return; }
    if (isNaN(empEr) || empEr < 0 || empEr > 100) { setFormError('Employer contribution must be 0–100%.'); return; }

    const data = {
      current_balance: balance,
      employee_contribution_pct: empEe,
      employer_contribution_pct: empEr,
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
        <h1 className="page-title">Pension Pots</h1>
        {error && <div className="page-error">{error}</div>}
        {actionError && <div className="error-banner">{actionError}</div>}
        <div className="resource-layout">

          <div className="card resource-form-card">
            <p className="card-title">{editingId ? 'Edit pension pot' : 'Add pension pot'}</p>
            {formError && <div className="error-banner">{formError}</div>}
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label htmlFor="pen-balance">Current pot value (£)</label>
                <input
                  id="pen-balance"
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.current_balance}
                  onChange={e => field('current_balance', e.target.value)}
                  placeholder="e.g. 15000"
                />
              </div>
              <div className="form-group">
                <label htmlFor="pen-ee">Your contribution (%)</label>
                <input
                  id="pen-ee"
                  type="number"
                  min="0"
                  max="100"
                  step="0.1"
                  value={form.employee_contribution_pct}
                  onChange={e => field('employee_contribution_pct', e.target.value)}
                  placeholder="e.g. 5"
                />
                <span className="form-hint">Percentage of your gross salary you contribute each month.</span>
              </div>
              <div className="form-group">
                <label htmlFor="pen-er">Employer contribution (%)</label>
                <input
                  id="pen-er"
                  type="number"
                  min="0"
                  max="100"
                  step="0.1"
                  value={form.employer_contribution_pct}
                  onChange={e => field('employer_contribution_pct', e.target.value)}
                  placeholder="e.g. 3"
                />
                <span className="form-hint">Minimum statutory employer contribution is 3%.</span>
              </div>
              <div className="form-actions">
                <button type="submit" className="btn-primary" disabled={saving}>
                  {saving ? 'Saving…' : editingId ? 'Save changes' : 'Add pension pot'}
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
            <p className="card-title">Your pension pots</p>
            {loading ? (
              <p className="list-empty">Loading…</p>
            ) : items.length === 0 ? (
              <p className="list-empty">No pension pots yet.</p>
            ) : (
              <ul className="item-list">
                {items.map(item => (
                  <li key={item.id} className={`item-row${editingId === item.id ? ' item-row--editing' : ''}`}>
                    <div className="item-info">
                      <span className="item-name">{gbp(item.current_balance)} pot value</span>
                      <span className="item-detail">
                        You: {item.employee_contribution_pct}% · Employer: {item.employer_contribution_pct}%
                        &nbsp;({item.employee_contribution_pct + item.employer_contribution_pct}% total)
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
