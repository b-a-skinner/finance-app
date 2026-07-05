import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { API_BASE } from '../utils/config';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

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
  const [salary,   setSalary]   = useState('');
  const [error,    setError]    = useState('');
  const [loading,  setLoading]  = useState(false);

  function validate() {
    if (!email || !password) return 'Please fill in email and password.';
    if (!EMAIL_RE.test(email)) return 'Please enter a valid email address.';
    if (password.length < 8)  return 'Password must be at least 8 characters.';
    if (salary && (isNaN(parseFloat(salary)) || parseFloat(salary) <= 0))
      return 'Please enter a valid salary, or leave it blank to skip.';
    return null;
  }

  async function submit(includeSalary) {
    setError('');
    const err = validate();
    if (err) { setError(err); return; }
    setLoading(true);
    try {
      await register(email, password);
      await login(email, password);
      if (includeSalary && salary && parseFloat(salary) > 0) {
        await createInitialIncome(salary);
      }
      navigate('/dashboard', { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(e) {
    e.preventDefault();
    submit(true);
  }

  function handleSkip(e) {
    e.preventDefault();
    submit(false);
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
            <input
              id="password"
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="At least 8 characters"
              autoComplete="new-password"
            />
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

          <p className="register-skip">
            <a href="#" onClick={handleSkip}>Skip for now — I'll add this later</a>
          </p>
        </form>

        <p className="auth-footer">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
