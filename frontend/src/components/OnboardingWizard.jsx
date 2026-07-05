import { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { gbp } from '../utils/format';
import { API_BASE } from '../utils/config';

const STEPS = ['about_you', 'goals', 'income', 'expenses', 'debts', 'savings', 'pension', 'assets'];

const GOAL_OPTIONS = [
  { key: 'understanding_my_finances', emoji: '📊', label: 'Understanding my finances' },
  { key: 'building_my_savings',       emoji: '🏦', label: 'Building my savings' },
  { key: 'buying_a_home',             emoji: '🏠', label: 'Buying a home' },
  { key: 'managing_my_spending',      emoji: '💰', label: 'Managing my spending' },
  { key: 'paying_off_debt',           emoji: '🎯', label: 'Paying off debt' },
  { key: 'planning_for_the_future',   emoji: '📈', label: 'Planning for the future' },
];

const STEP_TITLES = {
  about_you: 'About you',
  goals:     'What are your financial goals?',
  income:    'Add your income',
  expenses:  'Add your expenses',
  debts:     'Add any debts',
  savings:   'Add your savings & investments',
  pension:   'Set up your pension',
  assets:    'Add other assets',
};

const STEP_DESCRIPTIONS = {
  about_you: 'Tell us a bit about yourself — date of birth, occupation, and location. Full profile setup is coming soon.',
  goals:     "Tell us what you're working towards — retiring early, buying a home, building an emergency fund — anything. This helps personalise your dashboard.",
  income:    "Enter your salary so we can calculate take-home pay, tax, and National Insurance. You can add multiple income sources.",
  expenses:  "Add your regular monthly outgoings (rent, bills, subscriptions) so we can calculate how much you have left each month.",
  debts:     "Add any outstanding debts — credit cards, student loans, mortgages — to include them in your net worth.",
  savings:   "Add your cash savings, ISAs, investment accounts, and trading accounts to get a complete picture of your wealth.",
  pension:   "Enter your pension balance and contribution rates to include your pot in net worth calculations.",
  assets:    "Add other assets — property, vehicles, investments — to complete your net worth picture.",
};

const DEBT_LABELS = { credit_card: 'Credit card', mortgage: 'Mortgage', student_loan: 'Student loan', other: 'Other' };
const ASSET_LABELS = { property: 'Property', vehicle: 'Vehicle', investment: 'Investment', other: 'Other' };

function ExistingList({ items, renderItem }) {
  if (!items.length) return null;
  return (
    <div className="wizard-existing">
      <ul className="wizard-existing-list">
        {items.map(item => {
          const { left, right } = renderItem(item);
          return (
            <li key={item.id} className="wizard-existing-item">
              <span className="wizard-existing-name">{left}</span>
              <span className="wizard-existing-value">{right}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function AboutYouStep({ onNext, onFirstNameChange }) {
  const { apiFetch } = useAuth();
  const [form, setForm] = useState({
    first_name: '',
    dob_day: '', dob_month: '', dob_year: '',
    occupation_text: '', occupation_soc_code: '',
    postcode: '',
  });
  const [occupations, setOccupations] = useState([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  // Fetch existing profile data to pre-populate on back-navigation
  useEffect(() => {
    apiFetch('/api/profile')
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (!data) return;
        const parts = data.date_of_birth ? data.date_of_birth.split('-') : ['', '', ''];
        setForm(p => ({
          ...p,
          first_name: data.first_name ?? '',
          dob_year: parts[0] ?? '',
          dob_month: parts[1] ?? '',
          dob_day: parts[2] ?? '',
          occupation_text: data.occupation ?? '',
          postcode: data.postcode_outward ?? '',
        }));
      })
      .catch(() => {});
  }, [apiFetch]); // eslint-disable-line react-hooks/exhaustive-deps

  // Fetch occupation list once (no auth needed)
  useEffect(() => {
    fetch(`${API_BASE}/api/occupations`)
      .then(r => r.ok ? r.json() : [])
      .then(setOccupations)
      .catch(() => {});
  }, []);

  const filtered = form.occupation_text.length >= 1
    ? occupations.filter(o =>
        o.title.toLowerCase().includes(form.occupation_text.toLowerCase())
      )
    : [];

  const grouped = filtered.reduce((acc, o) => {
    if (!acc[o.soc_group]) acc[o.soc_group] = [];
    acc[o.soc_group].push(o);
    return acc;
  }, {});

  function selectOccupation(occ) {
    setForm(p => ({ ...p, occupation_text: occ.title, occupation_soc_code: occ.soc_code }));
    setShowDropdown(false);
  }

  function validateDob() {
    const { dob_day, dob_month, dob_year } = form;
    if (!dob_day && !dob_month && !dob_year) return null;
    if (!dob_day || !dob_month || !dob_year) return 'Please enter a complete date of birth.';
    const day = parseInt(dob_day, 10);
    const month = parseInt(dob_month, 10);
    const year = parseInt(dob_year, 10);
    if (isNaN(day) || isNaN(month) || isNaN(year)) return 'Invalid date.';
    if (month < 1 || month > 12) return 'Month must be between 1 and 12.';
    if (day < 1 || day > 31) return 'Day must be between 1 and 31.';
    const dob = new Date(year, month - 1, day);
    if (dob.getMonth() !== month - 1) return 'Invalid date.';
    const now = new Date();
    if (dob >= now) return 'Date of birth must be in the past.';
    let age = now.getFullYear() - dob.getFullYear();
    if (now < new Date(now.getFullYear(), dob.getMonth(), dob.getDate())) age--;
    if (age < 16) return 'You must be at least 16 years old.';
    if (age > 100) return 'Please enter a valid date of birth.';
    return null;
  }

  function validatePostcode() {
    const pc = form.postcode.trim();
    if (!pc) return null;
    if (!/^[A-Za-z]{1,2}[0-9]{1,2}[A-Za-z]?$/.test(pc)) {
      return 'Enter just the first part of your postcode, e.g. SW1A or M1.';
    }
    return null;
  }

  async function handleContinue() {
    setError('');
    const dobErr = validateDob();
    if (dobErr) { setError(dobErr); return; }
    const pcErr = validatePostcode();
    if (pcErr) { setError(pcErr); return; }

    const payload = {};
    if (form.first_name.trim()) payload.first_name = form.first_name.trim();
    const { dob_day, dob_month, dob_year } = form;
    if (dob_day && dob_month && dob_year) {
      payload.date_of_birth =
        `${dob_year.padStart(4, '0')}-${dob_month.padStart(2, '0')}-${dob_day.padStart(2, '0')}`;
    }
    if (form.occupation_text.trim()) payload.occupation = form.occupation_text.trim();
    if (form.postcode.trim()) payload.postcode_outward = form.postcode.trim().toUpperCase();

    if (Object.keys(payload).length > 0) {
      setSaving(true);
      try {
        const res = await apiFetch('/api/profile', {
          method: 'PATCH',
          body: JSON.stringify(payload),
        });
        if (!res.ok) {
          const b = await res.json().catch(() => ({}));
          throw new Error(b.detail || 'Failed to save profile.');
        }
      } catch (err) {
        setError(err.message);
        setSaving(false);
        return;
      }
      setSaving(false);
    }

    if (form.first_name.trim()) onFirstNameChange(form.first_name.trim());
    onNext();
  }

  return (
    <div className="wizard-step-body">
      {error && <p className="wizard-error">{error}</p>}
      <div className="wizard-form">
        <div className="form-group">
          <label htmlFor="ay-first-name">First name</label>
          <input
            id="ay-first-name"
            type="text"
            value={form.first_name}
            onChange={e => setForm(p => ({ ...p, first_name: e.target.value }))}
            placeholder="e.g. Ben"
          />
        </div>

        <div className="form-group">
          <label>Date of birth</label>
          <div className="wizard-dob-row">
            <input
              type="number" min="1" max="31"
              value={form.dob_day}
              onChange={e => setForm(p => ({ ...p, dob_day: e.target.value }))}
              placeholder="DD"
              className="wizard-dob-part wizard-dob-day"
            />
            <input
              type="number" min="1" max="12"
              value={form.dob_month}
              onChange={e => setForm(p => ({ ...p, dob_month: e.target.value }))}
              placeholder="MM"
              className="wizard-dob-part wizard-dob-month"
            />
            <input
              type="number" min="1900" max={new Date().getFullYear()}
              value={form.dob_year}
              onChange={e => setForm(p => ({ ...p, dob_year: e.target.value }))}
              placeholder="YYYY"
              className="wizard-dob-part wizard-dob-year"
            />
          </div>
        </div>

        <div className="form-group wizard-occ-group">
          <label htmlFor="ay-occupation">Occupation</label>
          <div className="wizard-occ-wrap">
            <input
              id="ay-occupation"
              type="text"
              autoComplete="off"
              value={form.occupation_text}
              onChange={e => {
                setForm(p => ({ ...p, occupation_text: e.target.value, occupation_soc_code: '' }));
                setShowDropdown(true);
              }}
              onFocus={() => setShowDropdown(true)}
              onBlur={() => setTimeout(() => setShowDropdown(false), 150)}
              placeholder="Search occupations…"
            />
            {showDropdown && form.occupation_text.length >= 1 && (
              Object.keys(grouped).length > 0 ? (
                <ul className="wizard-occ-dropdown">
                  {Object.entries(grouped).map(([group, items]) => (
                    <li key={group} className="wizard-occ-group-item">
                      <div className="wizard-occ-group-header">{group}</div>
                      {items.map(occ => (
                        <div
                          key={occ.id}
                          className="wizard-occ-option"
                          onMouseDown={() => selectOccupation(occ)}
                        >
                          {occ.title}
                        </div>
                      ))}
                    </li>
                  ))}
                </ul>
              ) : (
                <ul className="wizard-occ-dropdown">
                  <li className="wizard-occ-group-item">
                    <div
                      className="wizard-occ-option wizard-occ-option--freetext"
                      onMouseDown={() => selectOccupation({ title: form.occupation_text.trim(), soc_code: null })}
                    >
                      Use &ldquo;{form.occupation_text.trim()}&rdquo; as my occupation →
                    </div>
                  </li>
                </ul>
              )
            )}
          </div>
        </div>

        <div className="form-group">
          <label htmlFor="ay-postcode">Postcode</label>
          <input
            id="ay-postcode"
            type="text"
            value={form.postcode}
            onChange={e => setForm(p => ({ ...p, postcode: e.target.value }))}
            placeholder="e.g. SW1A"
          />
          <span className="form-hint">Just the first part, e.g. SW1A or M1</span>
        </div>
      </div>

      <div className="wizard-step-actions">
        <button className="btn-primary" onClick={handleContinue} disabled={saving}>
          {saving ? 'Saving…' : 'Continue'}
        </button>
      </div>
    </div>
  );
}

function GoalsStep({ onSave, onBack, initialSelected }) {
  const [selected, setSelected] = useState(initialSelected ?? []);

  function toggle(key) {
    setSelected(prev => prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]);
  }

  return (
    <div className="wizard-step-body">
      <div className="wizard-goals-grid">
        {GOAL_OPTIONS.map(({ key, emoji, label }) => (
          <button
            key={key}
            type="button"
            className={`wizard-goal-tile${selected.includes(key) ? ' wizard-goal-tile--selected' : ''}`}
            onClick={() => toggle(key)}
          >
            <span className="wizard-goal-emoji">{emoji}</span>
            <span className="wizard-goal-label">{label}</span>
          </button>
        ))}
      </div>
      <div className="wizard-step-actions">
        <button className="btn-secondary" onClick={onBack}>Back</button>
        <button className="btn-primary" onClick={() => onSave(selected)}>
          {selected.length > 0 ? 'Save & continue' : 'Skip'}
        </button>
      </div>
    </div>
  );
}

function IncomeStep({ onNext, onBack }) {
  const { apiFetch } = useAuth();
  const [form, setForm] = useState({ label: '', gross_annual_salary: '' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [existing, setExisting] = useState([]);

  useEffect(() => {
    apiFetch('/api/income')
      .then(r => r.ok ? r.json() : [])
      .then(data => setExisting(Array.isArray(data) ? data.filter(i => i.is_active) : []))
      .catch(() => {});
  }, [apiFetch]); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleAdd(e) {
    e.preventDefault();
    setError('');
    const salary = parseFloat(form.gross_annual_salary);
    if (!form.label.trim()) { setError('Label is required.'); return; }
    if (isNaN(salary) || salary <= 0) { setError('Enter a valid salary.'); return; }
    setSaving(true);
    try {
      const res = await apiFetch('/api/income', {
        method: 'POST',
        body: JSON.stringify({ label: form.label.trim(), gross_annual_salary: salary, pay_frequency: 'annual' }),
      });
      if (!res.ok) { const b = await res.json().catch(() => ({})); throw new Error(b.detail || 'Failed'); }
      const newItem = await res.json();
      setExisting(prev => [...prev, newItem]);
      setForm({ label: '', gross_annual_salary: '' });
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="wizard-step-body">
      <ExistingList items={existing} renderItem={item => ({ left: item.label, right: `${gbp(item.gross_annual_salary)}/yr` })} />
      {error && <p className="wizard-error">{error}</p>}
      <form onSubmit={handleAdd} className="wizard-form">
        <div className="form-group">
          <label>Label</label>
          <input type="text" value={form.label} onChange={e => setForm(p => ({ ...p, label: e.target.value }))} placeholder="e.g. Main salary" />
        </div>
        <div className="form-group">
          <label>Gross annual salary (£)</label>
          <input type="number" min="0" step="1" value={form.gross_annual_salary} onChange={e => setForm(p => ({ ...p, gross_annual_salary: e.target.value }))} placeholder="e.g. 45000" />
        </div>
        <button type="submit" className="btn-primary" disabled={saving}>{saving ? 'Adding…' : 'Add income source'}</button>
      </form>
      <div className="wizard-step-actions">
        <button className="btn-secondary" onClick={onBack}>Back</button>
        <button className="btn-primary" onClick={onNext} disabled={existing.length === 0}>Continue</button>
        {existing.length === 0 && <span className="wizard-required-hint">Add at least one income source to continue</span>}
      </div>
    </div>
  );
}

function ExpensesStep({ onNext, onBack }) {
  const { apiFetch } = useAuth();
  const [form, setForm] = useState({ category: '', amount: '', frequency: 'monthly' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [existing, setExisting] = useState([]);

  useEffect(() => {
    apiFetch('/api/expenses')
      .then(r => r.ok ? r.json() : [])
      .then(data => setExisting(Array.isArray(data) ? data.filter(i => i.is_active) : []))
      .catch(() => {});
  }, [apiFetch]); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleAdd(e) {
    e.preventDefault();
    setError('');
    const amount = parseFloat(form.amount);
    if (!form.category.trim()) { setError('Category is required.'); return; }
    if (isNaN(amount) || amount < 0) { setError('Enter a valid amount.'); return; }
    setSaving(true);
    try {
      const res = await apiFetch('/api/expenses', {
        method: 'POST',
        body: JSON.stringify({ category: form.category.trim(), amount, frequency: form.frequency, is_fixed: true }),
      });
      if (!res.ok) { const b = await res.json().catch(() => ({})); throw new Error(b.detail || 'Failed'); }
      const newItem = await res.json();
      setExisting(prev => [...prev, newItem]);
      setForm({ category: '', amount: '', frequency: 'monthly' });
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="wizard-step-body">
      <ExistingList items={existing} renderItem={item => ({ left: item.category, right: `${gbp(item.amount)}/${item.frequency}` })} />
      {error && <p className="wizard-error">{error}</p>}
      <form onSubmit={handleAdd} className="wizard-form">
        <div className="form-group">
          <label>Category</label>
          <input type="text" value={form.category} onChange={e => setForm(p => ({ ...p, category: e.target.value }))} placeholder="e.g. Rent, Groceries" />
        </div>
        <div className="form-group">
          <label>Amount (£)</label>
          <input type="number" min="0" step="0.01" value={form.amount} onChange={e => setForm(p => ({ ...p, amount: e.target.value }))} placeholder="e.g. 1200" />
        </div>
        <div className="form-group">
          <label>Frequency</label>
          <select value={form.frequency} onChange={e => setForm(p => ({ ...p, frequency: e.target.value }))}>
            <option value="monthly">Monthly</option>
            <option value="weekly">Weekly</option>
            <option value="annual">Annual</option>
          </select>
        </div>
        <button type="submit" className="btn-primary" disabled={saving}>{saving ? 'Adding…' : 'Add expense'}</button>
      </form>
      <div className="wizard-step-actions">
        <button className="btn-secondary" onClick={onBack}>Back</button>
        <button className="btn-primary" onClick={onNext}>Continue</button>
        {existing.length === 0 && <button className="btn-secondary" onClick={onNext}>Skip</button>}
      </div>
    </div>
  );
}

const EMPTY_DEBT = { debt_type: 'credit_card', balance: '', interest_rate: '', min_payment: '', student_loan_plan_id: '', graduation_year: '' };

function DebtsStep({ onNext, onBack }) {
  const { apiFetch } = useAuth();
  const [form, setForm] = useState(EMPTY_DEBT);
  const [loanPlans, setLoanPlans] = useState([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [existing, setExisting] = useState([]);

  useEffect(() => {
    apiFetch('/api/debts')
      .then(r => r.ok ? r.json() : [])
      .then(data => setExisting(Array.isArray(data) ? data.filter(i => i.is_active) : []))
      .catch(() => {});
  }, [apiFetch]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    fetch(`${API_BASE}/api/config/student-loan-plans`)
      .then(r => r.json())
      .then(setLoanPlans)
      .catch(() => {});
  }, []);

  async function handleAdd(e) {
    e.preventDefault();
    setError('');
    const balance = parseFloat(form.balance);
    const rate = parseFloat(form.interest_rate);
    const minPay = parseFloat(form.min_payment);
    if (isNaN(balance) || balance < 0) { setError('Enter a valid balance.'); return; }
    if (isNaN(rate) || rate < 0) { setError('Enter a valid interest rate.'); return; }
    if (isNaN(minPay) || minPay < 0) { setError('Enter a valid minimum payment.'); return; }
    if (form.debt_type === 'student_loan' && !form.student_loan_plan_id) { setError('Please select your student loan plan.'); return; }
    setSaving(true);
    try {
      const res = await apiFetch('/api/debts', {
        method: 'POST',
        body: JSON.stringify({
          debt_type: form.debt_type,
          balance,
          interest_rate: rate,
          min_payment: minPay,
          student_loan_plan_id: form.debt_type === 'student_loan' && form.student_loan_plan_id ? parseInt(form.student_loan_plan_id, 10) : null,
          graduation_year: form.debt_type === 'student_loan' && form.graduation_year ? parseInt(form.graduation_year, 10) : null,
        }),
      });
      if (!res.ok) { const b = await res.json().catch(() => ({})); throw new Error(b.detail || 'Failed'); }
      const newItem = await res.json();
      setExisting(prev => [...prev, newItem]);
      setForm(EMPTY_DEBT);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="wizard-step-body">
      <ExistingList items={existing} renderItem={item => ({ left: DEBT_LABELS[item.debt_type] ?? item.debt_type, right: gbp(item.balance) })} />
      {error && <p className="wizard-error">{error}</p>}
      <form onSubmit={handleAdd} className="wizard-form">
        <div className="form-group">
          <label>Type</label>
          <select value={form.debt_type} onChange={e => setForm(p => ({ ...p, debt_type: e.target.value }))}>
            <option value="credit_card">Credit card</option>
            <option value="mortgage">Mortgage</option>
            <option value="student_loan">Student loan</option>
            <option value="other">Other</option>
          </select>
        </div>
        {form.debt_type === 'student_loan' && (
          <>
            <div className="form-group">
              <label>Student loan plan</label>
              <select value={form.student_loan_plan_id} onChange={e => setForm(p => ({ ...p, student_loan_plan_id: e.target.value }))}>
                <option value="">Select plan…</option>
                {loanPlans.map(p => (
                  <option key={p.id} value={p.id}>{p.plan_name}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>Year you graduated (or left university)</label>
              <input
                type="number"
                min="1990"
                max="2050"
                step="1"
                value={form.graduation_year}
                onChange={e => setForm(p => ({ ...p, graduation_year: e.target.value }))}
                placeholder="e.g. 2019"
              />
              <span className="form-hint">
                Used to calculate your projected repayment period. Repayments begin April 6 the following year.
              </span>
            </div>
          </>
        )}
        {form.debt_type === 'student_loan' && (
          <p className="projection-link">
            <a href="https://www.gov.uk/sign-in-to-manage-your-student-loan-balance" target="_blank" rel="noopener noreferrer">
              Sign in to view your student loan balance on <span style={{ whiteSpace: 'nowrap' }}>gov.uk →</span>
            </a>
          </p>
        )}
        <div className="form-group">
          <label>Outstanding balance (£)</label>
          <input type="number" min="0" step="0.01" value={form.balance} onChange={e => setForm(p => ({ ...p, balance: e.target.value }))} placeholder="e.g. 5000" />
        </div>
        <div className="form-group">
          <label>Interest rate (%)</label>
          <input type="number" min="0" step="0.01" value={form.interest_rate} onChange={e => setForm(p => ({ ...p, interest_rate: e.target.value }))} placeholder="e.g. 19.9" />
        </div>
        <div className="form-group">
          <label>Monthly minimum payment (£)</label>
          <input type="number" min="0" step="0.01" value={form.min_payment} onChange={e => setForm(p => ({ ...p, min_payment: e.target.value }))} placeholder="e.g. 50" />
        </div>
        <button type="submit" className="btn-primary" disabled={saving}>{saving ? 'Adding…' : 'Add debt'}</button>
      </form>
      <div className="wizard-step-actions">
        <button className="btn-secondary" onClick={onBack}>Back</button>
        <button className="btn-primary" onClick={onNext}>Continue</button>
        {existing.length === 0 && <button className="btn-secondary" onClick={onNext}>Skip</button>}
      </div>
    </div>
  );
}

const WIZARD_ACCOUNT_TYPE_OPTIONS = [
  { value: 'cash_savings',       label: 'Cash savings' },
  { value: 'stocks_shares_isa',  label: 'Stocks & Shares ISA' },
  { value: 'lifetime_isa',       label: 'Lifetime ISA' },
  { value: 'investment_account', label: 'Investment account' },
  { value: 'trading_account',    label: 'Trading account' },
  { value: 'other',              label: 'Other' },
];

function SavingsStep({ onNext, onBack }) {
  const { apiFetch } = useAuth();
  const [form, setForm] = useState({ name: '', current_balance: '', target_amount: '', monthly_contribution: '', account_type: '' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [existing, setExisting] = useState([]);

  useEffect(() => {
    apiFetch('/api/savings')
      .then(r => r.ok ? r.json() : [])
      .then(data => setExisting(Array.isArray(data) ? data.filter(i => i.is_active) : []))
      .catch(() => {});
  }, [apiFetch]); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleAdd(e) {
    e.preventDefault();
    setError('');
    const balance = parseFloat(form.current_balance);
    const target = form.target_amount !== '' ? parseFloat(form.target_amount) : null;
    const monthly = parseFloat(form.monthly_contribution);
    if (!form.name.trim()) { setError('Name is required.'); return; }
    if (isNaN(balance) || balance < 0) { setError('Enter a valid balance.'); return; }
    if (target !== null && (isNaN(target) || target < 0)) { setError('Enter a valid target amount.'); return; }
    if (isNaN(monthly) || monthly < 0) { setError('Enter a valid monthly contribution.'); return; }
    setSaving(true);
    try {
      const res = await apiFetch('/api/savings', {
        method: 'POST',
        body: JSON.stringify({
          name: form.name.trim(),
          current_balance: balance,
          target_amount: target,
          monthly_contribution: monthly,
          account_type: form.account_type || null,
        }),
      });
      if (!res.ok) { const b = await res.json().catch(() => ({})); throw new Error(b.detail || 'Failed'); }
      const newItem = await res.json();
      setExisting(prev => [...prev, newItem]);
      setForm({ name: '', current_balance: '', target_amount: '', monthly_contribution: '', account_type: '' });
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="wizard-step-body">
      <ExistingList
        items={existing}
        renderItem={item => ({
          left: item.name,
          right: item.target_amount ? `${gbp(item.current_balance)} of ${gbp(item.target_amount)}` : `${gbp(item.current_balance)} saved`,
        })}
      />
      {error && <p className="wizard-error">{error}</p>}
      <form onSubmit={handleAdd} className="wizard-form">
        <div className="form-group">
          <label>Account type</label>
          <select value={form.account_type} onChange={e => setForm(p => ({ ...p, account_type: e.target.value }))}>
            <option value="">Select type…</option>
            {WIZARD_ACCOUNT_TYPE_OPTIONS.map(o => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
        <div className="form-group">
          <label>Name</label>
          <input type="text" value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))} placeholder="e.g. Emergency fund" />
        </div>
        <div className="form-group">
          <label>Current balance (£)</label>
          <input type="number" min="0" step="0.01" value={form.current_balance} onChange={e => setForm(p => ({ ...p, current_balance: e.target.value }))} placeholder="e.g. 2000" />
        </div>
        <div className="form-group">
          <label>Target amount (£) <span className="form-hint-inline">(optional)</span></label>
          <input type="number" min="0" step="0.01" value={form.target_amount} onChange={e => setForm(p => ({ ...p, target_amount: e.target.value }))} placeholder="e.g. 10000" />
        </div>
        <div className="form-group">
          <label>Monthly contribution (£)</label>
          <input type="number" min="0" step="0.01" value={form.monthly_contribution} onChange={e => setForm(p => ({ ...p, monthly_contribution: e.target.value }))} placeholder="e.g. 200" />
        </div>
        <button type="submit" className="btn-primary" disabled={saving}>{saving ? 'Adding…' : 'Add account'}</button>
      </form>
      <div className="wizard-step-actions">
        <button className="btn-secondary" onClick={onBack}>Back</button>
        <button className="btn-primary" onClick={onNext}>Continue</button>
        {existing.length === 0 && <button className="btn-secondary" onClick={onNext}>Skip</button>}
      </div>
    </div>
  );
}

function PensionStep({ onNext, onBack }) {
  const { apiFetch } = useAuth();
  const [form, setForm] = useState({ current_balance: '', employee_contribution_pct: '', employer_contribution_pct: '' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [existing, setExisting] = useState([]);

  useEffect(() => {
    apiFetch('/api/pension')
      .then(r => r.ok ? r.json() : [])
      .then(data => setExisting(Array.isArray(data) ? data.filter(i => i.is_active) : []))
      .catch(() => {});
  }, [apiFetch]); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleAdd(e) {
    e.preventDefault();
    setError('');
    const balance = parseFloat(form.current_balance);
    const emp = parseFloat(form.employee_contribution_pct);
    const er = parseFloat(form.employer_contribution_pct);
    if (isNaN(balance) || balance < 0) { setError('Enter a valid balance.'); return; }
    if (isNaN(emp) || emp < 0) { setError('Enter a valid employee contribution %.'); return; }
    if (isNaN(er) || er < 0) { setError('Enter a valid employer contribution %.'); return; }
    setSaving(true);
    try {
      const res = await apiFetch('/api/pension', {
        method: 'POST',
        body: JSON.stringify({ current_balance: balance, employee_contribution_pct: emp, employer_contribution_pct: er }),
      });
      if (!res.ok) { const b = await res.json().catch(() => ({})); throw new Error(b.detail || 'Failed'); }
      const newItem = await res.json();
      setExisting(prev => [...prev, newItem]);
      setForm({ current_balance: '', employee_contribution_pct: '', employer_contribution_pct: '' });
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="wizard-step-body">
      <ExistingList
        items={existing}
        renderItem={item => ({
          left: `${item.employee_contribution_pct}% you · ${item.employer_contribution_pct}% employer`,
          right: gbp(item.current_balance),
        })}
      />
      {error && <p className="wizard-error">{error}</p>}
      <form onSubmit={handleAdd} className="wizard-form">
        <div className="form-group">
          <label>Current pension balance (£)</label>
          <input type="number" min="0" step="0.01" value={form.current_balance} onChange={e => setForm(p => ({ ...p, current_balance: e.target.value }))} placeholder="e.g. 15000" />
        </div>
        <div className="form-group">
          <label>Your contribution (%)</label>
          <input type="number" min="0" step="0.1" value={form.employee_contribution_pct} onChange={e => setForm(p => ({ ...p, employee_contribution_pct: e.target.value }))} placeholder="e.g. 5" />
        </div>
        <div className="form-group">
          <label>Employer contribution (%)</label>
          <input type="number" min="0" step="0.1" value={form.employer_contribution_pct} onChange={e => setForm(p => ({ ...p, employer_contribution_pct: e.target.value }))} placeholder="e.g. 3" />
        </div>
        <button type="submit" className="btn-primary" disabled={saving}>{saving ? 'Adding…' : 'Add pension'}</button>
      </form>
      <div className="wizard-step-actions">
        <button className="btn-secondary" onClick={onBack}>Back</button>
        <button className="btn-primary" onClick={onNext}>Continue</button>
        {existing.length === 0 && <button className="btn-secondary" onClick={onNext}>Skip</button>}
      </div>
    </div>
  );
}

function AssetsStep({ onNext, onBack }) {
  const { apiFetch } = useAuth();
  const [form, setForm] = useState({ name: '', asset_type: 'property', current_value: '' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [existing, setExisting] = useState([]);

  useEffect(() => {
    apiFetch('/api/assets')
      .then(r => r.ok ? r.json() : [])
      .then(data => setExisting(Array.isArray(data) ? data.filter(i => i.is_active) : []))
      .catch(() => {});
  }, [apiFetch]); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleAdd(e) {
    e.preventDefault();
    setError('');
    const value = parseFloat(form.current_value);
    if (!form.name.trim()) { setError('Name is required.'); return; }
    if (isNaN(value) || value < 0) { setError('Enter a valid value.'); return; }
    setSaving(true);
    try {
      const res = await apiFetch('/api/assets', {
        method: 'POST',
        body: JSON.stringify({ name: form.name.trim(), asset_type: form.asset_type, current_value: value }),
      });
      if (!res.ok) { const b = await res.json().catch(() => ({})); throw new Error(b.detail || 'Failed'); }
      const newItem = await res.json();
      setExisting(prev => [...prev, newItem]);
      setForm({ name: '', asset_type: 'property', current_value: '' });
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="wizard-step-body">
      <ExistingList
        items={existing}
        renderItem={item => ({ left: `${item.name} (${ASSET_LABELS[item.asset_type] ?? item.asset_type})`, right: gbp(item.current_value) })}
      />
      {error && <p className="wizard-error">{error}</p>}
      <form onSubmit={handleAdd} className="wizard-form">
        <div className="form-group">
          <label>Name</label>
          <input type="text" value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))} placeholder="e.g. Family home" />
        </div>
        <div className="form-group">
          <label>Type</label>
          <select value={form.asset_type} onChange={e => setForm(p => ({ ...p, asset_type: e.target.value }))}>
            <option value="property">Property</option>
            <option value="vehicle">Vehicle</option>
            <option value="investment">Investment</option>
            <option value="other">Other</option>
          </select>
        </div>
        <div className="form-group">
          <label>Current value (£)</label>
          <input type="number" min="0" step="0.01" value={form.current_value} onChange={e => setForm(p => ({ ...p, current_value: e.target.value }))} placeholder="e.g. 250000" />
        </div>
        <button type="submit" className="btn-primary" disabled={saving}>{saving ? 'Adding…' : 'Add asset'}</button>
      </form>
      <div className="wizard-step-actions">
        <button className="btn-secondary" onClick={onBack}>Back</button>
        <button className="btn-primary" onClick={onNext}>Finish</button>
        {existing.length === 0 && <button className="btn-secondary" onClick={onNext}>Skip</button>}
      </div>
    </div>
  );
}

export default function OnboardingWizard({ initialStep, dismissCount, firstName: propFirstName, onFirstNameChange, onComplete, onDismiss }) {
  const { apiFetch } = useAuth();
  const [step, setStep] = useState(initialStep ?? 0);
  const [goalsSelected, setGoalsSelected] = useState([]);
  const [wizardFirstName, setWizardFirstName] = useState(propFirstName ?? '');

  async function persistStep(nextStep) {
    try {
      await apiFetch('/api/profile/onboarding', {
        method: 'PATCH',
        body: JSON.stringify({ current_onboarding_step: nextStep }),
      });
    } catch (_) { /* non-critical */ }
  }

  function goTo(nextStep) {
    persistStep(nextStep);
    setStep(nextStep);
  }

  async function handleGoalsSave(selected) {
    setGoalsSelected(selected);
    try {
      const body = selected.length > 0
        ? { financial_goals: JSON.stringify(selected), current_onboarding_step: 2 }
        : { current_onboarding_step: 2 };
      await apiFetch('/api/profile/onboarding', {
        method: 'PATCH',
        body: JSON.stringify(body),
      });
    } catch (_) { /* non-critical */ }
    setStep(2);
  }

  async function handleComplete() {
    try {
      await apiFetch('/api/profile/onboarding', {
        method: 'PATCH',
        body: JSON.stringify({ onboarding_completed: true }),
      });
    } catch (_) { /* non-critical */ }
    onComplete();
  }

  async function handleDismiss() {
    try {
      await apiFetch('/api/profile/onboarding', {
        method: 'PATCH',
        body: JSON.stringify({ onboarding_dismiss_count: (dismissCount ?? 0) + 1 }),
      });
    } catch (_) { /* non-critical */ }
    onDismiss();
  }

  const totalSteps = STEPS.length;
  const stepKey = STEPS[step];
  const isCompletion = step >= totalSteps;

  return (
    <div className="wizard-overlay" role="dialog" aria-modal="true" aria-label="Setup wizard">
      <div className="wizard-modal">
        {isCompletion ? (
          <div className="wizard-completion">
            <div className="wizard-completion-icon">✓</div>
            <h2 className="wizard-completion-title">
              {wizardFirstName ? `You're all set, ${wizardFirstName}!` : "You're all set!"}
            </h2>
            <p className="wizard-completion-body">
              Your dashboard is ready. You can update any of these details from the individual pages at any time.
            </p>
            <button className="btn-primary" onClick={handleComplete}>Go to dashboard</button>
          </div>
        ) : (
          <>
            <div className="wizard-header">
              <div className="wizard-progress">
                {STEPS.map((_, i) => (
                  <div key={i} className={`wizard-dot${i === step ? ' wizard-dot--active' : i < step ? ' wizard-dot--done' : ''}`} />
                ))}
              </div>
              <p className="wizard-step-count">Step {step + 1} of {totalSteps}</p>
            </div>

            <h2 className="wizard-title">{STEP_TITLES[stepKey]}</h2>
            <p className="wizard-description">{STEP_DESCRIPTIONS[stepKey]}</p>

            {stepKey === 'about_you' && (
              <AboutYouStep
                onNext={() => goTo(1)}
                onFirstNameChange={name => {
                  setWizardFirstName(name);
                  onFirstNameChange?.(name);
                }}
              />
            )}
            {stepKey === 'goals'    && <GoalsStep onSave={handleGoalsSave} onBack={() => goTo(0)} initialSelected={goalsSelected} />}
            {stepKey === 'income'   && <IncomeStep onNext={() => goTo(3)} onBack={() => goTo(1)} />}
            {stepKey === 'expenses' && <ExpensesStep onNext={() => goTo(4)} onBack={() => goTo(2)} />}
            {stepKey === 'debts'    && <DebtsStep onNext={() => goTo(5)} onBack={() => goTo(3)} />}
            {stepKey === 'savings'  && <SavingsStep onNext={() => goTo(6)} onBack={() => goTo(4)} />}
            {stepKey === 'pension'  && <PensionStep onNext={() => goTo(7)} onBack={() => goTo(5)} />}
            {stepKey === 'assets'   && <AssetsStep onNext={() => goTo(totalSteps)} onBack={() => goTo(6)} />}
          </>
        )}
      </div>
    </div>
  );
}
