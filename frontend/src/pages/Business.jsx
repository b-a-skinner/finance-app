import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import NavBar from '../components/NavBar';
import { useAuth } from '../context/AuthContext';
import { gbp } from '../utils/format';
import {
  Tip, AddButtons, IncomeModal, ExpenseModal,
  fmtMiles,
} from '../components/BusinessShared';
import { class2EducationSnippet, CLASS2_PENSION_EXPLAINER } from '../utils/class2Education';
import { taxCardLabel, yearSelectorOptions } from '../utils/businessDashboard';

export default function Business() {
  const { apiFetch, businessType } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (businessType === null) navigate('/choose-business-type', { replace: true });
  }, [businessType, navigate]);

  const [summary,      setSummary]      = useState(null);
  const [income,       setIncome]       = useState([]);
  const [expenses,     setExpenses]     = useState([]);
  const [taxConfig,    setTaxConfig]    = useState(null); // rates for the SELECTED dashboard year
  const [currentTaxConfig, setCurrentTaxConfig] = useState(null); // always this tax year — for the add-entry modals, which default to today's date
  const [taxYears,     setTaxYears]     = useState([]);
  const [selectedYear, setSelectedYear] = useState('');
  const [loading,    setLoading]    = useState(true);
  const [modal,      setModal]      = useState(null);
  const [editItem,   setEditItem]   = useState(null);
  const [actionError, setActionError] = useState('');

  // Re-fetches only the year-scoped figures (summary + tax config) for the given tax
  // year — income/expenses/the year list itself don't change when switching years.
  const fetchForYear = useCallback(async (year) => {
    const qs = year ? `?tax_year=${encodeURIComponent(year)}` : '';
    const [sRes, cfgRes] = await Promise.all([
      apiFetch(`/api/business/summary${qs}`),
      apiFetch(`/api/business/tax-config${qs}`),
    ]);
    if (sRes.ok) {
      const s = await sRes.json();
      setSummary(s);
      setSelectedYear(s.tax_year);
    }
    setTaxConfig(cfgRes.ok ? await cfgRes.json() : null);
  }, [apiFetch]);

  const fetchAll = useCallback(async () => {
    const [iRes, eRes, yrRes, curCfgRes] = await Promise.all([
      apiFetch('/api/business/income'),
      apiFetch('/api/business/expenses'),
      apiFetch('/api/business/tax-years'),
      apiFetch('/api/business/tax-config'),
    ]);
    if (iRes.ok) setIncome(await iRes.json());
    if (eRes.ok) setExpenses(await eRes.json());
    if (yrRes.ok) setTaxYears((await yrRes.json()).years);
    setCurrentTaxConfig(curCfgRes.ok ? await curCfgRes.json() : null);
    await fetchForYear(selectedYear);
    setLoading(false);
  }, [apiFetch, fetchForYear, selectedYear]);

  useEffect(() => { fetchAll(); }, []); // eslint-disable-line react-hooks/exhaustive-deps -- initial load only; year switches go through fetchForYear directly

  function openIncomeModal()  { setEditItem(null); setModal('income'); }
  function openExpenseModal() { setEditItem(null); setModal('expense'); }
  function closeModal()       { setModal(null); setEditItem(null); }
  function handleSuccess()    { closeModal(); fetchAll(); }

  function startEdit(type, item) { setEditItem({ type, item }); setModal(type); }

  function handleYearChange(e) { fetchForYear(e.target.value); }

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
              Track income and expenses to see your profit position at a glance.
              Log mileage, home office costs, and dual-purpose expenses with HMRC-compliant methods.
            </p>
            <AddButtons onIncome={openIncomeModal} onExpense={openExpenseModal} />
          </div>
          {disclaimer}
        </main>
        {modal === 'income'  && <IncomeModal  onClose={closeModal} onSuccess={handleSuccess} item={null} />}
        {modal === 'expense' && <ExpenseModal onClose={closeModal} onSuccess={handleSuccess} item={null} taxConfig={currentTaxConfig} />}
      </>
    );
  }

  const cashClass    = summary.cash_profit    >= 0 ? 'business-metric--positive' : 'business-metric--negative';
  const taxableClass = summary.taxable_profit >= 0 ? 'business-metric--positive' : 'business-metric--negative';

  const yearOptions = yearSelectorOptions(selectedYear, taxYears);

  return (
    <>
      <NavBar />
      <main className="resource-page business-page">
        <div className="business-header-row">
          <h1 className="page-title">Business</h1>
          {yearOptions.length > 0 && (
            <div className="tax-year-select-wrap">
              <label htmlFor="biz-tax-year" className="tax-year-select-label">Tax year</label>
              <select id="biz-tax-year" className="tax-year-select" value={selectedYear} onChange={handleYearChange}>
                {yearOptions.map(y => <option key={y} value={y}>{y}</option>)}
              </select>
            </div>
          )}
        </div>
        <AddButtons onIncome={openIncomeModal} onExpense={openExpenseModal} />

        {actionError && <div className="error-banner">{actionError}</div>}

        {!summary.tax_config_available && (
          <p className="tax-config-missing-banner">
            Tax rates for {summary.tax_year} haven&rsquo;t been added yet — allowable expenses, mileage
            allowance, and the tax bill estimate for this year may be incomplete.
          </p>
        )}

        {/* All 6 summary cards — 3×2 desktop, 2×3 mobile */}
        <div className="biz-cards-grid">
          <div className="card">
            <p className="card-title">Revenue</p>
            <p className="business-metric">{gbp(summary.revenue_ytd)}</p>
          </div>
          <div className="card">
            <p className="card-title">Total expenses</p>
            <p className="business-metric">{gbp(summary.total_expenses_ytd)}</p>
          </div>
          <div className="card">
            <p className="card-title">
              Allowable expenses
              <Tip text="Allowable expenses (including mileage allowance and home office flat rate) reduce your taxable profit." />
            </p>
            <p className="business-metric">{gbp(summary.allowable_expenses_ytd)}</p>
            {summary.allowable_expenses_ytd > 0 && (() => {
              const hoAllowance   = summary.home_office_allowance ?? 0;
              const cashAllowable = Math.round((summary.allowable_expenses_ytd - summary.total_mileage_allowance - hoAllowance) * 100) / 100;
              return (
                <details className="biz-tax-breakdown">
                  <summary>Show breakdown</summary>
                  <ul className="biz-tax-breakdown-list">
                    {cashAllowable > 0 && (
                      <li>
                        <span className="breakdown-label">Allowable cash expenses</span>
                        <span>{gbp(cashAllowable)}</span>
                      </li>
                    )}
                    {summary.total_business_miles > 0 && (
                      <li>
                        <span className="breakdown-label">Mileage allowance ({fmtMiles(summary.total_business_miles)} business miles)</span>
                        <span>{gbp(summary.total_mileage_allowance)}</span>
                      </li>
                    )}
                    {hoAllowance > 0 && (
                      <li>
                        <span className="breakdown-label">Home office allowance</span>
                        <span>{gbp(hoAllowance)}</span>
                      </li>
                    )}
                  </ul>
                </details>
              );
            })()}
          </div>
          <div className="card">
            <p className="card-title">Money left after all costs</p>
            <p className={`business-metric ${cashClass}`}>{gbp(summary.cash_profit)}</p>
            <p className="biz-metric-sub">Revenue minus total expenses</p>
          </div>
          <div className="card">
            <p className="card-title">
              Taxable profit (estimated)
              <Tip text="Revenue minus all allowable expenses (including mileage and home office). This is what HMRC income tax and Class 4 NI are calculated on." />
            </p>
            <p className={`business-metric ${taxableClass}`}>{gbp(summary.taxable_profit)}</p>
            <p className="biz-metric-sub">Revenue minus allowable expenses</p>
          </div>
          {summary.tax_estimate && summary.tax_estimate.taxable_profit > 0 && (
            <div className="card biz-tax-hero">
              <p className="card-title">
                {taxCardLabel(summary)}
                <Tip text="Income tax + Class 4 NI on your taxable profit. Class 2 NI is shown separately — it's either automatic or voluntary." />
              </p>
              <p className="biz-tax-hero-amount">{gbp(summary.tax_estimate.total_set_aside)}</p>
              <p className="biz-metric-sub">
                {(summary.tax_estimate.effective_rate * 100).toFixed(1)}% effective rate on{' '}
                {gbp(summary.tax_estimate.taxable_profit)} taxable profit
              </p>
              <details className="biz-tax-breakdown">
                <summary>Show breakdown</summary>
                <ul className="biz-tax-breakdown-list">
                  <li>
                    <span className="breakdown-label">Income tax</span>
                    <span>{gbp(summary.tax_estimate.income_tax_on_profit)}</span>
                  </li>
                  <li>
                    <span className="breakdown-label">Class 4 NI</span>
                    <span>{gbp(summary.tax_estimate.class4_ni)}</span>
                  </li>
                  <li className="breakdown-class2">
                    <span className="breakdown-label">Class 2 NI</span>
                    <p className="biz-class2-snippet">
                      {class2EducationSnippet(summary.tax_estimate.class2_status, taxConfig)}
                    </p>
                    <details className="biz-class2-explainer">
                      <summary>What does this mean for my State Pension?</summary>
                      <p>
                        {CLASS2_PENSION_EXPLAINER.split('gov.uk/check-state-pension')[0]}
                        <a
                          href="https://www.gov.uk/check-state-pension"
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          gov.uk/check-state-pension
                        </a>
                        {CLASS2_PENSION_EXPLAINER.split('gov.uk/check-state-pension')[1]}
                      </p>
                    </details>
                  </li>
                </ul>
              </details>
              <p className="biz-tax-hero-disclaimer">
                This figure assumes self-employment income only and doesn&rsquo;t account for other income
                you may have. This is a calculation tool, not tax advice.
              </p>
            </div>
          )}
        </div>



        {disclaimer}
      </main>

      {modal === 'income' && (
        <IncomeModal onClose={closeModal} onSuccess={handleSuccess}
          item={editItem?.type === 'income' ? editItem.item : null} />
      )}
      {modal === 'expense' && (
        <ExpenseModal onClose={closeModal} onSuccess={handleSuccess}
          item={editItem?.type === 'expense' ? editItem.item : null}
          taxConfig={currentTaxConfig} />
      )}
    </>
  );
}
