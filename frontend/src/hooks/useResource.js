import { useCallback, useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';

/**
 * Generic hook for authenticated CRUD against a single REST resource endpoint.
 * All five finance resource pages (income, expenses, debts, savings, pension) use this.
 */
export function useResource(url) {
  const { apiFetch } = useAuth();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    apiFetch(url)
      .then(r => {
        if (!r.ok) throw new Error('Failed to load');
        return r.json();
      })
      .then(data => { setItems(data); setLoading(false); })
      .catch(e => { setError(e.message); setLoading(false); });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const create = useCallback(async (data) => {
    const res = await apiFetch(url, { method: 'POST', body: JSON.stringify(data) });
    if (!res.ok) {
      const b = await res.json().catch(() => ({}));
      throw new Error(b.detail || 'Failed to create');
    }
    const item = await res.json();
    setItems(prev => [...prev, item]);
    return item;
  }, [apiFetch, url]);

  const update = useCallback(async (id, data) => {
    const res = await apiFetch(`${url}/${id}`, { method: 'PUT', body: JSON.stringify(data) });
    if (!res.ok) {
      const b = await res.json().catch(() => ({}));
      throw new Error(b.detail || 'Failed to update');
    }
    const item = await res.json();
    setItems(prev => prev.map(i => (i.id === id ? item : i)));
    return item;
  }, [apiFetch, url]);

  const remove = useCallback(async (id) => {
    const res = await apiFetch(`${url}/${id}`, { method: 'DELETE' });
    if (!res.ok) {
      const b = await res.json().catch(() => ({}));
      throw new Error(b.detail || 'Failed to delete');
    }
    setItems(prev => prev.filter(i => i.id !== id));
  }, [apiFetch, url]);

  return { items, loading, error, create, update, remove };
}
