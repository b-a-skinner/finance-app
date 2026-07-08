import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import NavBar from '../components/NavBar';
import { useAuth } from '../context/AuthContext';
import { gbp } from '../utils/format';

// ---------------------------------------------------------------------------
// Category metadata — label, default allowability, and per-category tip text
// ---------------------------------------------------------------------------

const CATEGORY_INFO = {
  // Allowable by default
  equipment:         { label: 'Equipment',                        allowable: true,  tip: 'Normally an allowable business expense that reduces your corporation tax.' },
  software:          { label: 'Software & subscriptions',         allowable: true,  tip: 'Normally an allowable business expense that reduces your corporation tax.' },
  office:            { label: 'Office costs (rent, utilities)',   allowable: true,  tip: 'Normally an allowable business expense that reduces your corporation tax.' },
  travel:            { label: 'Business travel',                  allowable: true,  tip: 'Normally an allowable business expense that reduces your corporation tax.' },
  professional_fees: { label: 'Professional fees',                allowable: true,  tip: 'Normally an allowable business expense that reduces your corporation tax.' },
  marketing:         { label: 'Marketing & advertising',          allowable: true,  tip: 'Normally an allowable business expense that reduces your corporation tax.' },
  training:          { label: 'Training',                         allowable: true,  tip: "Training that updates skills for your current work is allowable. Training for a completely new trade usually isn't." },
  insurance:         { label: 'Insurance',                        allowable: true,  tip: 'Normally an allowable business expense that reduces your corporation tax.' },
  staff_costs:       { label: 'Staff costs / salaries',           allowable: true,  tip: 'Normally an allowable business expense that reduces your corporation tax.' },
  phone_internet:    { label: 'Phone & internet (business)',      allowable: true,  tip: 'Normally an allowable business expense that reduces your corporation tax.' },
  pension_employer:  { label: 'Pension contributions (employer)', allowable: true,  tip: 'Normally an allowable business expense that reduces your corporation tax.' },
  bank_charges:      { label: 'Bank & finance charges',          allowable: true,  tip: 'Normally an allowable business expense that reduces your corporation tax.' },
  // Non-allowable by default
  client_entertainment: { label: 'Client entertainment',         allowable: false, tip: "Client entertainment can be recorded but isn't tax-deductible — HMRC doesn't allow it to reduce your corporation tax." },
  fines:             { label: 'Fines & penalties',               allowable: false, tip: "Fines and penalties (including parking and speeding) aren't tax-deductible, even if incurred for business." },
  personal:          { label: 'Personal expenses / drawings',    allowable: false, tip: "Personal expenses and drawings don't reduce your business tax bill." },
  political:         { label: 'Political donations',             allowable: false, tip: "Political donations aren't allowable business expenses for tax purposes." },
  // Dual-purpose — user should confirm
  home_office:       { label: 'Home office',                     allowable: false, tip: "Only the business-use portion is claimable. Many directors use HMRC's £6/week flat rate. Adjust the toggle if you're claiming the business proportion." },
  other:             { label: 'Other',                           allowable: false, tip: 'Check with your accountant whether this expense is allowable for corporation tax.' },
};

const ALLOWABLE_CATS     = ['equipment','software','office','travel','professional_fees','marketing','training','insurance','staff_costs','phone_internet','pension_employer','bank_charges'];
const NON_ALLOWABLE_CATS = ['client_entertainment','fines','personal','political'];
const DUAL_CATS          = ['home_office','other'];

function today() {
  return new Date().toISOString().split('T')[0];
}

function formatDate(iso) {
  if (!iso) return '';
  return new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }).format(new Date(iso));
}

// ---------------------------------------------------------------------------
// Inline tooltip
// ---------------------------------------------------------------------------

