import { useState } from 'react';
import NavBar from '../components/NavBar';
import InfoTip from '../components/InfoTip';
import { useResource } from '../hooks/useResource';

const EMPTY = { label: '', gross_annual_salary: '' };
const PAY_LABEL = { annual: 'annually', monthly: 'monthly', weekly: 'weekly' };

import { gbp } from '../utils/format';

export default function Income() {
  const { items, loading, error, create, update, remove } = useResource('/api/income');
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
      label: item.label,
      gross_annual_salary: item.gross_annual_salary,
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
    const salary = parseFloat(form.gross_annual_salary);
    if (!form.label.trim()) { setFormError('Label is required.'); return; }
    if (isNaN(salary) || salary <= 0) { setFormError('Enter a valid salary amount.'); return; }

    const data = {
      label: form.label.trim(),
      gross_annual_salary: salary,
      pay_frequency: 'annual',
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
        <h1 className="page-title">Income Sources</h1>
        {error && <div className="page-error">{error}</div>}
        {actionError && <div className="error-banner">{actionError}</div>}
        <div className="resource-layout">

          <div className="card resource-form-card">
            <p className="card-title">{editingId ? 'Edit income source' : 'Add income source'}</p>
            {formError && <div className="error-banner">{formError}</div>}
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label htmlFor="inc-label">Label</label>
                <input
                  id="inc-label"
                  type="text"
                  value={form.label}
                  onChange={e => field('label', e.target.value)}
                  placeholder="e.g. Main salary"
                />
              </div>
              <div className="form-group">
                <label htmlFor="inc-salary"><span className="label-with-tip">Gross annual salary (£)<InfoTip text="Your total salary before any tax, National Insurance, or other deductions are taken off." /></span></label>
                <input
                  id="inc-salary"
                  type="number"
                  min="0"
                  step="1"
                  value={form.gross_annual_salary}
                  onChange={e => field('gross_annual_salary', e.target.value)}
                  placeholder="e.g. 50000"
                />
                <span className="form-hint">Always enter the annual total. £4,000/month = £48,000.</span>
              </div>
              <div className="form-actions">
                <button type="submit" className="btn-primary" disabled={saving}>
                  {saving ? 'Saving…' : editingId ? 'Save changes' : 'Add income source'}
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
            <p className="card-title">Your income sources</p>
            {loading ? (
              <p className="list-empty">Loading…</p>
            ) : items.length === 0 ? (
              <p className="list-empty">No income sources yet — add one to get started.</p>
            ) : (
              <ul className="item-list">
                {items.map(item => (
                  <li key={item.id} className={`item-row${editingId === item.id ? ' item-row--editing' : ''}`}>
                    <div className="item-info">
                      <span className="item-name">{item.label}</span>
                      <span className="item-detail">{gbp(item.gross_annual_salary)}/year · Paid {PAY_LABEL[item.pay_frequency]}</span>
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
