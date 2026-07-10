import { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { gbp } from '../utils/format';

// ---------------------------------------------------------------------------
// Category metadata
// ---------------------------------------------------------------------------

export const CATEGORY_INFO = {
  equipment:            { label: 'Equipment',                        allowable: true,  tip: 'Computers, tools, machinery — normally allowable for tax.' },
  software:             { label: 'Software & subscriptions',         allowable: true,  tip: 'Business software and subscriptions are normally allowable.' },
  office:               { label: 'Office costs (rent, utilities)',   allowable: true,  tip: 'Office rent and running costs are normally allowable.' },
  travel:               { label: 'Business travel',                  allowable: true,  tip: 'Use mileage for car/van/motorcycle/bicycle. Use actual costs for trains, taxis, etc.' },
  professional_fees:    { label: 'Professional fees',                allowable: true,  tip: 'Accountancy, legal, and other professional fees are normally allowable.' },
  marketing:            { label: 'Marketing & advertising',          allowable: true,  tip: 'Advertising and marketing spend is normally allowable.' },
  training:             { label: 'Training',                         allowable: true,  tip: 'Training that updates your current skills is allowable. New-trade training usually isn\'t.' },
  insurance:            { label: 'Insurance',                        allowable: true,  tip: 'Business insurance premiums are normally allowable.' },
  staff_costs:          { label: 'Staff costs / salaries',           allowable: true,  tip: 'Wages, salaries, and employer NI contributions are normally allowable.' },
  phone_internet:       { label: 'Phone & internet',                 allowable: true,  tip: 'Enter the total bill and set your business use % — only that portion is allowable.' },
  pension_employer:     { label: 'Pension contributions (employer)', allowable: true,  tip: 'Employer pension contributions are normally allowable.' },
  bank_charges:         { label: 'Bank & finance charges',           allowable: true,  tip: 'Business bank charges and interest are normally allowable.' },
  client_entertainment: { label: 'Client entertainment',             allowable: false, tip: 'Client entertainment is not tax-deductible under HMRC rules.' },
  fines:                { label: 'Fines & penalties',                allowable: false, tip: 'Fines and penalties are not allowable, even if incurred on business.' },
  personal:             { label: 'Personal expenses / drawings',     allowable: false, tip: 'Personal expenses and drawings don\'t reduce your tax bill.' },
  political:            { label: 'Political donations',              allowable: false, tip: 'Political donations are not allowable business expenses.' },
  home_office:          { label: 'Home office',                      allowable: true,  tip: 'Use the HMRC flat rate (£10–£26/month) or claim actual costs at your business-use %.' },
  other:                { label: 'Other',                            allowable: true,  tip: 'Enter your business use % if this is a dual-purpose expense. Check with your accountant.' },
};

export const ALLOWABLE_CATS     = ['equipment','software','office','travel','professional_fees','marketing','training','insurance','staff_costs','phone_internet','pension_employer','bank_charges'];
export const NON_ALLOWABLE_CATS = ['client_entertainment','fines','personal','political'];
export const DUAL_CATS          = ['home_office','other'];

export const VEHICLE_LABELS = { car_van: 'car/van', motorcycle: 'motorcycle', bicycle: 'bicycle' };

export const BAND_LABELS = {
  '25_50':    '25–50 hours/month',
  '51_100':   '51–100 hours/month',
  '101_plus': '101+ hours/month',
};

// ---------------------------------------------------------------------------
// Pure helpers
// ---------------------------------------------------------------------------

export function homeOfficeFlatAllowance(band, taxConfig) {
  if (!taxConfig || !band) return null;
  const value = {
    '25_50':    taxConfig.home_office_band_25_50,
    '51_100':   taxConfig.home_office_band_51_100,
    '101_plus': taxConfig.home_office_band_101_plus,
  }[band];
  return value ?? null;
}

export function defaultMethodForCat(cat) {
  if (cat === 'home_office') return 'home_office_flat';
  if (cat === 'travel')      return 'mileage';
  if (cat === 'phone_internet' || cat === 'other') return 'percentage';
  return null;
}

export function vehicleRateNote(vehicleType, taxConfig) {
  if (!taxConfig || !vehicleType) return null;
  const RATES = {
    car_van:    { first: taxConfig.mileage_car_van_first, over: taxConfig.mileage_car_van_over, threshold: taxConfig.mileage_threshold },
    motorcycle: { rate: taxConfig.mileage_motorcycle },
    bicycle:    { rate: taxConfig.mileage_bicycle },
  };
  const info = RATES[vehicleType];
  if (!info) return null;
  if ('rate' in info) {
    if (info.rate == null) return null;
    return `${Math.round(info.rate * 100)}p per mile.`;
  }
  if (info.first == null || info.over == null || info.threshold == null) return null;
  return `${Math.round(info.first * 100)}p per mile for the first ${info.threshold.toLocaleString('en-GB')} miles this tax year, then ${Math.round(info.over * 100)}p.`;
}

export function today() {
  return new Date().toISOString().split('T')[0];
}

export function formatDate(iso) {
  if (!iso) return '';
  return new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }).format(new Date(iso));
}

