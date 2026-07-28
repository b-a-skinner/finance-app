import { useCallback, useEffect, useState } from 'react';
import NavBar from '../components/NavBar';
import { useAuth } from '../context/AuthContext';

const BUSINESS_TYPE_LABELS = {
  sole_trader:     'Sole trader',
  limited_company: 'Limited company',
  partnership:     'Partnership',
  llp:             'Limited liability partnership (LLP)',
  not_sure:        'Not sure yet',
};

const INVOICING_EMPTY = {
  business_name: '',
  business_address: '',
  bank_account_name: '',
  bank_sort_code: '',
  bank_account_number: '',
  vat_registered: false,
  vat_number: '',
};

export default function BusinessProfile() {
  const { apiFetch, setBusinessType: ctxSetBusinessType } = useAuth();
  const [businessTypeSel, setBusinessTypeSel] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const [invoicing, setInvoicing] = useState(INVOICING_EMPTY);
  const [invoicingError, setInvoicingError] = useState('');
  const [invoicingSaving, setInvoicingSaving] = useState(false);
  const [invoicingSaved, setInvoicingSaved] = useState(false);

  const load = useCallback(() => {
    apiFetch('/api/profile')
      .then(r => r.json())
      .then(data => {
        setBusinessTypeSel(data.business_type ?? '');
        setInvoicing({
          business_name: data.business_name ?? '',
          business_address: data.business_address ?? '',
          bank_account_name: data.bank_account_name ?? '',
          bank_sort_code: data.bank_sort_code ?? '',
          bank_account_number: data.bank_account_number ?? '',
          vat_registered: !!data.vat_registered,
          vat_number: data.vat_number ?? '',
        });
      })
      .catch(() => setError('Failed to load profile.'))
      .finally(() => setLoading(false));
  }, [apiFetch]);

  useEffect(() => { load(); }, [load]);

  async function handleSave() {
    setSaving(true);
    setSaved(false);
    try {
      const res = await apiFetch('/api/profile', {
        method: 'PATCH',
        body: JSON.stringify({ business_type: businessTypeSel || null }),
      });
      if (res.ok) {
        ctxSetBusinessType(businessTypeSel || null);
        setSaved(true);
      }
    } finally {
      setSaving(false);
    }
  }

  function invoicingField(key, val) {
    setInvoicing(prev => ({ ...prev, [key]: val }));
    setInvoicingSaved(false);
  }

  async function handleInvoicingSave() {
    setInvoicingError('');
    setInvoicingSaved(false);
    if (invoicing.vat_registered && !invoicing.vat_number.trim()) {
      setInvoicingError('Enter your VAT number, or turn off VAT registered.');
      return;
    }
    setInvoicingSaving(true);
    try {
      const res = await apiFetch('/api/profile', {
        method: 'PATCH',
        body: JSON.stringify({
          business_name: invoicing.business_name.trim() || null,
          business_address: invoicing.business_address.trim() || null,
          bank_account_name: invoicing.bank_account_name.trim() || null,
          bank_sort_code: invoicing.bank_sort_code.trim() || null,
          bank_account_number: invoicing.bank_account_number.trim() || null,
          vat_registered: invoicing.vat_registered,
          vat_number: invoicing.vat_registered ? invoicing.vat_number.trim() : null,
        }),
      });
      if (res.ok) {
        setInvoicingSaved(true);
      } else {
        const body = await res.json().catch(() => ({}));
        setInvoicingError(body.detail || 'Failed to save.');
      }
    } catch {
      setInvoicingError('Network error — please try again.');
    } finally {
      setInvoicingSaving(false);
    }
  }

  if (loading) {
    return (
      <>
        <NavBar />
        <div className="page-loading">Loading…</div>
      </>
    );
  }

  return (
    <>
      <NavBar />
      <main className="resource-page">
        <h1 className="page-title">Profile</h1>
        {error && <div className="page-error">{error}</div>}
        <div className="resource-layout resource-layout--single">
          <div className="card">
            <p className="card-title">Business</p>
            <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', marginBottom: '1.25rem' }}>
              Used to tailor business features as they roll out. Doesn't affect any calculations.
            </p>
            <div className="form-group">
              <label htmlFor="business-type">Business type</label>
              <select
                id="business-type"
                value={businessTypeSel}
                onChange={e => { setBusinessTypeSel(e.target.value); setSaved(false); }}
              >
                <option value="">— Select —</option>
                {Object.entries(BUSINESS_TYPE_LABELS).map(([v, l]) => (
                  <option key={v} value={v}>{l}</option>
                ))}
              </select>
            </div>
            <div className="form-actions">
              <button type="button" className="btn-primary" onClick={handleSave} disabled={saving}>
                {saving ? 'Saving…' : 'Save'}
              </button>
              {saved && (
                <span style={{ color: 'var(--color-positive)', fontSize: '0.9rem', alignSelf: 'center' }}>
                  Saved ✓
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="resource-layout resource-layout--single" style={{ marginTop: '1.5rem' }}>
          <div className="card">
            <p className="card-title">Invoicing details</p>
            <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', marginBottom: '1.25rem' }}>
              Shown on invoices you send to clients. All optional, but a client can't pay you without your bank details.
            </p>
            {invoicingError && <div className="error-banner">{invoicingError}</div>}

            <div className="form-group">
              <label htmlFor="inv-business-name">Business name</label>
              <input
                id="inv-business-name"
                type="text"
                value={invoicing.business_name}
                onChange={e => invoicingField('business_name', e.target.value)}
                placeholder="e.g. your name or trading name"
              />
            </div>
            <div className="form-group">
              <label htmlFor="inv-business-address">Business address</label>
              <textarea
                id="inv-business-address"
                rows={3}
                value={invoicing.business_address}
                onChange={e => invoicingField('business_address', e.target.value)}
                placeholder={'Street\nCity\nPostcode'}
              />
            </div>

            <div className="form-group">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={invoicing.vat_registered}
                  onChange={e => invoicingField('vat_registered', e.target.checked)}
                />
                VAT registered
              </label>
            </div>
            {invoicing.vat_registered && (
              <div className="form-group">
                <label htmlFor="inv-vat-number">VAT number</label>
                <input
                  id="inv-vat-number"
                  type="text"
                  value={invoicing.vat_number}
                  onChange={e => invoicingField('vat_number', e.target.value)}
                  placeholder="e.g. GB123456789"
                />
                <span className="form-hint">20% VAT will be added automatically to every invoice you create.</span>
              </div>
            )}

            <p className="card-title" style={{ fontSize: '0.9rem', marginTop: '1.5rem' }}>Bank details</p>
            <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', marginBottom: '1rem' }}>
              Shown on invoices so clients know how to pay you.
            </p>
            <div className="form-group">
              <label htmlFor="inv-bank-name">Account name</label>
              <input
                id="inv-bank-name"
                type="text"
                value={invoicing.bank_account_name}
                onChange={e => invoicingField('bank_account_name', e.target.value)}
              />
            </div>
            <div className="form-group">
              <label htmlFor="inv-sort-code">Sort code</label>
              <input
                id="inv-sort-code"
                type="text"
                value={invoicing.bank_sort_code}
                onChange={e => invoicingField('bank_sort_code', e.target.value)}
                placeholder="e.g. 12-34-56"
              />
            </div>
            <div className="form-group">
              <label htmlFor="inv-account-number">Account number</label>
              <input
                id="inv-account-number"
                type="text"
                value={invoicing.bank_account_number}
                onChange={e => invoicingField('bank_account_number', e.target.value)}
              />
            </div>

            <div className="form-actions">
              <button type="button" className="btn-primary" onClick={handleInvoicingSave} disabled={invoicingSaving}>
                {invoicingSaving ? 'Saving…' : 'Save'}
              </button>
              {invoicingSaved && (
                <span style={{ color: 'var(--color-positive)', fontSize: '0.9rem', alignSelf: 'center' }}>
                  Saved ✓
                </span>
              )}
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
