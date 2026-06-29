import { useState } from 'react';
import NavBar from '../components/NavBar';
import { useResource } from '../hooks/useResource';

const EMPTY = { category: '', amount: '', frequency: 'monthly', is_fixed: true };
const FREQ = { annual: 'per year', monthly: 'per month', weekly: 'per week' };

const gbp = n => new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' }).format(n);

export default function Expenses() {
  const { items, loading, error, create, update, remove } = useResource('/api/expenses');
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
      category: item.category,
      amount: item.amount,
      frequency: item.frequency,
      is_fixed: item.is_fixed,
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
    const amount = parseFloat(form.amount);
    if (!form.category.trim()) { setFormError('Category is required.'); return; }
    if (isNaN(amount) || amount <= 0) { setFormError('Enter a valid amount.'); return; }

    const data = {
      category: form.category.trim(),
      amount,
      frequency: form.frequency,
      is_fixed: form.is_fixed,
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
        <h1 className="page-title">Expenses</h1>
        {error && <div className="page-error">{error}</div>}
        {actionError && <div className="error-banner">{actionError}</div>}
        <div className="resource-layout">

          <div className="card resource-form-card">
            <p className="card-title">{editingId ? 'Edit expense' : 'Add expense'}</p>
            {formError && <div className="error-banner">{formError}</div>}
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label htmlFor="exp-cat">Category</label>
                <input
                  id="exp-cat"
                  type="text"
                  value={form.category}
                  onChange={e => field('category', e.target.value)}
                  placeholder="e.g. Rent, Groceries, Utilities"
                />
              </div>
              <div className="form-group">
                <label htmlFor="exp-amount">Amount (£)</label>
                <input
                  id="exp-amount"
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.amount}
                  onChange={e => field('amount', e.target.value)}
                  placeholder="e.g. 1200"
                />
              </div>
              <div className="form-group">
                <label htmlFor="exp-freq">Frequency</label>
                <select
                  id="exp-freq"
                  value={form.frequency}
                  onChange={e => field('frequency', e.target.value)}
                >
                  <option value="monthly">Monthly</option>
                  <option value="annual">Annual</option>
                  <option value="weekly">Weekly</option>
                </select>
              </div>
              <div className="form-group form-check">
                <input
                  id="exp-fixed"
                  type="checkbox"
                  checked={form.is_fixed}
                  onChange={e => field('is_fixed', e.target.checked)}
                />
                <label htmlFor="exp-fixed">Fixed expense (same amount every period)</label>
              </div>
              <div className="form-actions">
                <button type="submit" className="btn-primary" disabled={saving}>
                  {saving ? 'Saving…' : editingId ? 'Save changes' : 'Add expense'}
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
            <p className="card-title">Your expenses</p>
            {loading ? (
              <p className="list-empty">Loading…</p>
            ) : items.length === 0 ? (
              <p className="list-empty">No expenses yet — add one to see your disposable income.</p>
            ) : (
              <ul className="item-list">
                {items.map(item => (
                  <li key={item.id} className={`item-row${editingId === item.id ? ' item-row--editing' : ''}`}>
                    <div className="item-info">
                      <span className="item-name">
                        {item.category}
                        <span className={`badge ${item.is_fixed ? 'badge-neutral' : 'badge-variable'}`}>
                          {item.is_fixed ? 'Fixed' : 'Variable'}
                        </span>
                      </span>
                      <span className="item-detail">{gbp(item.amount)} {FREQ[item.frequency]}</span>
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
