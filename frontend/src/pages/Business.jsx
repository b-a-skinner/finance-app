import { useCallback, useEffect, useRef, useState } from 'react';
import NavBar from '../components/NavBar';
import { useAuth } from '../context/AuthContext';
import { gbp } from '../utils/format';

const CATEGORY_LABEL = {
  equipment: 'Equipment',
  software: 'Software',
  travel: 'Travel',
  office: 'Office',
  professional_fees: 'Professional fees',
  training: 'Training',
  marketing: 'Marketing',
  other: 'Other',
};

const CATEGORY_OPTIONS = Object.entries(CATEGORY_LABEL);

function today() {
  return new Date().toISOString().split('T')[0];
}

function formatDate(iso) {
  if (!iso) return '';
  return new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }).format(new Date(iso));
}

// ---------------------------------------------------------------------------
// Modals
// ---------------------------------------------------------------------------

function ModalShell({ title, onClose, children }) {
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
      </div>
    </div>
  );
}

function IncomeModal({ onClose, onSuccess, item }) {
  const { apiFetch } = useAuth();
  const [form, setForm] = useState({
    amount: item?.amount ?? '',
    date_received: item?.date_received ?? today(),
    description: item?.description ?? '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  function field(k, v) { setForm(p => ({ ...p, [k]: v })); }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    const amount = parseFloat(form.amount);
    if (isNaN(amount) || amount <= 0) { setError('Enter a valid amount.'); return; }
    if (!form.date_received) { setError('Date is required.'); return; }
    setSaving(true);
    try {
      const url = item ? `/api/business/income/${item.id}` : '/api/business/income';
      const method = item ? 'PATCH' : 'POST';
      const res = await apiFetch(url, {
        method,
        body: JSON.stringify({
          amount,
          date_received: form.date_received,
          description: form.description.trim() || null,
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
    <ModalShell title={item ? 'Edit income' : 'Add income'} onClose={onClose}>
      <form onSubmit={handleSubmit} className="qa-form">
        {error && <p className="qa-error">{error}</p>}
        <div className="form-group">
          <label htmlFor="bi-amount">Amount (£)</label>
          <input id="bi-amount" type="number" min="0" step="0.01" value={form.amount} onChange={e => field('amount', e.target.value)} placeholder="e.g. 1500" autoFocus />
        </div>
        <div className="form-group">
          <label htmlFor="bi-date">Date received</label>
          <input id="bi-date" type="date" value={form.date_received} onChange={e => field('date_received', e.target.value)} />
        </div>
        <div className="form-group">
          <label htmlFor="bi-desc">Description <span className="form-hint-inline">(optional)</span></label>
          <input id="bi-desc" type="text" value={form.description} onChange={e => field('description', e.target.value)} placeholder="e.g. Invoice payment, day's takings" />
        </div>
        <button type="submit" className="btn-primary" disabled={saving}>{saving ? 'Saving…' : item ? 'Save changes' : 'Add income'}</button>
      </form>
    </ModalShell>
  );
}

function ExpenseModal({ onClose, onSuccess, item }) {
  const { apiFetch } = useAuth();
  const [form, setForm] = useState({
    amount: item?.amount ?? '',
    date_incurred: item?.date_incurred ?? today(),
    category: item?.category ?? 'other',
    description: item?.description ?? '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  function field(k, v) { setForm(p => ({ ...p, [k]: v })); }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    const amount = parseFloat(form.amount);
    if (isNaN(amount) || amount <= 0) { setError('Enter a valid amount.'); return; }
    if (!form.date_incurred) { setError('Date is required.'); return; }
    setSaving(true);
    try {
      const url = item ? `/api/business/expenses/${item.id}` : '/api/business/expenses';
      const method = item ? 'PATCH' : 'POST';
      const res = await apiFetch(url, {
        method,
        body: JSON.stringify({
          amount,
          date_incurred: form.date_incurred,
          category: form.category,
          description: form.description.trim() || null,
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
    <ModalShell title={item ? 'Edit expense' : 'Add expense'} onClose={onClose}>
      <form onSubmit={handleSubmit} className="qa-form">
        {error && <p className="qa-error">{error}</p>}
        <div className="form-group">
          <label htmlFor="be-amount">Amount (£)</label>
          <input id="be-amount" type="number" min="0" step="0.01" value={form.amount} onChange={e => field('amount', e.target.value)} placeholder="e.g. 299" autoFocus />
        </div>
        <div className="form-group">
          <label htmlFor="be-date">Date</label>
          <input id="be-date" type="date" value={form.date_incurred} onChange={e => field('date_incurred', e.target.value)} />
        </div>
        <div className="form-group">
          <label htmlFor="be-cat">Category</label>
          <select id="be-cat" value={form.category} onChange={e => field('category', e.target.value)}>
            {CATEGORY_OPTIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </div>
        <div className="form-group">
          <label htmlFor="be-desc">Description <span className="form-hint-inline">(optional)</span></label>
          <input id="be-desc" type="text" value={form.description} onChange={e => field('description', e.target.value)} placeholder="e.g. Figma subscription" />
        </div>
        <button type="submit" className="btn-primary" disabled={saving}>{saving ? 'Saving…' : item ? 'Save changes' : 'Add expense'}</button>
      </form>
    </ModalShell>
  );
}

// ---------------------------------------------------------------------------
// Add buttons (reused in both empty state and main view)
// ---------------------------------------------------------------------------

function AddButtons({ onIncome, onExpense }) {
  return (
    <div className="business-actions">
      <button className="btn-primary" onClick={onIncome}>+ Add income</button>
      <button className="btn-secondary" onClick={onExpense}>+ Add expense</button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function Business() {
  const { apiFetch } = useAuth();
  const [summary, setSummary] = useState(null);
  const [income, setIncome] = useState([]);
  const [expenses, setExpenses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null);   // 'income' | 'expense'
  const [editItem, setEditItem] = useState(null); // { type, item }
  const [actionError, setActionError] = useState('');

  const fetchAll = useCallback(async () => {
    const [sRes, iRes, eRes] = await Promise.all([
      apiFetch('/api/business/summary'),
      apiFetch('/api/business/income'),
      apiFetch('/api/business/expenses'),
    ]);
    if (sRes.ok) setSummary(await sRes.json());
    if (iRes.ok) setIncome(await iRes.json());
    if (eRes.ok) setExpenses(await eRes.json());
    setLoading(false);
  }, [apiFetch]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  function openIncomeModal() { setEditItem(null); setModal('income'); }
  function openExpenseModal() { setEditItem(null); setModal('expense'); }
  function closeModal() { setModal(null); setEditItem(null); }

  function handleSuccess() {
    closeModal();
    fetchAll();
  }

  function startEdit(type, item) {
    setEditItem({ type, item });
    setModal(type);
  }

  async function handleDelete(type, id) {
    setActionError('');
    const url = type === 'income' ? `/api/business/income/${id}` : `/api/business/expenses/${id}`;
    try {
      const res = await apiFetch(url, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to delete.');
      fetchAll();
    } catch (err) {
      setActionError(err.message);
    }
  }

  // Merge income + expenses, sort newest first, take top 10
  const activity = [
    ...income.map(i => ({ ...i, _type: 'income', _date: i.date_received })),
    ...expenses.map(e => ({ ...e, _type: 'expense', _date: e.date_incurred })),
  ]
    .sort((a, b) => b._date.localeCompare(a._date))
    .slice(0, 10);

  // ---------------------------------------------------------------------------
  // Loading state
  // ---------------------------------------------------------------------------

  if (loading) {
    return (
      <>
        <NavBar />
        <main className="resource-page">
          <p className="list-empty">Loading…</p>
        </main>
      </>
    );
  }

  // ---------------------------------------------------------------------------
  // First visit — no data yet
  // ---------------------------------------------------------------------------

  if (!summary?.has_business_data) {
    return (
      <>
        <NavBar />
        <main className="resource-page">
          <div className="empty-state">
            <h2>Your business finances</h2>
            <p>
              Track your business income and expenses to see your profit position at a glance.
              Log payments individually or as daily totals — whatever suits your business.
            </p>
            <AddButtons onIncome={openIncomeModal} onExpense={openExpenseModal} />
          </div>
        </main>
        {modal === 'income' && <IncomeModal onClose={closeModal} onSuccess={handleSuccess} item={null} />}
        {modal === 'expense' && <ExpenseModal onClose={closeModal} onSuccess={handleSuccess} item={null} />}
      </>
    );
  }

  // ---------------------------------------------------------------------------
  // Main view
  // ---------------------------------------------------------------------------

  const profitClass = summary.estimated_profit >= 0 ? 'business-metric--positive' : 'business-metric--negative';

  return (
    <>
      <NavBar />
      <main className="resource-page">
        <h1 className="page-title">Business</h1>

        {actionError && <div className="error-banner">{actionError}</div>}

        {/* Summary cards */}
        <div className="cards-grid business-summary-grid">
          <div className="card">
            <p className="card-title">Revenue this year</p>
            <p className="business-metric">{gbp(summary.revenue_ytd)}</p>
          </div>
          <div className="card">
            <p className="card-title">Expenses this year</p>
            <p className="business-metric">{gbp(summary.expenses_ytd)}</p>
          </div>
          <div className="card">
            <p className="card-title">Estimated profit</p>
            <p className={`business-metric ${profitClass}`}>{gbp(summary.estimated_profit)}</p>
          </div>
        </div>

        {/* Action buttons */}
        <AddButtons onIncome={openIncomeModal} onExpense={openExpenseModal} />

        {/* Recent activity */}
        {activity.length > 0 && (
          <div className="card" style={{ marginTop: '1.5rem' }}>
            <p className="card-title">Recent activity</p>
            <ul className="item-list">
              {activity.map(entry => {
                const isIncome = entry._type === 'income';
                const label = isIncome
                  ? (entry.description || 'Income')
                  : (CATEGORY_LABEL[entry.category] || entry.category);
                const detail = [
                  formatDate(entry._date),
                  !isIncome && entry.description ? entry.description : null,
                ].filter(Boolean).join(' · ');

                return (
                  <li key={`${entry._type}-${entry.id}`} className="item-row business-activity-row">
                    <div className="item-info">
                      <span className="item-name">{label}</span>
                      <span className="item-detail">{detail}</span>
                    </div>
                    <span className={`business-amount ${isIncome ? 'business-amount--income' : 'business-amount--expense'}`}>
                      {isIncome ? '+' : '−'}{gbp(entry.amount)}
                    </span>
                    <div className="item-actions">
                      <button className="btn-sm" onClick={() => startEdit(entry._type, entry)}>Edit</button>
                      <button className="btn-sm btn-danger" onClick={() => handleDelete(entry._type, entry.id)}>Delete</button>
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>
        )}
      </main>

      {modal === 'income' && (
        <IncomeModal onClose={closeModal} onSuccess={handleSuccess} item={editItem?.type === 'income' ? editItem.item : null} />
      )}
      {modal === 'expense' && (
        <ExpenseModal onClose={closeModal} onSuccess={handleSuccess} item={editItem?.type === 'expense' ? editItem.item : null} />
      )}
    </>
  );
}
