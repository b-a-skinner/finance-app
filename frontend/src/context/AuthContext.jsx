import { createContext, useCallback, useContext, useState } from 'react';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(null);

  /**
   * POST /api/auth/login — OAuth2 form data (username = email).
   * On success stores the JWT in state.
   */
  async function login(email, password) {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ username: email, password }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || 'Login failed');
    }
    const data = await res.json();
    setToken(data.access_token);
  }

  /**
   * POST /api/auth/register — JSON body.
   * Does NOT log the user in; call login() afterwards.
   */
  async function register(email, password) {
    const res = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || 'Registration failed');
    }
  }

  function logout() {
    setToken(null);
  }

  /**
   * Wrapper around fetch that automatically adds the Authorization header
   * when a token is present. Use this for all authenticated API calls.
   * Memoised on `token` so its reference is stable between renders.
   */
  const apiFetch = useCallback(
    (url, options = {}) => {
      const headers = {
        'Content-Type': 'application/json',
        ...options.headers,
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      };
      return fetch(url, { ...options, headers });
    },
    [token],
  );

  return (
    <AuthContext.Provider
      value={{ token, isAuthenticated: !!token, login, register, logout, apiFetch }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
