import { createContext, useCallback, useContext, useState } from 'react';
import { API_BASE } from '../utils/config';

const TOKEN_KEY         = 'token';
const MODE_KEY          = 'activeMode';
const BUSINESS_TYPE_KEY = 'businessType';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const [activeMode, setActiveModeState] = useState(
    () => localStorage.getItem(MODE_KEY) || null,
  );
  const [businessType, setBusinessTypeState] = useState(
    () => localStorage.getItem(BUSINESS_TYPE_KEY) || null,
  );

  async function login(email, password) {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ username: email, password }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || 'Login failed');
    }
    const data = await res.json();
    localStorage.setItem(TOKEN_KEY, data.access_token);
    setToken(data.access_token);
  }

  async function register(email, password) {
    const res = await fetch(`${API_BASE}/api/auth/register`, {
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
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(MODE_KEY);
    localStorage.removeItem(BUSINESS_TYPE_KEY);
    setToken(null);
    setActiveModeState(null);
    setBusinessTypeState(null);
  }

  // Fetch profile from server, sync active_mode + business_type into local state.
  // Returns the mode string ('personal'|'business'|null).
  async function loadModeFromServer() {
    const currentToken = localStorage.getItem(TOKEN_KEY);
    if (!currentToken) return null;
    try {
      const res = await fetch(`${API_BASE}/api/profile`, {
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${currentToken}`,
        },
      });
      if (!res.ok) return null;
      const data = await res.json();

      const mode = data.active_mode ?? null;
      if (mode) localStorage.setItem(MODE_KEY, mode);
      else localStorage.removeItem(MODE_KEY);
      setActiveModeState(mode);

      const btype = data.business_type ?? null;
      if (btype) localStorage.setItem(BUSINESS_TYPE_KEY, btype);
      else localStorage.removeItem(BUSINESS_TYPE_KEY);
      setBusinessTypeState(btype);

      return mode;
    } catch {
      return null;
    }
  }

  // Optimistically update mode locally, then persist to server in background.
  function switchMode(mode) {
    setActiveModeState(mode);
    if (mode) localStorage.setItem(MODE_KEY, mode);
    else localStorage.removeItem(MODE_KEY);

    const currentToken = localStorage.getItem(TOKEN_KEY);
    if (currentToken) {
      fetch(`${API_BASE}/api/profile/mode`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${currentToken}`,
        },
        body: JSON.stringify({ active_mode: mode }),
      }).catch(() => {});
    }
  }

  // Update business_type locally + persist to server.
  function setBusinessType(type) {
    setBusinessTypeState(type);
    if (type) localStorage.setItem(BUSINESS_TYPE_KEY, type);
    else localStorage.removeItem(BUSINESS_TYPE_KEY);

    const currentToken = localStorage.getItem(TOKEN_KEY);
    if (currentToken) {
      fetch(`${API_BASE}/api/profile`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${currentToken}`,
        },
        body: JSON.stringify({ business_type: type }),
      }).catch(() => {});
    }
  }

  const apiFetch = useCallback(
    (url, options = {}) => {
      const headers = {
        'Content-Type': 'application/json',
        ...options.headers,
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      };
      return fetch(`${API_BASE}${url}`, { ...options, headers });
    },
    [token],
  );

  return (
    <AuthContext.Provider
      value={{
        token,
        isAuthenticated: !!token,
        activeMode,
        businessType,
        login,
        register,
        logout,
        switchMode,
        setBusinessType,
        loadModeFromServer,
        apiFetch,
      }}
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
