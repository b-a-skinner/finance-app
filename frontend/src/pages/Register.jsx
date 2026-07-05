import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { API_BASE } from '../utils/config';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function EyeIcon({ visible }) {
  return visible ? (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
      <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
      <line x1="1" y1="1" x2="23" y2="23" />
    </svg>
  ) : (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

async function createInitialIncome(salary) {
  const token = localStorage.getItem('token');
  if (!token) return;
  await fetch(`${API_BASE}/api/income`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify({ label: 'Main salary', gross_annual_salary: parseFloat(salary), pay_frequency: 'monthly' }),
  });
}

export default function Register() {
  const { register, login } = useAuth();
  const navigate = useNavigate();

  const [email,    setEmail]    = useState('');
  const [password, setPassword] = useState('');
  const [showPw,   setShowPw]   = useState(false);
  const [salary,   setSalary]   = useState('');
  const [error,    setError]    = useState('');
  const [loading,  setLoading]  = useState(false);

  function validate() {
    if (!email || !password) return 'Please fill in email and password.';
    if (!EMAIL_RE.test(email)) return 'Please enter a valid email address.';
    if (password.length < 8)  return 'Password must be at least 8 characters.';
    if (!salary || isNaN(parseFloat(salary)) || parseFloat(salary) <= 0)
      return 'Please enter your gross annual salary to continue.';
    return null;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    const err = validate();
    if (err) { setError(err); return; }
    setLoading(true);
    try {
      await register(email, password);
      await login(email, password);
      await createInitialIncome(salary);
      navigate('/goals', { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <p className="auth-wordmark">fivera</p>
        <h1>Create your account</h1>
        <p className="auth-subtitle">See your true financial picture in minutes</p>

        <form onSubmit={handleSubmit} noValidate>
          {error && <div className="error-banner">{error}</div>}

          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="you@example.com"
              autoComplete="email"
              autoFocus
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <div className="password-wrap">
              <input
                id="password"
                type={showPw ? 'text' : 'password'}
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="At least 8 characters"
                autoComplete="new-password"
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowPw(v => !v)}
                aria-label={showPw ? 'Hide password' : 'Show password'}
                tabIndex={-1}
              >
                <EyeIcon visible={showPw} />
              </button>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="salary">Gross annual salary (£)</label>
            <input
              id="salary"
              type="number"
              min="0"
              step="1"
              value={salary}
              onChange={e => setSalary(e.target.value)}
              placeholder="e.g. 45000"
            />
            <span className="form-hint">We use this to calculate your exact take-home pay</span>
            <span className="form-hint" style={{ marginTop: '0.1rem', fontStyle: 'italic' }}>You can change this later</span>
          </div>

          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Creating account…' : 'Create account'}
          </button>
        </form>

        <p className="auth-footer">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