export function fmtMiles(n) {
  return (n || 0).toLocaleString('en-GB');
}

export function activityLabel(entry, taxConfig) {
  if (entry._type === 'income') return entry.description || 'Income';

  const catLabel = CATEGORY_INFO[entry.category]?.label ?? entry.category;

  if (entry.expense_method === 'mileage') {
    const vLabel = VEHICLE_LABELS[entry.vehicle_type] ?? entry.vehicle_type ?? 'vehicle';
    return `${fmtMiles(entry.business_miles)} miles (${vLabel})`;
  }

  if (entry.expense_method === 'home_office_flat') {
    return 'Home office (flat rate)';
  }

  return catLabel;
}

export function activityDetail(entry, taxConfig) {
  if (entry._type === 'income') return formatDate(entry._date);

  const parts = [formatDate(entry._date)];

  if (entry.expense_method === 'mileage') {
    if (entry.description) parts.push(entry.description);
    return parts.join(' · ');
  }

  if (entry.expense_method === 'home_office_flat' && taxConfig) {
    const rate = {
      '25_50':    taxConfig.home_office_band_25_50,
      '51_100':   taxConfig.home_office_band_51_100,
      '101_plus': taxConfig.home_office_band_101_plus,
    }[entry.home_office_hours_band];
    if (rate != null) parts.push(`${gbp(rate)} allowable`);
  }

  if (entry.expense_method === 'percentage' || entry.expense_method === 'home_office_actual') {
    const pct = entry.business_use_percent || 100;
    const allowable = Math.round(entry.amount * pct) / 100;
    parts.push(`${gbp(allowable)} allowable`);
  }

  if (!entry.expense_method || entry.expense_method === null) {
    if (entry.description) parts.push(entry.description);
    if (!entry.is_allowable) parts.push('non-allowable');
  }

  return parts.join(' · ');
}

// ---------------------------------------------------------------------------
// Tooltip
// ---------------------------------------------------------------------------

