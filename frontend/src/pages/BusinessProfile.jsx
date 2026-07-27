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

export default function BusinessProfile() {
  const { apiFetch, setBusinessType: ctxSetBusinessType } = useAuth();
  const [businessTypeSel, setBusinessTypeSel] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const load = useCallback(() => {
    apiFetch('/api/profile')
      .then(r => r.json())
      .then(data => setBusinessTypeSel(data.business_type ?? ''))
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
      </main>
    </>
  );
}
