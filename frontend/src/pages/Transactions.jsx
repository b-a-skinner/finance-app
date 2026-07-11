import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import NavBar from '../components/NavBar';
import { useAuth } from '../context/AuthContext';
import { gbp } from '../utils/format';
import {
  Tip, IncomeModal, ExpenseModal,
  activityLabel, activityDetail, homeOfficeFlatAllowance,
} from '../components/BusinessShared';

export default function Transactions() {
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

  function closeModal()    { setModal(null); setEditItem(null); }
  function handleSuccess() { closeModal(); fetchAll(); }

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

  const allActivity = [
    ...income.map(i => ({ ...i, _type: 'income',  _date: i.date_received })),
    ...expenses.map(e => ({ ...e, _type: 'expense', _date: e.date_incurred })),
  ].sort((a, b) => b._date.localeCompare(a._date));

  if (loading) {
    return (
      <>
        <NavBar />
        <main className="resource-page">
          <p className="list-empty">Loading…</p>
        </main>
      </>
    );
  }

  return (
    <>
      <NavBar />
      <main className="resource-page">
        <h1 className="page-title">Transactions</h1>

        {actionError && <div className="error-banner">{actionError}</div>}

        {allActivity.length > 0 ? (
          <div className="card">
            <ul className="item-list">
              {allActivity.map(entry => {
                const isIncome = entry._type === 'income';
                const isMile   = !isIncome && entry.expense_method === 'mileage';
                const isFlatHO = !isIncome && entry.expense_method === 'home_office_flat';
                const label    = activityLabel(entry, taxConfig);
                const detail   = activityDetail(entry, taxConfig);
                const mileAttr   = isMile   ? (summary?.mileage_attribution?.[entry.id] ?? 0) : null;
                const flatHOAmt  = isFlatHO ? homeOfficeFlatAllowance(entry.home_office_hours_band, taxConfig) : null;
                return (
                  <li key={`${entry._type}-${entry.id}`} className="item-row business-activity-row">
                    <div className="item-info">
                      <span className="item-name">{label}</span>
                      <span className="item-detail">
                        {detail}
                        {isMile && (
                          <span className="mileage-cumulative-note">
                            {' '}<Tip text="Calculated across your cumulative miles this tax year." />
                          </span>
                        )}
                      </span>
                    </div>
                    {isIncome ? (
                      <span className="business-amount business-amount--income">+{gbp(entry.amount)}</span>
                    ) : isMile ? (
                      <span className="business-amount business-amount--expense">−{gbp(mileAttr)}</span>
                    ) : isFlatHO && flatHOAmt != null ? (
                      <span className="business-amount business-amount--expense">−{gbp(flatHOAmt)}</span>
                    ) : isFlatHO ? null : (
                      <span className="business-amount business-amount--expense">−{gbp(entry.amount)}</span>
                    )}
                    <div className="item-actions">
                      <button className="btn-sm" onClick={() => startEdit(entry._type, entry)}>Edit</button>
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>
        ) : (
          <p className="list-empty">No transactions yet. Add income or expenses from the Business dashboard.</p>
        )}
      </main>

      {modal === 'income' && (
        <IncomeModal onClose={closeModal} onSuccess={handleSuccess}
          item={editItem?.type === 'income' ? editItem.item : null}
          onDelete={editItem?.type === 'income' ? () => { handleDelete('income', editItem.item.id); closeModal(); } : undefined} />
      )}
      {modal === 'expense' && (
        <ExpenseModal onClose={closeModal} onSuccess={handleSuccess}
          item={editItem?.type === 'expense' ? editItem.item : null}
          taxConfig={taxConfig}
          onDelete={editItem?.type === 'expense' ? () => { handleDelete('expense', editItem.item.id); closeModal(); } : undefined} />
      )}
    </>
  );
}