function Tip({ text }) {
  const [show, setShow] = useState(false);
  return (
    <span
      className="biz-tip-wrap"
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
      onFocus={() => setShow(true)}
      onBlur={() => setShow(false)}
    >
      <button type="button" className="biz-tip-btn" aria-label="More info" tabIndex={0}>ℹ</button>
      {show && <span className="biz-tip-bubble" role="tooltip">{text}</span>}
    </span>
  );
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
      const res = await apiFetch(url, {
        method: item ? 'PATCH' : 'POST',
        body: JSON.stringify({ amount, date_received: form.date_received, description: form.description.trim() || null }),
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

  const initCat = item?.category ?? 'equipment';
  const [form, setForm] = useState({
    amount: item?.amount ?? '',
    date_incurred: item?.date_incurred ?? today(),
    category: initCat,
    description: item?.description ?? '',
    is_allowable: item != null ? item.is_allowable : CATEGORY_INFO[initCat].allowable,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  function field(k, v) { setForm(p => ({ ...p, [k]: v })); }

  function handleCategoryChange(cat) {
    setForm(p => ({ ...p, category: cat, is_allowable: CATEGORY_INFO[cat]?.allowable ?? true }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    const amount = parseFloat(form.amount);
    if (isNaN(amount) || amount <= 0) { setError('Enter a valid amount.'); return; }
    if (!form.date_incurred) { setError('Date is required.'); return; }
    setSaving(true);
    try {
      const url = item ? `/api/business/expenses/${item.id}` : '/api/business/expenses';
      const res = await apiFetch(url, {
        method: item ? 'PATCH' : 'POST',
        body: JSON.stringify({
          amount,
          date_incurred: form.date_incurred,
          category: form.category,
          description: form.description.trim() || null,
          is_allowable: form.is_allowable,
        }),
      });
      if (!res.ok) { const b = await res.json().catch(() => ({})); throw new Error(b.detail || 'Failed to save.'); }
      onSuccess();
    } catch (err) {
      setError(err.message);
      setSaving(false);
    }
  }

  const catInfo = CATEGORY_INFO[form.category] ?? CATEGORY_INFO.other;

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
          <select id="be-cat" value={form.category} onChange={e => handleCategoryChange(e.target.value)}>
            <optgroup label="✓ Allowable expenses">
              {ALLOWABLE_CATS.map(v => <option key={v} value={v}>{CATEGORY_INFO[v].label}</option>)}
            </optgroup>
            <optgroup label="✗ Non-allowable expenses">
              {NON_ALLOWABLE_CATS.map(v => <option key={v} value={v}>{CATEGORY_INFO[v].label}</option>)}
            </optgroup>
            <optgroup label="Dual-purpose — confirm below">
              {DUAL_CATS.map(v => <option key={v} value={v}>{CATEGORY_INFO[v].label}</option>)}
            </optgroup>
          </select>
        </div>
        <div className="form-group">
          <label className="allowable-row-label">
            Allowable for tax
            <Tip text={catInfo.tip} />
          </label>
          <label className="allowable-toggle">
            <input
              type="checkbox"
              checked={form.is_allowable}
              onChange={e => field('is_allowable', e.target.checked)}
            />
            <span className={`allowable-badge${form.is_allowable ? ' allowable-badge--yes' : ' allowable-badge--no'}`}>
              {form.is_allowable ? '✓ Yes — reduces taxable profit' : '✗ No — not tax-deductible'}
            </span>
          </label>
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
// Add buttons
// ---------------------------------------------------------------------------

function AddButtons({ onIncome, onExpense }) {
  return (
    <div className="business-actions">
      <button className="btn-primary" onClick={onIncome}>+ Add income</button>
      <button className="btn-primary" onClick={onExpense}>+ Add expense</button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function Business() {
  const { apiFetch, businessType } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (businessType === null) {
      navigate('/choose-business-type', { replace: true });
    }
  }, [businessType, navigate]);

  const [summary, setSummary] = useState(null);
  const [income, setIncome] = useState([]);
  const [expenses, setExpenses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null);
  const [editItem, setEditItem] = useState(null);
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

  function openIncomeModal()  { setEditItem(null); setModal('income'); }
  function openExpenseModal() { setEditItem(null); setModal('expense'); }
  function closeModal()       { setModal(null); setEditItem(null); }
  function handleSuccess()    { closeModal(); fetchAll(); }

  function startEdit(type, item) { setEditItem({ type, item }); setModal(type); }

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

  const activity = [
    ...income.map(i => ({ ...i, _type: 'income', _date: i.date_received })),
    ...expenses.map(e => ({ ...e, _type: 'expense', _date: e.date_incurred })),
  ]
    .sort((a, b) => b._date.localeCompare(a._date))
    .slice(0, 10);

  const disclaimer = (
    <p className="biz-disclaimer">
      Allowability is based on standard HMRC rules — your situation may differ.
      Speak to an accountant if you&rsquo;re unsure. This is a calculation tool, not tax advice.
    </p>
  );

  if (loading) {
    return (
      <>
        <NavBar />
        <main className="resource-page business-page">
          <p className="list-empty">Loading…</p>
        </main>
      </>
    );
  }

  if (!summary?.has_business_data) {
    return (
      <>
        <NavBar />
        <main className="resource-page business-page">
          <div className="empty-state">
            <h2>Your business finances</h2>
            <p>
              Track your business income and expenses to see your profit position at a glance.
              Log payments individually or as daily totals — whatever suits your business.
            </p>
            <AddButtons onIncome={openIncomeModal} onExpense={openExpenseModal} />
          </div>
          {disclaimer}
        </main>
        {modal === 'income'   && <IncomeModal  onClose={closeModal} onSuccess={handleSuccess} item={null} />}
        {modal === 'expense'  && <ExpenseModal onClose={closeModal} onSuccess={handleSuccess} item={null} />}
      </>
    );
  }

  const cashClass    = summary.cash_profit    >= 0 ? 'business-metric--positive' : 'business-metric--negative';
  const taxableClass = summary.taxable_profit >= 0 ? 'business-metric--positive' : 'business-metric--negative';

  return (
    <>
      <NavBar />
      <main className="resource-page business-page">
        <h1 className="page-title">Business</h1>

        {actionError && <div className="error-banner">{actionError}</div>}

        {/* Expenses breakdown — 3 cards */}
        <div className="cards-grid business-summary-grid">
          <div className="card">
            <p className="card-title">Revenue this year</p>
            <p className="business-metric">{gbp(summary.revenue_ytd)}</p>
          </div>
          <div className="card">
            <p className="card-title">Total expenses</p>
            <p className="business-metric">{gbp(summary.total_expenses_ytd)}</p>
          </div>
          <div className="card">
            <p className="card-title">
              Allowable expenses
              <Tip text="Allowable expenses reduce your taxable profit and therefore your corporation tax bill." />
            </p>
            <p className="business-metric">{gbp(summary.allowable_expenses_ytd)}</p>
          </div>
        </div>

        {/* Profit split — 2 cards */}
        <div className="biz-profit-grid">
          <div className="card">
            <p className="card-title">Money left after all costs</p>
            <p className={`business-metric ${cashClass}`}>{gbp(summary.cash_profit)}</p>
            <p className="biz-metric-sub">Revenue minus all expenses</p>
          </div>
          <div className="card">
            <p className="card-title">
              Taxable profit (estimated)
              <Tip text="Revenue minus allowable expenses only — this is what corporation tax is calculated on." />
            </p>
            <p className={`business-metric ${taxableClass}`}>{gbp(summary.taxable_profit)}</p>
            <p className="biz-metric-sub">Revenue minus allowable expenses only</p>
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
                const catInfo  = CATEGORY_INFO[entry.category];
                const label    = isIncome ? (entry.description || 'Income') : (catInfo?.label ?? entry.category);
                const detail   = [
                  formatDate(entry._date),
                  !isIncome && entry.description ? entry.description : null,
                  !isIncome && !entry.is_allowable ? 'non-allowable' : null,
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

        {disclaimer}
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
