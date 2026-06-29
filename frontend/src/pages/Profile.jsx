import { useCallback, useEffect, useState } from 'react';
import NavBar from '../components/NavBar';
import { useAuth } from '../context/AuthContext';

const EMPTY = { date_of_birth: '', occupation: '', postcode_outward: '' };

function gbp(n) {
  return new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP', maximumFractionDigits: 0 }).format(n);
}

function comparisonWord(pct) {
  if (pct === null || pct === undefined) return null;
  if (pct > 110) return 'above';
  if (pct < 90) return 'below';
  return 'about the same as';
}

function BenchmarkRow({ label, children }) {
  return (
    <div className="benchmark-row">
      <p className="benchmark-row-label">{label}</p>
      {children}
    </div>
  );
}

function HowYouCompare({ cmp, dobSet }) {
  if (!dobSet) {
    return (
      <div className="card benchmark-card">
        <p className="card-title">How you compare</p>
        <p className="benchmark-prompt">
          Add your date of birth above to see how your salary and pension compare to UK medians for your age group.
        </p>
      </div>
    );
  }

  if (!cmp) {
    return (
      <div className="card benchmark-card">
        <p className="card-title">How you compare</p>
        <p className="benchmark-prompt">Loading comparison…</p>
      </div>
    );
  }

  const {
    user_age,
    salary_band_label, median_monthly_salary, salary_comparison_pct, salary_source, salary_source_metric,
    current_monthly_salary,
    pension_band_label, median_pension_pot, pension_comparison_pct, pension_data_available,
    pension_source, pension_source_metric,
    current_pension_pot,
  } = cmp;

  return (
    <div className="card benchmark-card">
      <p className="card-title">How you compare — age {user_age}</p>

      <BenchmarkRow label="Monthly salary">
        {salary_band_label ? (
          <>
            <p className="benchmark-text">
              Your gross monthly salary of <strong>{gbp(current_monthly_salary)}</strong> is{' '}
              <strong>{comparisonWord(salary_comparison_pct)}</strong> the UK median of{' '}
              <strong>{gbp(median_monthly_salary)}</strong> for the {salary_band_label} age group
              {salary_comparison_pct !== null && ` (${salary_comparison_pct}% of median)`}.
            </p>
            <p className="benchmark-source">{salary_source} · {salary_source_metric}</p>
          </>
        ) : (
          <p className="benchmark-text benchmark-unavailable">
            No salary benchmark data available for your age group.
          </p>
        )}
      </BenchmarkRow>

      <BenchmarkRow label="Pension pot">
        {pension_band_label && pension_data_available ? (
          <>
            <p className="benchmark-text">
              Your pension pot of <strong>{gbp(current_pension_pot)}</strong> is{' '}
              <strong>{comparisonWord(pension_comparison_pct)}</strong> the UK median of{' '}
              <strong>{gbp(median_pension_pot)}</strong> for the {pension_band_label} age group
              {pension_comparison_pct !== null && ` (${pension_comparison_pct}% of median)`}.
            </p>
            <p className="benchmark-source">{pension_source} · {pension_source_metric}</p>
          </>
        ) : pension_band_label ? (
          <p className="benchmark-text benchmark-unavailable">
            Benchmark data not yet available for the {pension_band_label} age group.
          </p>
        ) : (
          <p className="benchmark-text benchmark-unavailable">
            No pension benchmark data available for your age group.
          </p>
        )}
      </BenchmarkRow>
    </div>
  );
}

