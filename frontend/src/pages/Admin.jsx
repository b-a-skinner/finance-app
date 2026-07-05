import { useEffect, useState } from 'react';
import { API_BASE } from '../utils/config';

const KEY_STORAGE = 'fiveraAdminKey';

function getStoredKey() {
  return sessionStorage.getItem(KEY_STORAGE) || '';
}

async function adminFetch(url, options = {}) {
  return fetch(`${API_BASE}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
      'X-Admin-Key': getStoredKey(),
    },
  });
}

function fmtDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
}

function StatCard({ label, value }) {
  return (
    <div className="adm-stat-card">
      <div className="adm-stat-value">{value}</div>
      <div className="adm-stat-label">{label}</div>
    </div>
  );
}

const PROFILE_CATS = ['income', 'expenses', 'debts', 'savings', 'pension', 'assets'];
const CAT_SHORT    = { income: 'Inc', expenses: 'Exp', debts: 'Dbt', savings: 'Sav', pension: 'Pen', assets: 'Ast' };

function ProfileCompletion({ pc }) {
  return (
    <span className="adm-profile-cats">
      {PROFILE_CATS.map(k => (
        <span
          key={k}
          title={k}
          className={`adm-profile-cat${pc[k] ? ' adm-profile-cat--done' : ''}`}
        >
          {CAT_SHORT[k]}
        </span>
      ))}
    </span>
  );
}

export default function Admin() {
  const [authed,    setAuthed]    = useState(false);
  const [loading,   setLoading]   = useState(false);
  const [keyInput,  setKeyInput]  = useState('');
  const [gateError, setGateError] = useState('');
  const [stats,     setStats]     = useState(null);
  const [users,     setUsers]     = useState([]);

  useEffect(() => {
    if (getStoredKey()) loadAll();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function loadAll() {
    setLoading(true);
    setGateError('');
    try {
      const [sr, ur] = await Promise.all([
        adminFetch('/api/admin/stats'),
        adminFetch('/api/admin/users'),
      ]);
      if (sr.status === 403 || ur.status === 403) {
        sessionStorage.removeItem(KEY_STORAGE);
        setAuthed(false);
        setGateError('Invalid admin key');
        return;
      }
      const [statsData, usersData] = await Promise.all([sr.json(), ur.json()]);
      setStats(statsData);
      setUsers([...usersData].sort((a, b) => new Date(b.created_at) - new Date(a.created_at)));
      setAuthed(true);
    } catch {
      setGateError('Network error — is the backend running?');
    } finally {
      setLoading(false);
    }
  }

  async function handleEnter(e) {
    e.preventDefault();
    const key = keyInput.trim();
    if (!key) return;
    sessionStorage.setItem(KEY_STORAGE, key);
    await loadAll();
  }

  function handleSignOut() {
    sessionStorage.removeItem(KEY_STORAGE);
    setAuthed(false);
    setStats(null);
    setUsers([]);
    setKeyInput('');
    setGateError('');
  }

  async function handleDelete(userId, email) {
    if (!confirm(`Are you sure? This cannot be undone.\n\nPermanently deletes ${email} and all their data.`)) return;
    try {
      const res = await adminFetch(`/api/admin/users/${userId}`, { method: 'DELETE' });
      if (res.status === 403) { handleSignOut(); return; }
      if (res.ok) setUsers(prev => prev.filter(u => u.id !== userId));
    } catch {
      alert('Network error.');
    }
  }

  if (!authed) {
    return (
      <div className="adm-gate">
        <form className="adm-gate-form" onSubmit={handleEnter}>
          <p className="adm-gate-wordmark">fivera</p>
          <p className="adm-gate-subtitle">admin</p>
          {gateError && <p className="adm-gate-error">{gateError}</p>}
          <input
            type="password"
            className="adm-gate-input"
            value={keyInput}
            onChange={e => setKeyInput(e.target.value)}
            placeholder="Admin key"
            autoFocus
          />
          <button type="submit" className="adm-gate-btn" disabled={loading}>
            {loading ? 'Checking…' : 'Enter'}
          </button>
        </form>
      </div>
    );
  }

  const fa = stats?.feature_adoption ?? {};

  return (
    <div className="adm-page">
      <div className="adm-header">
        <span className="adm-header-wordmark">fivera <span className="adm-header-badge">admin</span></span>
        <button className="adm-signout-btn" onClick={handleSignOut}>Sign out</button>
      </div>

      {stats && (
        <>
          <section className="adm-section">
            <h2 className="adm-section-title">Overview</h2>
            <div className="adm-stat-grid">
              <StatCard label="Total users"            value={stats.total_users} />
              <StatCard label="Active last 7 days"     value={stats.users_active_last_7_days} />
              <StatCard label="Active last 30 days"    value={stats.users_active_last_30_days} />
              <StatCard label="Completed onboarding"   value={stats.users_completed_onboarding} />
              <StatCard label="Users with income"      value={stats.users_with_income} />
              <StatCard label="Users with debts"       value={stats.users_with_debts} />
              <StatCard label="Users with savings"     value={stats.users_with_savings} />
              <StatCard label="Users with pension"     value={stats.users_with_pension} />
            </div>
          </section>

          <section className="adm-section">
            <h2 className="adm-section-title">Feature adoption</h2>
            <div className="adm-stat-grid">
              {Object.entries(fa).map(([key, pct]) => (
                <StatCard key={key} label={key} value={`${pct}%`} />
              ))}
            </div>
          </section>
        </>
      )}

      <section className="adm-section">
        <h2 className="adm-section-title">Users ({users.length})</h2>
        {users.length === 0 ? (
          <p className="adm-empty">No users yet.</p>
        ) : (
          <div className="adm-table-wrap">
            <table className="adm-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Joined</th>
                  <th>Last active</th>
                  <th>Onboarding</th>
                  <th>Profile</th>
                  <th>Goals</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {users.map(u => (
                  <tr key={u.id}>
                    <td>{u.first_name || <span className="adm-muted">—</span>}</td>
                    <td>{u.email}</td>
                    <td className="adm-muted">{fmtDate(u.created_at)}</td>
                    <td className="adm-muted">{fmtDate(u.last_active)}</td>
                    <td>{u.onboarding_completed ? <span className="adm-check">✓</span> : <span className="adm-muted">—</span>}</td>
                    <td><ProfileCompletion pc={u.profile_complete} /></td>
                    <td className="adm-muted">{u.financial_goals ? u.financial_goals.length : '—'}</td>
                    <td>
                      <button
                        className="adm-delete-btn"
                        onClick={() => handleDelete(u.id, u.email)}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
