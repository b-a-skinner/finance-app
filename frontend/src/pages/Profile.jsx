import { useCallback, useEffect, useRef, useState } from 'react';
import NavBar from '../components/NavBar';
import { useAuth } from '../context/AuthContext';
import { gbp } from '../utils/format';
import { API_BASE } from '../utils/config';

const EMPTY = { dob_day: '', dob_month: '', dob_year: '', occupation: '', postcode_outward: '' };

const GOAL_OPTIONS = [
  { key: 'understanding_my_finances', emoji: '📊', label: 'Understanding my finances' },
  { key: 'building_my_savings',       emoji: '🏦', label: 'Building my savings' },
  { key: 'buying_a_home',             emoji: '🏠', label: 'Buying a home' },
  { key: 'managing_my_spending',      emoji: '💰', label: 'Managing my spending' },
  { key: 'paying_off_debt',           emoji: '🎯', label: 'Paying off debt' },
  { key: 'planning_for_the_future',   emoji: '📈', label: 'Planning for the future' },
];

function comparisonWord(pct) {
  if (pct === null || pct === undefined) return null;
  if (pct > 110) return 'above';
  if (pct < 90) return 'below';
  return 'about the same as';
}

function gapPct(pct) {
  if (pct === null || pct === undefined) return null;
  const gap = Math.abs(pct - 100).toFixed(1);
  const dir = pct >= 100 ? 'above' : 'below';
  return `${gap}% ${dir} median`;
}

function BenchmarkRow({ label, children }) {
  return (
    <div className="benchmark-row">
      <p className="benchmark-row-label">{label}</p>
      {children}
    </div>
  );
}

