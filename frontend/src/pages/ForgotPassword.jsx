import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function ForgotPassword() {
  const { forgotPassword } = useAuth();
  const [email,     setEmail]     = useState('');
  const [error,     setError]     = useState('');
  const [loading,   setLoading]   = useState(false);
  const [submitted, setSubmitted] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    if (!email) { setError('Please enter your email address.'); return; }
    setLoading(true);
    try {
      await forgotPassword(email);
      setSubmitted(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (submitted) {
    return (
      <div className="auth-page">
        <div className="auth-card">
          <p className="auth-wordmark">fivera</p>
          <h1>Check your email</h1>
          <p className="auth-subtitle">
            If an account exists for that email, we&rsquo;ve sent a reset link. It expires in 1 hour.
          </p>
          <p className="auth-footer">
            <Link to="/login">Back to sign in</Link>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <p className="auth-wordmark">fivera</p>
        <h1>Reset your password</h1>
        <p className="auth-subtitle">Enter your email and we&rsquo;ll send you a reset link</p>

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

          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Sending…' : 'Send reset link'}
          </button>
        </form>

        <p className="auth-footer">
          <Link to="/login">Back to sign in</Link>
        </p>
      </div>
    </div>
  );
}
