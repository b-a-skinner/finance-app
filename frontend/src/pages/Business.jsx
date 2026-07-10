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

export default function Business() {
  const { apiFetch, businessType } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (businessType === null) navigate('/choose-business-type', { replace: true });
  }, [businessType, navigate]);

  const [summary,    setSummary]    = useState(null);
  const [income,     setIncome]     = useState([]);
  const [expenses,   setExpenses]   = useState([]);
  const [taxConfig,  setTaxConfig]  = useState(null);
  const [loading,    setLoading]    = useState(true);
  const [modal,      setModal]      = useState(null);
  const [editItem,   setEditItem]   = useState(null);
  const [actionError, setActionError] = useState('');

  const fetchAll = useCallback(async () => {
    const [sRes, iRes, eRes, cfgRes] = await Promise.all([
      apiFetch('/api/business/summary'),
      apiFetch('/api/business/income'),
      apiFetch('/api/business/expenses'),
      apiFetch('/api/business/tax-config'),
    ]);
    if (sRes.ok)   setSummary(await sRes.json());
    if (iRes.ok)   setIncome(await iRes.json());
    if (eRes.ok)   setExpenses(await eRes.json());
    if (cfgRes.ok) setTaxConfig(await cfgRes.json());
    setLoading(false);
  }, [apiFetch]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  function openIncomeModal()  { setEditItem(null); setModal('income'); }
  function openExpenseModal() { setEditItem(null); setModal('expense'); }
  function closeModal()       { setModal(null); setEditItem(null); }
  function handleSuccess()    { closeModal(); fetchAll(); }

  function startEdit(type, item) { setEditItem({ type, item }); setModal(type); }

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
        {modal === 'expense' && <ExpenseModal onClose={closeModal} onSuccess={handleSuccess} item={null} taxConfig={taxConfig} />}
      </>
    );
  }

  const cashClass    = summary.cash_profit    >= 0 ? 'business-metric--positive' : 'business-metric--negative';
  const taxableClass = summary.taxable_profit >= 0 ? 'business-metric--positive' : 'business-metric--negative';

  return (
    <>
      <NavBar />
      <main className="resource-page business-page">
        <h1 className="page-title">Business</h1>
        <AddButtons onIncome={openIncomeModal} onExpense={openExpenseModal} />

        {actionError && <div className="error-banner">{actionError}</div>}

        {/* Summary — 3 cards */}
        <div className="cards-grid business-summary-grid">
          <div className="card">
            <p className="card-title">Revenue this year</p>
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
            {summary.total_business_miles > 0 && (() => {
              const cashAllowable = Math.round((summary.allowable_expenses_ytd - summary.total_mileage_allowance) * 100) / 100;
              return (
                <div className="biz-allowable-breakdown">
                  {cashAllowable > 0 && (
                    <p className="biz-metric-sub">{gbp(cashAllowable)} expenses</p>
                  )}
                  <p className="biz-metric-sub">
                    {gbp(summary.total_mileage_allowance)} mileage allowance ({fmtMiles(summary.total_business_miles)} business miles)
                  </p>
                  {summary.mileage_crossover_msg && (
                    <p className="biz-metric-sub biz-metric-note">{summary.mileage_crossover_msg}</p>
                  )}
                </div>
              );
            })()}
          </div>
        </div>

        {/* Profit split — 2 cards */}
        <div className="biz-profit-grid">
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
        </div>

        {/* Tax estimate hero */}
        {summary.tax_estimate && summary.tax_estimate.taxable_profit > 0 && (
          <div className="card biz-tax-hero">
            <p className="card-title">
              Set aside for your tax bill
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



        {disclaimer}
      </main>

      {modal === 'income' && (
        <IncomeModal onClose={closeModal} onSuccess={handleSuccess}
          item={editItem?.type === 'income' ? editItem.item : null} />
      )}
      {modal === 'expense' && (
        <ExpenseModal onClose={closeModal} onSuccess={handleSuccess}
          item={editItem?.type === 'expense' ? editItem.item : null}
          taxConfig={taxConfig} />
      )}
    </>
  );
}