function HowYouCompare({ cmp, dobSet, postcodeSet }) {
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
    region, median_annual_salary_for_region, salary_vs_region_pct,
    region_source, region_source_notes, is_london,
    current_annual_salary,
    occupation_soc_group_description, occupation_median_annual_salary, salary_vs_occupation_pct,
    occupation_source, occupation_source_notes,
  } = cmp;

  const regionLabel = region ?? 'the UK overall';

  return (
    <div className="card benchmark-card">
      <p className="card-title">
        How you compare{user_age != null ? ` — age ${user_age}` : ''}
      </p>

      {/* Age-based monthly salary */}
      <BenchmarkRow label="Monthly salary">
        {!dobSet ? (
          <p className="benchmark-prompt">
            Add your date of birth above to see how your salary compares by age group.
          </p>
        ) : salary_band_label ? (
          <>
            <p className="benchmark-text">
              Your gross monthly salary of <strong>{gbp(current_monthly_salary)}</strong> is{' '}
              <strong>{comparisonWord(salary_comparison_pct)}</strong> the UK median of{' '}
              <strong>{gbp(median_monthly_salary)}</strong> for the {salary_band_label} age group
              {salary_comparison_pct !== null && ` (${gapPct(salary_comparison_pct)})`}.
            </p>
            <p className="benchmark-source">{salary_source} · {salary_source_metric}</p>
          </>
        ) : (
          <p className="benchmark-text benchmark-unavailable">
            No salary benchmark data available for your age group.
          </p>
        )}
      </BenchmarkRow>

      {/* Regional annual salary */}
      <BenchmarkRow label="Regional salary">
        {!postcodeSet ? (
          <p className="benchmark-prompt">
            Add your postcode to see how your salary compares regionally.
          </p>
        ) : median_annual_salary_for_region != null ? (
          <>
            <p className="benchmark-text">
              Your gross annual salary of <strong>{gbp(current_annual_salary)}</strong> is{' '}
              <strong>{comparisonWord(salary_vs_region_pct)}</strong> the median of{' '}
              <strong>{gbp(median_annual_salary_for_region)}</strong> for {regionLabel}
              {salary_vs_region_pct !== null && ` (${gapPct(salary_vs_region_pct)})`}.
            </p>
            <p className="benchmark-source">{region_source} · all employees</p>
            {is_london && (
              <p className="benchmark-source benchmark-caveat">
                London figure is full-time employees only, so may overstate the typical comparison.
              </p>
            )}
          </>
        ) : (
          <p className="benchmark-text benchmark-unavailable">
            No regional salary benchmark data available.
          </p>
        )}
      </BenchmarkRow>

      {/* Pension pot */}
      <BenchmarkRow label="Pension pot">
        {!dobSet ? (
          <p className="benchmark-prompt">
            Add your date of birth above to see how your pension compares by age group.
          </p>
        ) : pension_band_label && pension_data_available ? (
          <>
            <p className="benchmark-text">
              Your pension pot of <strong>{gbp(current_pension_pot)}</strong> is{' '}
              <strong>{comparisonWord(pension_comparison_pct)}</strong> the UK median of{' '}
              <strong>{gbp(median_pension_pot)}</strong> for the {pension_band_label} age group
              {pension_comparison_pct !== null && ` (${gapPct(pension_comparison_pct)})`}.
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

      {/* Occupation salary — only shown when a SOC match exists */}
      {occupation_soc_group_description && (
        <BenchmarkRow label="Occupation">
          <>
            <p className="benchmark-text">
              Your gross annual salary of <strong>{gbp(current_annual_salary)}</strong> is{' '}
              <strong>{comparisonWord(salary_vs_occupation_pct)}</strong> the median of{' '}
              <strong>{gbp(occupation_median_annual_salary)}</strong> for{' '}
              {occupation_soc_group_description}
              {salary_vs_occupation_pct !== null && ` (${gapPct(salary_vs_occupation_pct)})`}.
            </p>
            <p className="benchmark-source">{occupation_source} · {occupation_source_notes}</p>
          </>
        </BenchmarkRow>
      )}
    </div>
  );
}

function DobInput({ day, month, year, onChange }) {
  const mmRef   = useRef(null);
  const yyyyRef = useRef(null);

  function handleDay(e) {
    const val = e.target.value.replace(/\D/g, '').slice(0, 2);
    onChange(val, month, year);
    if (val.length === 2) mmRef.current?.focus();
  }

  function handleMonth(e) {
    const val = e.target.value.replace(/\D/g, '').slice(0, 2);
    onChange(day, val, year);
    if (val.length === 2) yyyyRef.current?.focus();
  }

  function handleYear(e) {
    const val = e.target.value.replace(/\D/g, '').slice(0, 4);
    onChange(day, month, val);
  }

  return (
    <>
      <div className="dob-row">
        <input
          type="text"
          inputMode="numeric"
          maxLength={2}
          className="dob-input dob-input-dd"
          value={day}
          onChange={handleDay}
          placeholder="DD"
        />
        <span className="dob-sep">/</span>
        <input
          type="text"
          inputMode="numeric"
          maxLength={2}
          ref={mmRef}
          className="dob-input dob-input-mm"
          value={month}
          onChange={handleMonth}
          placeholder="MM"
        />
        <span className="dob-sep">/</span>
        <input
          type="text"
          inputMode="numeric"
          maxLength={4}
          ref={yyyyRef}
          className="dob-input dob-input-yyyy"
          value={year}
          onChange={handleYear}
          placeholder="YYYY"
        />
      </div>
      <span className="form-hint">e.g. 23 / 01 / 2001</span>
    </>
  );
}

export default function Profile() {
  const { apiFetch } = useAuth();
  const [form, setForm] = useState(EMPTY);
  const [occupations, setOccupations] = useState([]);
  const [showOccDropdown, setShowOccDropdown] = useState(false);
  const [region, setRegion] = useState(null);
  const [regionKnown, setRegionKnown] = useState(false);
  const [dobSet, setDobSet] = useState(false);
  const [postcodeSet, setPostcodeSet] = useState(false);
  const [comparison, setComparison] = useState(null);
  const [goals, setGoals] = useState([]);
  const [goalsSaving, setGoalsSaving] = useState(false);
  const [goalsSaved, setGoalsSaved] = useState(false);
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
        const dobParts = data.date_of_birth ? data.date_of_birth.split('-') : ['', '', ''];
        setForm({
          dob_year: dobParts[0] ?? '',
          dob_month: dobParts[1] ?? '',
          dob_day: dobParts[2] ?? '',
          occupation: data.occupation ?? '',
          postcode_outward: data.postcode_outward ?? '',
        });
        setRegion(data.region);
        setRegionKnown(data.postcode_outward != null && data.postcode_outward !== '');
        setDobSet(!!data.date_of_birth);
        setPostcodeSet(!!data.postcode_outward);
        loadComparison();
      })
      .catch(() => setError('Failed to load profile.'))
      .finally(() => setLoading(false));
  }, [apiFetch, loadComparison]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    apiFetch('/api/profile/onboarding')
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data?.financial_goals) {
          try { setGoals(JSON.parse(data.financial_goals)); } catch { /* ignore */ }
        }
      })
      .catch(() => {});
  }, [apiFetch]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    fetch(`${API_BASE}/api/occupations`)
      .then(r => r.ok ? r.json() : [])
      .then(setOccupations)
      .catch(() => {});
  }, []);

  const filteredOccs = form.occupation.length >= 1
    ? occupations.filter(o => o.title.toLowerCase().includes(form.occupation.toLowerCase()))
    : [];

  const groupedOccs = filteredOccs.reduce((acc, o) => {
    if (!acc[o.soc_group]) acc[o.soc_group] = [];
    acc[o.soc_group].push(o);
    return acc;
  }, {});

  function field(key, val) {
    setForm(prev => ({ ...prev, [key]: val }));
    setSaved(false);
  }

  function toggleGoal(key) {
    setGoals(prev => prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]);
    setGoalsSaved(false);
  }

  async function handleGoalsSave() {
    setGoalsSaving(true);
    setGoalsSaved(false);
    try {
      await apiFetch('/api/profile/onboarding', {
        method: 'PATCH',
        body: JSON.stringify({ financial_goals: JSON.stringify(goals) }),
      });
      setGoalsSaved(true);
    } finally {
      setGoalsSaving(false);
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setFormError('');
    setSaved(false);

    const payload = {};
    const { dob_day, dob_month, dob_year } = form;
    const hasAnyDob = dob_day || dob_month || dob_year;
    if (hasAnyDob) {
      if (!dob_day || !dob_month || !dob_year) { setFormError('Please enter a complete date of birth.'); return; }
      const d = parseInt(dob_day, 10);
      const m = parseInt(dob_month, 10);
      const y = parseInt(dob_year, 10);
      if (isNaN(d) || d < 1 || d > 31)   { setFormError('Day must be between 1 and 31.'); return; }
      if (isNaN(m) || m < 1 || m > 12)   { setFormError('Month must be between 1 and 12.'); return; }
      if (isNaN(y) || y < 1900 || y > new Date().getFullYear()) { setFormError('Enter a valid 4-digit year.'); return; }
      payload.date_of_birth = `${String(y).padStart(4, '0')}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
    } else {
      payload.date_of_birth = null;
    }
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
      setDobSet(!!data.date_of_birth);
      setPostcodeSet(!!data.postcode_outward);
      setSaved(true);
      loadComparison();
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
                <label>Date of birth</label>
                <DobInput
                  day={form.dob_day}
                  month={form.dob_month}
                  year={form.dob_year}
                  onChange={(d, m, y) => {
                    setForm(p => ({ ...p, dob_day: d, dob_month: m, dob_year: y }));
                    setSaved(false);
                  }}
                />
              </div>
              <div className="form-group occ-group">
                <label htmlFor="occupation">Occupation</label>
                <div className="occ-wrap">
                  <input
                    id="occupation"
                    type="text"
                    autoComplete="off"
                    value={form.occupation}
                    onChange={e => { field('occupation', e.target.value); setShowOccDropdown(true); }}
                    onFocus={() => setShowOccDropdown(true)}
                    onBlur={() => setTimeout(() => setShowOccDropdown(false), 150)}
                    placeholder="Search occupations…"
                  />
                  {showOccDropdown && form.occupation.length >= 1 && (
                    Object.keys(groupedOccs).length > 0 ? (
                      <ul className="occ-dropdown">
                        {Object.entries(groupedOccs).map(([group, items]) => (
                          <li key={group} className="occ-group-item">
                            <div className="occ-group-header">{group}</div>
                            {items.map(occ => (
                              <div
                                key={occ.id}
                                className="occ-option"
                                onMouseDown={() => { field('occupation', occ.title); setShowOccDropdown(false); }}
                              >
                                {occ.title}
                              </div>
                            ))}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <ul className="occ-dropdown">
                        <li className="occ-group-item">
                          <div
                            className="occ-option occ-option--freetext"
                            onMouseDown={() => { field('occupation', form.occupation.trim()); setShowOccDropdown(false); }}
                          >
                            Use &ldquo;{form.occupation.trim()}&rdquo; as my occupation →
                          </div>
                        </li>
                      </ul>
                    )
                  )}
                </div>
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
          <HowYouCompare cmp={comparison} dobSet={dobSet} postcodeSet={postcodeSet} />
        </div>

        <div className="resource-layout resource-layout--single" style={{ marginTop: '1.5rem' }}>
          <div className="card">
            <p className="card-title">Your goals</p>
            {goals.length === 0 && (
              <p style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)', marginBottom: '1rem' }}>
                Select what matters most to you.
              </p>
            )}
            <div className="wizard-goals-grid">
              {GOAL_OPTIONS.map(g => (
                <button
                  key={g.key}
                  type="button"
                  className={`wizard-goal-tile${goals.includes(g.key) ? ' wizard-goal-tile--selected' : ''}`}
                  onClick={() => toggleGoal(g.key)}
                >
                  <span className="wizard-goal-emoji">{g.emoji}</span>
                  <span className="wizard-goal-label">{g.label}</span>
                </button>
              ))}
            </div>
            <div className="form-actions" style={{ marginTop: '1rem' }}>
              <button type="button" className="btn-primary" onClick={handleGoalsSave} disabled={goalsSaving}>
                {goalsSaving ? 'Saving…' : 'Save goals'}
              </button>
              {goalsSaved && (
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
