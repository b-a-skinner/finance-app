import { useState } from 'react';
import NavBar from '../components/NavBar';
import { useResource } from '../hooks/useResource';

const EMPTY = { name: '', asset_type: 'property', current_value: '' };

const ASSET_TYPE_LABEL = {
  property: 'Property',
  vehicle: 'Vehicle',
  other: 'Other',
};

import { gbp } from '../utils/format';

export default function Assets() {
  const { items, loading, error, create, update, remove } = useResource('/api/assets');
  const [form, setForm] = useState(EMPTY);
  const [editingId, setEditingId] = useState(null);
  const [formOpen, setFormOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');
  const [actionError, setActionError] = useState('');

  function field(key, val) {
    setForm(prev => ({ ...prev, [key]: val }));
  }

  function startEdit(item) {
    setEditingId(item.id);
    setFormOpen(true);
    setForm({
      name: item.name,
      asset_type: item.asset_type,
      current_value: item.current_value,
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
    const value = parseFloat(form.current_value);
    if (!form.name.trim()) { setFormError('Name is required.'); return; }
    if (isNaN(value) || value < 0) { setFormError('Enter a valid current value.'); return; }

    const data = {
      name: form.name.trim(),
      asset_type: form.asset_type,
      current_value: value,
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
    try { await remove(id); } catch (err) { setActionError(err.message); }
  }

  return (
    <>
      <NavBar />
      <main className="resource-page">
        <h1 className="page-title">Assets</h1>
        {error && <div className="page-error">{error}</div>}
        {actionError && <div className="error-banner">{actionError}</div>}
        <div className="resource-layout">

          <div className={`card resource-form-card${!formOpen && !editingId ? ' resource-form-card--closed' : ''}`}>
            <button type="button" className="resource-mobile-add-btn" onClick={() => setFormOpen(true)}>+ Add asset</button>
            <p className="card-title">{editingId ? 'Edit asset' : 'Add asset'}</p>
            {formError && <div className="error-banner">{formError}</div>}
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label htmlFor="asset-name">Name</label>
                <input
                  id="asset-name"
                  type="text"
                  value={form.name}
                  onChange={e => field('name', e.target.value)}
                  placeholder="e.g. Family home, Car"
                />
              </div>
              <div className="form-group">
                <label htmlFor="asset-type">Type</label>
                <select
                  id="asset-type"
                  value={form.asset_type}
                  onChange={e => field('asset_type', e.target.value)}
                >
                  <option value="property">Property</option>
                  <option value="vehicle">Vehicle</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div className="form-group">
                <label htmlFor="asset-value">Current value (£)</label>
                <input
                  id="asset-value"
                  type="number"
                  min="0"
                  step="1"
                  value={form.current_value}
                  onChange={e => field('current_value', e.target.value)}
                  placeholder="e.g. 300000"
                />
                <span className="form-hint">Use your best estimate of the current market value.</span>
              </div>
              <div className="form-actions">
                <button type="submit" className="btn-primary" disabled={saving}>
                  {saving ? 'Saving…' : editingId ? 'Save changes' : 'Add asset'}
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
            <p className="card-title">Your assets</p>
            {loading ? (
              <p className="list-empty">Loading…</p>
            ) : items.length === 0 ? (
              <p className="list-empty">No assets yet — add property, vehicles, or other valuables.</p>
            ) : (
              <ul className="item-list">
                {items.map(item => (
                  <li key={item.id} className={`item-row${editingId === item.id ? ' item-row--editing' : ''}`}>
                    <div className="item-info">
                      <span className="item-name">
                        {item.name}
                        <span className="badge badge-neutral">{ASSET_TYPE_LABEL[item.asset_type] || item.asset_type}</span>
                      </span>
                      <span className="item-detail">{gbp(item.current_value)}</span>
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
