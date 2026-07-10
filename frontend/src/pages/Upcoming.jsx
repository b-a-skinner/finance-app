import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import NavBar from '../components/NavBar';
import { useAuth } from '../context/AuthContext';
import { gbp } from '../utils/format';
import { CATEGORY_INFO, VEHICLE_LABELS, RECURRENCE_LABELS, formatDate, today, fmtMiles } from '../components/BusinessShared';

function entryLabel(entry) {
  if (entry._type === 'income') return entry.description || 'Income';
  if (entry.expense_method === 'mileage') {
    const vLabel = VEHICLE_LABELS[entry.vehicle_type] ?? entry.vehicle_type ?? 'vehicle';
    return `${fmtMiles(entry.business_miles)} miles (${vLabel})`;
  }
  if (entry.expense_method === 'home_office_flat') return 'Home office (flat rate)';
  return CATEGORY_INFO[entry.category]?.label ?? entry.category;
}

function entryAmount(entry) {
  if (entry.expense_method === 'mileage') return `${fmtMiles(entry.business_miles)} miles`;
  return gbp(entry.amount);
}

function ApprovalItem({ entry, apiFetch, onRefresh }) {
  const isIncome = entry._type === 'income';
  const dateKey  = isIncome ? 'date_received' : 'date_incurred';
  const todayStr = today();

  const [amount, setAmount]   = useState(String(entry.amount));
  const [entDate, setEntDate] = useState(entry._date);
  const [saving, setSaving]   = useState(false);
  const [error, setError]     = useState('');

  const willStayScheduled = entDate > todayStr;
  const isMileage = entry.expense_method === 'mileage';

  async function handleApprove() {
    setSaving(true);
    setError('');
    const url = isIncome
      ? `/api/business/income/${entry.id}/approve`
      : `/api/business/expenses/${entry.id}/approve`;
    const body = { [dateKey]: entDate };
    if (!isMileage) body.amount = parseFloat(amount);
    try {
      const res = await apiFetch(url, { method: 'POST', body: JSON.stringify(body) });
      if (!res.ok) { const b = await res.json().catch(() => ({})); throw new Error(b.detail || 'Failed.'); }
      onRefresh();
    } catch (err) {
      setError(err.message);
      setSaving(false);
    }
  }

  async function handleDismiss() {
    setSaving(true);
    setError('');
    const url = isIncome
      ? `/api/business/income/${entry.id}/dismiss`
      : `/api/business/expenses/${entry.id}/dismiss`;
    try {
      const res = await apiFetch(url, { method: 'POST' });
      if (!res.ok) throw new Error('Failed to dismiss.');
      onRefresh();
    } catch (err) {
      setError(err.message);
      setSaving(false);
    }
  }

  return (
    <div className="approval-item">
      <div className="approval-item-header">
        <span className="approval-item-kind">{isIncome ? 'Income' : (CATEGORY_INFO[entry.category]?.label ?? entry.category)}</span>
        <span className="approval-item-type-badge">{isIncome ? 'income' : 'expense'}</span>
      </div>
      {entry.recurrence_freq && (
        <p className="recurrence-badge">
          Recurring {RECURRENCE_LABELS[entry.recurrence_freq]}
          {entry.recurrence_end_date ? `, until ${formatDate(entry.recurrence_end_date)}` : ''}
        </p>
      )}
      {entry.description && (
        <p className="approval-item-desc">{entry.description}</p>
      )}
      {isMileage && (
        <p className="approval-item-desc">{fmtMiles(entry.business_miles)} {VEHICLE_LABELS[entry.vehicle_type] ?? entry.vehicle_type} miles</p>
      )}
      {error && <p className="qa-error">{error}</p>}
      <div className="approval-item-fields">
        {!isMileage && (
          <div className="form-group">
            <label>Amount (£)</label>
            <input type="number" min="0" step="0.01" value={amount}
              onChange={e => setAmount(e.target.value)} />
          </div>
        )}
        <div className="form-group">
          <label>{isIncome ? 'Date received' : 'Date'}</label>
          <input type="date" value={entDate} onChange={e => setEntDate(e.target.value)} />
          {willStayScheduled && (
            <p className="scheduled-flag" style={{ marginTop: '0.25rem' }}>
              New date is still in the future — will reschedule, not confirm.
            </p>
          )}
        </div>
      </div>
      <div className="approval-item-actions">
        <button className="btn-primary" onClick={handleApprove} disabled={saving}>
          {saving ? 'Saving…' : willStayScheduled ? 'Reschedule' : '✓ Approve'}
        </button>
        <button className="approval-dismiss-btn" onClick={handleDismiss} disabled={saving}>
          Dismiss
        </button>
      </div>
    </div>
  );
}

