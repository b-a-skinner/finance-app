import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function ResetPassword() {
  const { resetPassword } = useAuth();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';

  const [password, setPassword] = useState('');
  const [confirm,  setConfirm]  = useState('');
  const [error,    setError]    = useState('');
  const [loading,  setLoading]  = useState(false);
  const [done,     setDone]     = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    if (password.length < 8) { setError('Password must be at least 8 characters.'); return; }
    if (password !== confirm) { setError('Passwords do not match.'); return; }
    setLoading(true);
    try {
      await resetPassword(token, password);
      setDone(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (!token) {
    return (
      <div className="auth-page">
        <div className="auth-card">
          <p className="auth-wordmark">fivera</p>
          <h1>Invalid reset link</h1>
          <p className="auth-subtitle">This link is missing its reset token.</p>
          <p className="auth-footer">
            <Link to="/forgot-password">Request a new link</Link>
          </p>
        </div>
      </div>
    );
  }

  if (done) {
    return (
      <div className="auth-page">
        <div className="auth-card">
          <p className="auth-wordmark">fivera</p>
          <h1>Password reset</h1>
          <p className="auth-subtitle">Your password has been changed. You can now sign in.</p>
          <Link to="/login" className="btn-primary" style={{ display: 'block', textAlign: 'center', textDecoration: 'none', marginTop: '1rem' }}>
            Sign in
          </Link>
        </div>
      </div>
    );
  }

  const tokenIssue = /invalid|expired/i.test(error);

  return (
    <div className="auth-page">
      <div className="auth-card">
        <p className="auth-wordmark">fivera</p>
        <h1>Choose a new password</h1>

        <form onSubmit={handleSubmit} noValidate>
          {error && (
            <div className="error-banner">
              {error}
              {tokenIssue && <> <Link to="/forgot-password">Request a new link</Link></>}
            </div>
          )}

          <div className="form-group">
            <label htmlFor="password">New password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="At least 8 characters"
              autoComplete="new-password"
              autoFocus
            />
          </div>

          <div className="form-group">
            <label htmlFor="confirm">Confirm new password</label>
            <input
              id="confirm"
              type="password"
              value={confirm}
              onChange={e => setConfirm(e.target.value)}
              placeholder="Repeat your new password"
              autoComplete="new-password"
            />
          </div>

          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Resetting…' : 'Reset password'}
          </button>
        </form>
      </div>
    </div>
  );
}
