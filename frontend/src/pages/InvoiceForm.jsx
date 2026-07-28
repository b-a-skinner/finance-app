import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import NavBar from '../components/NavBar';
import { useAuth } from '../context/AuthContext';
import { gbp } from '../utils/format';
import { today } from '../components/BusinessShared';
import { computeTotals, isBankDetailsIncomplete, statusLabel, chaseMessage, daysOverdue } from '../utils/invoices';

const EMPTY_LINE_ITEM = { description: '', quantity: 1, unit_price: '' };
const NEW_CONTACT_VALUE = '__new__';

function LineItemsEditor({ lineItems, onChange }) {
  function updateItem(i, key, val) {
    const next = lineItems.slice();
    next[i] = { ...next[i], [key]: val };
    onChange(next);
  }
  function addItem() { onChange([...lineItems, { ...EMPTY_LINE_ITEM }]); }
  function removeItem(i) { onChange(lineItems.filter((_, idx) => idx !== i)); }

  return (
    <div className="invoice-line-items">
      <div className="invoice-line-items-header">
        <span>Description</span>
        <span>Qty / hrs</span>
        <span>Unit price (£)</span>
        <span></span>
      </div>
      {lineItems.map((li, i) => (
        <div className="invoice-line-item-row" key={i}>
          <input
            type="text"
            value={li.description}
            onChange={e => updateItem(i, 'description', e.target.value)}
            placeholder="e.g. 6 Instagram pictures"
          />
          <input
            type="number" min="0" step="0.5"
            value={li.quantity}
            onChange={e => updateItem(i, 'quantity', e.target.value)}
          />
          <input
            type="number" min="0" step="0.01"
            value={li.unit_price}
            onChange={e => updateItem(i, 'unit_price', e.target.value)}
          />
          <button type="button" className="btn-sm btn-danger" onClick={() => removeItem(i)} disabled={lineItems.length <= 1}>
            Remove
          </button>
        </div>
      ))}
      <button type="button" className="btn-sm" onClick={addItem}>+ Add line item</button>
    </div>
  );
}