export function Tip({ text }) {
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
// Modal shell
// ---------------------------------------------------------------------------

export function ModalShell({ title, onClose, children }) {
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

// ---------------------------------------------------------------------------
// Income modal
// ---------------------------------------------------------------------------

export function IncomeModal({ onClose, onSuccess, item }) {
  const { apiFetch } = useAuth();
  const [form, setForm] = useState({
    amount: item?.amount ?? '',
    date_received: item?.date_received ?? today(),
    description: item?.description ?? '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError]   = useState('');

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
          {form.date_received > today() && (
            <p className="scheduled-flag">Scheduled — this won't count towards your figures until its date passes and you approve it.</p>
          )}
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

// ---------------------------------------------------------------------------
// Expense modal
// ---------------------------------------------------------------------------

export function ExpenseModal({ onClose, onSuccess, item, taxConfig }) {
  const { apiFetch } = useAuth();

  const initCat = item?.category ?? 'equipment';

  function initForm(cat, src) {
    const method = src?.expense_method ?? defaultMethodForCat(cat);
    return {
      amount:                 src?.amount != null && src.amount !== 0 ? String(src.amount) : '',
      date_incurred:          src?.date_incurred ?? today(),
      category:               cat,
      description:            src?.description ?? '',
      is_allowable:           src != null ? src.is_allowable : (CATEGORY_INFO[cat]?.allowable ?? true),
      expense_method:         method,
      home_office_hours_band: src?.home_office_hours_band ?? '101_plus',
      business_miles:         src?.business_miles != null ? String(src.business_miles) : '',
      vehicle_type:           src?.vehicle_type ?? 'car_van',
      business_use_percent:   src?.business_use_percent != null ? String(src.business_use_percent) : '100',
    };
  }

  const [form, setForm]     = useState(() => initForm(initCat, item));
  const [saving, setSaving] = useState(false);
  const [error, setError]   = useState('');

  function field(k, v) { setForm(p => ({ ...p, [k]: v })); }

  function handleCategoryChange(cat) {
    setForm(p => ({
      ...initForm(cat, null),
      date_incurred: p.date_incurred,
      description:   p.description,
    }));
  }

  const isMileage    = form.expense_method === 'mileage';
  const isFlatRate   = form.expense_method === 'home_office_flat';
  const isPercentage = form.expense_method === 'percentage' || form.expense_method === 'home_office_actual';
  const isStandard   = !isMileage && !isFlatRate && !isPercentage;

  const showAmountField = !isMileage && !isFlatRate;

  const previewAllowable = isPercentage
    ? (() => {
        const amt = parseFloat(form.amount);
        const pct = parseInt(form.business_use_percent, 10);
        if (!isNaN(amt) && amt > 0 && !isNaN(pct) && pct > 0) {
          return Math.round(amt * pct) / 100;
        }
        return null;
      })()
    : null;

  function flatRateAmount(band) {
    if (!taxConfig) return null;
    return { '25_50': taxConfig.home_office_band_25_50, '51_100': taxConfig.home_office_band_51_100, '101_plus': taxConfig.home_office_band_101_plus }[band] ?? null;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');

    if (!form.date_incurred) { setError('Date is required.'); return; }

    let payload;

    if (isMileage) {
      const miles = parseInt(form.business_miles, 10);
      if (isNaN(miles) || miles <= 0) { setError('Enter the number of business miles.'); return; }
      if (!form.vehicle_type) { setError('Select a vehicle type.'); return; }
      payload = {
        amount: 0,
        date_incurred: form.date_incurred,
        category: form.category,
        description: form.description.trim() || null,
        is_allowable: true,
        expense_method: 'mileage',
        business_miles: miles,
        vehicle_type: form.vehicle_type,
        business_use_percent: 100,
      };

    } else if (isFlatRate) {
      if (!form.home_office_hours_band) { setError('Select a hours band.'); return; }
      payload = {
        amount: 0,
        date_incurred: form.date_incurred,
        category: form.category,
        description: form.description.trim() || null,
        is_allowable: true,
        expense_method: 'home_office_flat',
        home_office_hours_band: form.home_office_hours_band,
        business_use_percent: 100,
      };

    } else if (isPercentage) {
      const amount = parseFloat(form.amount);
      if (isNaN(amount) || amount <= 0) { setError('Enter a valid amount.'); return; }
      const pct = parseInt(form.business_use_percent, 10);
      if (isNaN(pct) || pct < 1 || pct > 100) { setError('Business use must be between 1 and 100%.'); return; }
      payload = {
        amount,
        date_incurred: form.date_incurred,
        category: form.category,
        description: form.description.trim() || null,
        is_allowable: true,
        expense_method: form.expense_method,
        business_use_percent: pct,
      };

    } else {
      const amount = parseFloat(form.amount);
      if (isNaN(amount) || amount <= 0) { setError('Enter a valid amount.'); return; }
      payload = {
        amount,
        date_incurred: form.date_incurred,
        category: form.category,
        description: form.description.trim() || null,
        is_allowable: form.is_allowable,
        business_use_percent: 100,
      };
    }

    setSaving(true);
    try {
      const url = item ? `/api/business/expenses/${item.id}` : '/api/business/expenses';
      const res = await apiFetch(url, {
        method: item ? 'PATCH' : 'POST',
        body: JSON.stringify(payload),
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

        {form.category === 'home_office' && (
          <div className="form-group">
            <label>Claiming method</label>
            <div className="method-radio-group">
              <label className="method-radio-label">
                <input type="radio" name="ho-method" value="home_office_flat"
                  checked={form.expense_method === 'home_office_flat'}
                  onChange={() => field('expense_method', 'home_office_flat')} />
                Flat rate (HMRC simplified)
              </label>
              <label className="method-radio-label">
                <input type="radio" name="ho-method" value="home_office_actual"
                  checked={form.expense_method === 'home_office_actual'}
                  onChange={() => field('expense_method', 'home_office_actual')} />
                Actual costs (business use %)
              </label>
            </div>
          </div>
        )}

        {isFlatRate && (
          <div className="form-group">
            <label htmlFor="be-band">Hours worked at home (per month)</label>
            <select id="be-band" value={form.home_office_hours_band}
              onChange={e => field('home_office_hours_band', e.target.value)}>
              {Object.entries(BAND_LABELS).map(([val, lbl]) => {
                const rate = flatRateAmount(val);
                return (
                  <option key={val} value={val}>
                    {lbl}{rate != null ? ` — ${gbp(rate)}/month allowable` : ''}
                  </option>
                );
              })}
            </select>
            {taxConfig && (
              <p className="form-hint-inline" style={{ marginTop: '0.25rem' }}>
                Allowable this month: {gbp(flatRateAmount(form.home_office_hours_band) ?? 0)}
              </p>
            )}
          </div>
        )}

        {form.category === 'travel' && (
          <div className="form-group">
            <label>Claiming method</label>
            <div className="method-radio-group">
              <label className="method-radio-label">
                <input type="radio" name="tr-method" value="mileage"
                  checked={form.expense_method === 'mileage'}
                  onChange={() => field('expense_method', 'mileage')} />
                Mileage allowance (HMRC rates)
              </label>
              <label className="method-radio-label">
                <input type="radio" name="tr-method" value="percentage"
                  checked={form.expense_method === 'percentage'}
                  onChange={() => field('expense_method', 'percentage')} />
                Actual cost (train, taxi, etc.)
              </label>
            </div>
          </div>
        )}

        {isMileage && (
          <>
            <div className="form-group">
              <label htmlFor="be-vtype">Vehicle type</label>
              <select id="be-vtype" value={form.vehicle_type}
                onChange={e => field('vehicle_type', e.target.value)}>
                <option value="car_van">Car / van</option>
                <option value="motorcycle">Motorcycle</option>
                <option value="bicycle">Bicycle</option>
              </select>
              {vehicleRateNote(form.vehicle_type, taxConfig) && (
                <p className="form-hint-inline" style={{ marginTop: '0.25rem' }}>
                  {vehicleRateNote(form.vehicle_type, taxConfig)}
                </p>
              )}
            </div>
            <div className="form-group">
              <label htmlFor="be-miles">Business miles</label>
              <input id="be-miles" type="number" min="1" step="1" value={form.business_miles}
                onChange={e => field('business_miles', e.target.value)}
                placeholder="e.g. 1200" autoFocus={!item} />
            </div>
          </>
        )}

        {showAmountField && (
          <div className="form-group">
            <label htmlFor="be-amount">Amount (£)</label>
            <input id="be-amount" type="number" min="0" step="0.01" value={form.amount}
              onChange={e => field('amount', e.target.value)}
              placeholder="e.g. 299"
              autoFocus={!item && !isMileage} />
          </div>
        )}

        {isPercentage && (
          <div className="form-group">
            <label htmlFor="be-pct">Business use %</label>
            <input id="be-pct" type="number" min="1" max="100" step="1"
              value={form.business_use_percent}
              onChange={e => field('business_use_percent', e.target.value)}
              placeholder="e.g. 70" />
            {previewAllowable !== null && (
              <p className="form-hint-inline allowable-preview" style={{ marginTop: '0.25rem' }}>
                Allowable portion: {gbp(previewAllowable)}
              </p>
            )}
          </div>
        )}

        {isStandard && (
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
        )}

        <div className="form-group">
          <label htmlFor="be-date">Date</label>
          <input id="be-date" type="date" value={form.date_incurred} onChange={e => field('date_incurred', e.target.value)} />
          {form.date_incurred > today() && (
            <p className="scheduled-flag">Scheduled — this won't count towards your figures until its date passes and you approve it.</p>
          )}
        </div>

        <div className="form-group">
          <label htmlFor="be-desc">Description <span className="form-hint-inline">(optional)</span></label>
          <input id="be-desc" type="text" value={form.description} onChange={e => field('description', e.target.value)}
            placeholder={isMileage ? 'e.g. Client visit, site survey' : 'e.g. Figma subscription'} />
        </div>

        <button type="submit" className="btn-primary" disabled={saving}>
          {saving ? 'Saving…' : item ? 'Save changes' : isMileage ? 'Log miles' : isFlatRate ? 'Add home office month' : 'Add expense'}
        </button>
      </form>
    </ModalShell>
  );
}

// ---------------------------------------------------------------------------
// Add buttons
// ---------------------------------------------------------------------------

export function AddButtons({ onIncome, onExpense }) {
  return (
    <div className="business-actions">
      <button className="btn-primary" onClick={onIncome}>+ Add income</button>
      <button className="btn-primary" onClick={onExpense}>+ Add expense</button>
    </div>
  );
}
