import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import NavBar from '../components/NavBar';
import { useAuth } from '../context/AuthContext';
import { gbp } from '../utils/format';
import { formatDate, today } from '../components/BusinessShared';
import { statusLabel, chaseMessage, daysOverdue } from '../utils/invoices';

function StatusBadge({ status }) {
  return <span className={`badge badge-invoice-${status}`}>{statusLabel(status)}</span>;
}

function ChasePanel({ invoice, onClose }) {
  const [copied, setCopied] = useState(false);
  const message = chaseMessage(invoice, today());

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(message);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="qa-overlay" onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="qa-modal" role="dialog" aria-modal="true">
        <div className="qa-modal-header">
          <h2 className="qa-modal-title">Chase {invoice.invoice_number}</h2>
          <button className="qa-close" onClick={onClose} aria-label="Close">×</button>
        </div>
        <p className="upcoming-section-sub" style={{ marginBottom: '0.75rem' }}>
          A draft reminder — copy it and send it yourself. We never email your clients for you.
        </p>
        <textarea className="chase-message-box" readOnly rows={9} value={message} />
        <button type="button" className="btn-primary" onClick={handleCopy} style={{ marginTop: '0.75rem' }}>
          {copied ? 'Copied ✓' : 'Copy message'}
        </button>
      </div>
    </div>
  );
}

export default function Invoices() {
  const { apiFetch, businessType } = useAuth();
  const navigate = useNavigate();
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [chaseTarget, setChaseTarget] = useState(null);

  useEffect(() => {
    if (businessType === null) navigate('/choose-business-type', { replace: true });
  }, [businessType, navigate]);

  const fetchInvoices = useCallback(() => {
    apiFetch('/api/business/invoices')
      .then(r => r.ok ? r.json() : [])
      .then(setInvoices)
      .finally(() => setLoading(false));
  }, [apiFetch]);

  useEffect(() => { fetchInvoices(); }, [fetchInvoices]);

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

  const overdue = invoices.filter(i => i.effective_status === 'overdue');
  const todayStr = today();

  return (
    <>
      <NavBar />
      <main className="resource-page upcoming-page">
        <div className="business-header-row">
          <h1 className="page-title">Invoices</h1>
          <Link to="/invoices/new" className="btn-primary" style={{ width: 'auto', margin: 0 }}>
            + New invoice
          </Link>
        </div>

        {overdue.length > 0 && (
          <p className="tax-config-missing-banner">
            {overdue.length === 1 ? (
              <>Invoice {overdue[0].invoice_number} to {overdue[0].contact.name} is {daysOverdue(overdue[0].due_date, todayStr)} days overdue.</>
            ) : (
              <>{overdue.length} invoices are overdue — chase them below to keep cash flowing.</>
            )}
          </p>
        )}

        {invoices.length === 0 ? (
          <p className="list-empty" style={{ marginTop: '2rem' }}>
            No invoices yet. Create your first one to start tracking payments.
          </p>
        ) : (
          <div className="card">
            <ul className="item-list">
              {invoices.map(inv => (
                <li key={inv.id} className="item-row">
                  <div className="item-info">
                    <span className="item-name">
                      {inv.invoice_number} — {inv.contact.name}
                      <StatusBadge status={inv.effective_status} />
                    </span>
                    <span className="item-detail">Due {formatDate(inv.due_date)}</span>
                  </div>
                  <span className="business-amount">{gbp(inv.total)}</span>
                  <div className="item-actions">
                    {inv.effective_status === 'overdue' && (
                      <button className="btn-sm" onClick={() => setChaseTarget(inv)}>Chase</button>
                    )}
                    <Link className="btn-sm" to={`/invoices/${inv.id}`}>
                      {inv.status === 'paid' ? 'View' : 'Edit'}
                    </Link>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </main>

      {chaseTarget && <ChasePanel invoice={chaseTarget} onClose={() => setChaseTarget(null)} />}
    </>
  );
}