function ScheduledItem({ entry, apiFetch, onRefresh }) {
  const isIncome = entry._type === 'income';
  const [removing, setRemoving] = useState(false);

  async function handleRemove() {
    setRemoving(true);
    const url = isIncome ? `/api/business/income/${entry.id}` : `/api/business/expenses/${entry.id}`;
    await apiFetch(url, { method: 'DELETE' });
    onRefresh();
  }

  return (
    <div className="scheduled-item">
      <div className="scheduled-item-body">
        <div className="scheduled-item-main">
          <span className="scheduled-item-label">{entryLabel(entry)}</span>
          <span className="scheduled-item-date">{formatDate(entry._date)}</span>
          <span className="scheduled-item-amount">{entryAmount(entry)}</span>
        </div>
        {entry.recurrence_freq && (
          <p className="recurrence-badge">
            Recurring {RECURRENCE_LABELS[entry.recurrence_freq]}
            {entry.recurrence_end_date ? `, until ${formatDate(entry.recurrence_end_date)}` : ''}
          </p>
        )}
      </div>
      <button className="scheduled-item-remove" onClick={handleRemove} disabled={removing} aria-label="Remove">
        ×
      </button>
    </div>
  );
}

export default function Upcoming() {
  const { apiFetch, businessType } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (businessType === null) navigate('/choose-business-type', { replace: true });
  }, [businessType, navigate]);

  const [loading, setLoading]   = useState(true);
  const [income, setIncome]     = useState([]);
  const [expenses, setExpenses] = useState([]);

  const fetchUpcoming = useCallback(async () => {
    const res = await apiFetch('/api/business/upcoming');
    if (res.ok) {
      const data = await res.json();
      setIncome(data.income);
      setExpenses(data.expenses);
    }
    setLoading(false);
  }, [apiFetch]);

  useEffect(() => { fetchUpcoming(); }, [fetchUpcoming]);

  if (loading) {
    return (
      <>
        <NavBar />
        <main className="resource-page upcoming-page">
          <p className="list-empty">Loading…</p>
        </main>
      </>
    );
  }

  const todayStr = today();

  const allEntries = [
    ...income.map(e => ({ ...e, _type: 'income',  _date: e.date_received })),
    ...expenses.map(e => ({ ...e, _type: 'expense', _date: e.date_incurred })),
  ];

  const awaiting  = allEntries.filter(e => e._date <= todayStr).sort((a, b) => a._date.localeCompare(b._date));
  const scheduled = allEntries.filter(e => e._date > todayStr).sort((a, b) => a._date.localeCompare(b._date));

  const empty = awaiting.length === 0 && scheduled.length === 0;

  return (
    <>
      <NavBar />
      <main className="resource-page upcoming-page">
        <h1 className="page-title">Upcoming</h1>
        <p className="upcoming-intro">
          Future-dated entries are held here as forecasts — they don't count in your figures until you approve them.
        </p>

        {empty && (
          <p className="list-empty" style={{ marginTop: '2rem' }}>
            Nothing scheduled. Add an income or expense with a future date and it will appear here.
          </p>
        )}

        {awaiting.length > 0 && (
          <section className="upcoming-section">
            <h2 className="upcoming-section-title">To approve</h2>
            <p className="upcoming-section-sub">These entries' dates have passed — confirm the details and approve to count them in your figures, or dismiss if they didn't happen.</p>
            <div className="approval-list">
              {awaiting.map(entry => (
                <ApprovalItem
                  key={`${entry._type}-${entry.id}`}
                  entry={entry}
                  apiFetch={apiFetch}
                  onRefresh={fetchUpcoming}
                />
              ))}
            </div>
          </section>
        )}

        {scheduled.length > 0 && (
          <section className="upcoming-section">
            <h2 className="upcoming-section-title">Scheduled</h2>
            <p className="upcoming-section-sub">These are forecasts — they'll move to "To approve" once their date passes.</p>
            <div className="scheduled-list">
              {scheduled.map(entry => (
                <ScheduledItem
                  key={`${entry._type}-${entry.id}`}
                  entry={entry}
                  apiFetch={apiFetch}
                  onRefresh={fetchUpcoming}
                />
              ))}
            </div>
          </section>
        )}
      </main>
    </>
  );
}