export default function InvoiceForm() {
  const { apiFetch } = useAuth();
  const navigate = useNavigate();
  const { id } = useParams();
  const isEdit = !!id;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const [profile, setProfile] = useState(null);
  const [contacts, setContacts] = useState([]);
  const [invoice, setInvoice] = useState(null); // existing invoice, when editing

  const [contactSel, setContactSel] = useState('');
  const [newContact, setNewContact] = useState({ name: '', address: '', email: '' });
  const [issueDate, setIssueDate] = useState(today());
  const [dueDate, setDueDate] = useState(today());
  const [notes, setNotes] = useState('');
  const [lineItems, setLineItems] = useState([{ ...EMPTY_LINE_ITEM }]);
  const [paidDate, setPaidDate] = useState(today());
  const [showChase, setShowChase] = useState(false);
  const [copied, setCopied] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    const [profileRes, contactsRes] = await Promise.all([
      apiFetch('/api/profile'),
      apiFetch('/api/business/contacts'),
    ]);
    if (profileRes.ok) setProfile(await profileRes.json());
    if (contactsRes.ok) setContacts(await contactsRes.json());

    if (isEdit) {
      const r = await apiFetch(`/api/business/invoices/${id}`);
      if (!r.ok) { setError('Invoice not found.'); setLoading(false); return; }
      const data = await r.json();
      setInvoice(data);
      setContactSel(String(data.contact.id));
      setIssueDate(data.issue_date);
      setDueDate(data.due_date);
      setNotes(data.notes ?? '');
      setLineItems(data.line_items.map(li => ({ description: li.description, quantity: li.quantity, unit_price: li.unit_price })));
    }
    setLoading(false);
  }, [apiFetch, id, isEdit]);

  useEffect(() => { load(); }, [load]);

  function validLineItems() {
    return lineItems
      .map(li => ({ description: li.description.trim(), quantity: parseFloat(li.quantity), unit_price: parseFloat(li.unit_price) }))
      .filter(li => li.description && !isNaN(li.quantity) && li.quantity > 0 && !isNaN(li.unit_price) && li.unit_price >= 0);
  }

  async function resolveContactId() {
    if (contactSel === NEW_CONTACT_VALUE) {
      if (!newContact.name.trim()) { setError('Enter a name for the new contact.'); return null; }
      const res = await apiFetch('/api/business/contacts', {
        method: 'POST',
        body: JSON.stringify({
          name: newContact.name.trim(),
          address: newContact.address.trim() || null,
          email: newContact.email.trim() || null,
        }),
      });
      if (!res.ok) { setError('Failed to save the new contact.'); return null; }
      const created = await res.json();
      setContacts(prev => [...prev, created].sort((a, b) => a.name.localeCompare(b.name)));
      setContactSel(String(created.id));
      return created.id;
    }
    return contactSel ? parseInt(contactSel, 10) : null;
  }

  async function handleCreate(status) {
    setError('');
    const items = validLineItems();
    if (items.length === 0) { setError('Add at least one valid line item.'); return; }
    const contactId = await resolveContactId();
    if (!contactId) { if (!error) setError('Choose or add a client.'); return; }

    setSaving(true);
    try {
      const res = await apiFetch('/api/business/invoices', {
        method: 'POST',
        body: JSON.stringify({
          contact_id: contactId, issue_date: issueDate, due_date: dueDate,
          notes: notes.trim() || null, line_items: items, status,
        }),
      });
      if (!res.ok) { const b = await res.json().catch(() => ({})); throw new Error(b.detail || 'Failed to save.'); }
      const created = await res.json();
      navigate(`/invoices/${created.id}`, { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleSaveChanges() {
    setError('');
    const items = validLineItems();
    if (items.length === 0) { setError('Add at least one valid line item.'); return; }
    const contactId = await resolveContactId();
    if (!contactId) { if (!error) setError('Choose or add a client.'); return; }

    setSaving(true);
    try {
      const res = await apiFetch(`/api/business/invoices/${id}`, {
        method: 'PATCH',
        body: JSON.stringify({
          contact_id: contactId, issue_date: issueDate, due_date: dueDate,
          notes: notes.trim() || null, line_items: items,
        }),
      });
      if (!res.ok) { const b = await res.json().catch(() => ({})); throw new Error(b.detail || 'Failed to save.'); }
      setInvoice(await res.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleMarkSent() {
    setSaving(true);
    try {
      const res = await apiFetch(`/api/business/invoices/${id}/send`, { method: 'POST' });
      if (res.ok) setInvoice(await res.json());
    } finally {
      setSaving(false);
    }
  }

  async function handleMarkPaid() {
    setSaving(true);
    try {
      const res = await apiFetch(`/api/business/invoices/${id}/paid`, {
        method: 'POST',
        body: JSON.stringify({ paid_date: paidDate }),
      });
      if (res.ok) setInvoice(await res.json());
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!window.confirm('Delete this invoice? This cannot be undone.')) return;
    setSaving(true);
    try {
      const res = await apiFetch(`/api/business/invoices/${id}`, { method: 'DELETE' });
      if (res.ok) navigate('/invoices', { replace: true });
      else { const b = await res.json().catch(() => ({})); setError(b.detail || 'Failed to delete.'); }
    } finally {
      setSaving(false);
    }
  }

  async function handleDownloadPdf() {
    const res = await apiFetch(`/api/business/invoices/${id}/pdf`);
    if (!res.ok) { setError('Failed to generate PDF.'); return; }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${invoice?.invoice_number ?? 'invoice'}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  async function handleCopyChase() {
    try {
      await navigator.clipboard.writeText(chaseMessage(invoice, today()));
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  if (loading) {
    return (
      <>
        <NavBar />
        <main className="resource-page"><p className="list-empty">Loading…</p></main>
      </>
    );
  }

  const isPaid = invoice?.status === 'paid';
  const isReadOnly = isPaid;
  const vatRegistered = invoice ? invoice.vat_registered : !!profile?.vat_registered;
  const totals = computeTotals(validLineItems(), vatRegistered);
  const bankMissing = isBankDetailsIncomplete(profile);

  return (
    <>
      <NavBar />
      <main className="resource-page">
        <h1 className="page-title">
          {isEdit ? `Invoice ${invoice?.invoice_number ?? ''}` : 'New invoice'}
          {invoice && <span className={`badge badge-invoice-${invoice.effective_status}`} style={{ marginLeft: '0.6rem', verticalAlign: 'middle' }}>{statusLabel(invoice.effective_status)}</span>}
        </h1>

        {bankMissing && !isPaid && (
          <p className="tax-config-missing-banner">
            Add your bank details in <a href="/profile">Profile</a> so clients know how to pay you.
          </p>
        )}

        {error && <div className="error-banner">{error}</div>}

        <div className="resource-layout resource-layout--single">
          <div className="card resource-form-card">
            <div className="form-group">
              <label htmlFor="inv-contact">Client</label>
              <select
                id="inv-contact"
                value={contactSel}
                onChange={e => setContactSel(e.target.value)}
                disabled={isReadOnly}
              >
                <option value="">— Select a client —</option>
                {contacts.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                {!isReadOnly && <option value={NEW_CONTACT_VALUE}>+ Add new client</option>}
              </select>
            </div>

            {contactSel === NEW_CONTACT_VALUE && (
              <div className="card" style={{ marginBottom: '1.125rem', boxShadow: 'none', border: '1px dashed var(--color-border)' }}>
                <div className="form-group">
                  <label htmlFor="nc-name">Client name</label>
                  <input id="nc-name" type="text" value={newContact.name} onChange={e => setNewContact(p => ({ ...p, name: e.target.value }))} />
                </div>
                <div className="form-group">
                  <label htmlFor="nc-address">Address <span className="form-hint-inline">(optional)</span></label>
                  <textarea id="nc-address" rows={2} value={newContact.address} onChange={e => setNewContact(p => ({ ...p, address: e.target.value }))} />
                </div>
                <div className="form-group">
                  <label htmlFor="nc-email">Email <span className="form-hint-inline">(optional)</span></label>
                  <input id="nc-email" type="email" value={newContact.email} onChange={e => setNewContact(p => ({ ...p, email: e.target.value }))} />
                </div>
              </div>
            )}

            <div className="invoice-dates-row">
              <div className="form-group">
                <label htmlFor="inv-issue">Issue date</label>
                <input id="inv-issue" type="date" value={issueDate} onChange={e => setIssueDate(e.target.value)} disabled={isReadOnly} />
              </div>
              <div className="form-group">
                <label htmlFor="inv-due">Due date</label>
                <input id="inv-due" type="date" value={dueDate} onChange={e => setDueDate(e.target.value)} disabled={isReadOnly} />
              </div>
            </div>

            <div className="form-group">
              <label>Line items</label>
              {isReadOnly ? (
                <ul className="item-list">
                  {invoice.line_items.map(li => (
                    <li className="item-row" key={li.id}>
                      <div className="item-info">
                        <span className="item-name">{li.description}</span>
                        <span className="item-detail">{li.quantity} × {gbp(li.unit_price)}</span>
                      </div>
                      <span className="business-amount">{gbp(li.line_total)}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <LineItemsEditor lineItems={lineItems} onChange={setLineItems} />
              )}
            </div>

            <div className="invoice-totals">
              <div className="invoice-totals-row"><span>Subtotal</span><span>{gbp(totals.subtotal)}</span></div>
              {vatRegistered && <div className="invoice-totals-row"><span>VAT (20%)</span><span>{gbp(totals.vatAmount)}</span></div>}
              <div className="invoice-totals-row invoice-totals-row--final"><span>Total</span><span>{gbp(totals.total)}</span></div>
            </div>

            <div className="form-group">
              <label htmlFor="inv-notes">Notes <span className="form-hint-inline">(optional)</span></label>
              <textarea id="inv-notes" rows={2} value={notes} onChange={e => setNotes(e.target.value)} disabled={isReadOnly} />
            </div>

            {!isReadOnly && !isEdit && (
              <div className="form-actions" style={{ flexDirection: 'column', gap: '0.5rem' }}>
                <button type="button" className="btn-primary" onClick={() => handleCreate('draft')} disabled={saving} style={{ marginTop: 0 }}>
                  {saving ? 'Saving…' : 'Save as draft'}
                </button>
                <button type="button" className="btn-primary" onClick={() => handleCreate('sent')} disabled={saving} style={{ marginTop: 0 }}>
                  {saving ? 'Saving…' : 'Save and mark as sent'}
                </button>
              </div>
            )}

            {!isReadOnly && isEdit && (
              <div className="form-actions">
                <button type="button" className="btn-primary" onClick={handleSaveChanges} disabled={saving}>
                  {saving ? 'Saving…' : 'Save changes'}
                </button>
              </div>
            )}

            {isEdit && invoice && (
              <div className="modal-danger-zone" style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                {invoice.status === 'draft' && (
                  <button type="button" className="btn-sm" onClick={handleMarkSent} disabled={saving}>Mark as sent</button>
                )}
                {invoice.status !== 'paid' && (
                  <div className="invoice-mark-paid-row">
                    <input type="date" value={paidDate} onChange={e => setPaidDate(e.target.value)} />
                    <button type="button" className="btn-sm" onClick={handleMarkPaid} disabled={saving}>Mark as paid</button>
                  </div>
                )}
                <button type="button" className="btn-sm" onClick={handleDownloadPdf}>Download PDF</button>
                {invoice.effective_status === 'overdue' && (
                  <button type="button" className="btn-sm" onClick={() => setShowChase(v => !v)}>
                    {showChase ? 'Hide reminder' : 'Chase this invoice'}
                  </button>
                )}
                {showChase && (
                  <>
                    <textarea className="chase-message-box" readOnly rows={9} value={chaseMessage(invoice, today())} />
                    <button type="button" className="btn-sm" onClick={handleCopyChase}>{copied ? 'Copied ✓' : 'Copy message'}</button>
                  </>
                )}
                {invoice.status !== 'paid' && (
                  <button type="button" className="btn-sm btn-danger" onClick={handleDelete} disabled={saving}>Delete invoice</button>
                )}
              </div>
            )}
          </div>
        </div>
      </main>
    </>
  );
}
