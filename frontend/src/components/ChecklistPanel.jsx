import { useState } from 'react';
import { Link } from 'react-router-dom';

const ITEMS = [
  { key: 'income',   label: 'Income',   path: '/income' },
  { key: 'expenses', label: 'Expenses', path: '/expenses' },
  { key: 'debts',    label: 'Debts',    path: '/debts' },
  { key: 'savings',  label: 'Savings & Investments',  path: '/savings' },
  { key: 'pension',  label: 'Pension',  path: '/pension' },
  { key: 'assets',   label: 'Assets',   path: '/assets' },
];

const STORAGE_KEY = 'checklist_collapsed';

export default function ChecklistPanel({ status }) {
  const [collapsed, setCollapsed] = useState(() => {
    try { return localStorage.getItem(STORAGE_KEY) === 'true'; } catch { return false; }
  });

  function toggle() {
    const next = !collapsed;
    setCollapsed(next);
    try { localStorage.setItem(STORAGE_KEY, String(next)); } catch { /* ignore */ }
  }

  const allDone = ITEMS.every(item => status[item.key]);
  if (allDone) return null;

  const doneCount = ITEMS.filter(item => status[item.key]).length;

  return (
    <aside className="checklist-panel">
      <button className="checklist-toggle" onClick={toggle} aria-expanded={!collapsed}>
        <span className="checklist-toggle-label">Setup checklist</span>
        <span className="checklist-badge">{doneCount}/{ITEMS.length}</span>
        <span className="checklist-chevron">{collapsed ? '›' : '‹'}</span>
      </button>
      {!collapsed && (
        <ul className="checklist-list">
          {ITEMS.map(({ key, label, path }) => (
            <li key={key} className={`checklist-item${status[key] ? ' checklist-item--done' : ''}`}>
              <span className="checklist-tick">{status[key] ? '✓' : '○'}</span>
              {status[key] ? (
                <span className="checklist-label">{label}</span>
              ) : (
                <Link to={path} className="checklist-link">{label}</Link>
              )}
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}