export default function Profile() {
  const { apiFetch } = useAuth();
  const [form, setForm] = useState(EMPTY);
  const [region, setRegion] = useState(null);
  const [regionKnown, setRegionKnown] = useState(false);
  const [dobSet, setDobSet] = useState(false);
  const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');
  const [formError, setFormError] = useState('');

  const loadComparison = useCallback(() => {
    apiFetch('/api/profile/comparison')
      .then(r => r.json())
      .then(setComparison)
      .catch(() => {});
  }, [apiFetch]);

  const load = useCallback(() => {
    apiFetch('/api/profile')
      .then(r => r.json())
      .then(data => {
        const hasDob = !!data.date_of_birth;
        setForm({
          date_of_birth: data.date_of_birth ?? '',
          occupation: data.occupation ?? '',
          postcode_outward: data.postcode_outward ?? '',
        });
        setRegion(data.region);
        setRegionKnown(data.postcode_outward != null && data.postcode_outward !== '');
        setDobSet(hasDob);
        if (hasDob) loadComparison();
      })
      .catch(() => setError('Failed to load profile.'))
      .finally(() => setLoading(false));
  }, [apiFetch, loadComparison]);

  useEffect(() => { load(); }, [load]);

  function field(key, val) {
    setForm(prev => ({ ...prev, [key]: val }));
    setSaved(false);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setFormError('');
    setSaved(false);

    const payload = {};
    if (form.date_of_birth) payload.date_of_birth = form.date_of_birth;
    else payload.date_of_birth = null;
    payload.occupation = form.occupation.trim() || null;
    payload.postcode_outward = form.postcode_outward.trim() || null;

    setSaving(true);
    try {
      const res = await apiFetch('/api/profile', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const body = await res.json();
        const detail = body?.detail;
        if (Array.isArray(detail)) {
          setFormError(detail.map(d => d.msg).join(' '));
        } else {
          setFormError(detail || 'Failed to save.');
        }
        return;
      }
      const data = await res.json();
      setRegion(data.region);
      setRegionKnown(!!data.postcode_outward);
      const hasDob = !!data.date_of_birth;
      setDobSet(hasDob);
      setSaved(true);
      if (hasDob) loadComparison();
      else setComparison(null);
    } catch {
      setFormError('Network error — please try again.');
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
          <div className="card resource-form-card">
            <p className="card-title">Your details</p>
            <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', marginBottom: '1.25rem' }}>
              These details are optional and used only to personalise comparisons — we never share them.
            </p>
            {formError && <div className="error-banner">{formError}</div>}
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label htmlFor="dob">Date of birth</label>
                <input
                  id="dob"
                  type="date"
                  value={form.date_of_birth}
                  onChange={e => field('date_of_birth', e.target.value)}
                />
              </div>
              <div className="form-group">
                <label htmlFor="occupation">Occupation</label>
                <input
                  id="occupation"
                  type="text"
                  value={form.occupation}
                  onChange={e => field('occupation', e.target.value)}
                  placeholder="e.g. Software Engineer, Teacher, Nurse"
                />
              </div>
              <div className="form-group">
                <label htmlFor="postcode">Postcode area</label>
                <input
                  id="postcode"
                  type="text"
                  value={form.postcode_outward}
                  onChange={e => field('postcode_outward', e.target.value)}
                  placeholder="e.g. SW1A or M1"
                  maxLength={4}
                  style={{ textTransform: 'uppercase' }}
                />
                <span className="form-hint">
                  Just the first part of your postcode (e.g. SW1A or M1) — we don't need your full address.
                </span>
                {regionKnown && (
                  <span className="form-hint" style={{ color: region ? 'var(--color-positive)' : 'var(--color-text-muted)' }}>
                    {region ? `Region: ${region}` : 'Postcode area not recognised — region will not be shown.'}
                  </span>
                )}
              </div>
              <div className="form-actions">
                <button type="submit" className="btn-primary" disabled={saving}>
                  {saving ? 'Saving…' : 'Save profile'}
                </button>
                {saved && (
                  <span style={{ color: 'var(--color-positive)', fontSize: '0.9rem', alignSelf: 'center' }}>
                    Saved ✓
                  </span>
                )}
              </div>
            </form>
          </div>
        </div>

        <div className="resource-layout resource-layout--single" style={{ marginTop: '1.5rem' }}>
          <HowYouCompare cmp={comparison} dobSet={dobSet} />
        </div>
      </main>
    </>
  );
}
