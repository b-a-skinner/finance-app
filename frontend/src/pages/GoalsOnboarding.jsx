import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const GOAL_OPTIONS = [
  { key: 'understanding_my_finances', emoji: '📊', label: 'Understanding my finances' },
  { key: 'building_my_savings',       emoji: '🏦', label: 'Building my savings' },
  { key: 'buying_a_home',             emoji: '🏠', label: 'Buying a home' },
  { key: 'managing_my_spending',      emoji: '💰', label: 'Managing my spending' },
  { key: 'paying_off_debt',           emoji: '🎯', label: 'Paying off debt' },
  { key: 'planning_for_the_future',   emoji: '📈', label: 'Planning for the future' },
];

const SEEN_KEY = 'goals_screen_seen';

export default function GoalsOnboarding() {
  const { apiFetch } = useAuth();
  const navigate = useNavigate();
  const [selected, setSelected] = useState([]);
  const [ready,   setReady]   = useState(false);
  const [saving,  setSaving]  = useState(false);

  useEffect(() => {
    if (localStorage.getItem(SEEN_KEY) === '1') {
      navigate('/personal', { replace: true });
      return;
    }
    apiFetch('/api/profile/onboarding')
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (!data || data.onboarding_completed || data.financial_goals !== null) {
          navigate('/personal', { replace: true });
          return;
        }
        setReady(true);
      })
      .catch(() => navigate('/personal', { replace: true }));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  function toggle(key) {
    setSelected(prev => prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]);
  }

  async function handleContinue() {
    setSaving(true);
    localStorage.setItem(SEEN_KEY, '1');
    try {
      await apiFetch('/api/profile/onboarding', {
        method: 'PATCH',
        body: JSON.stringify({ financial_goals: JSON.stringify(selected) }),
      });
    } catch (_) { /* non-critical */ }
    navigate('/personal', { replace: true });
  }

  function handleSkip() {
    localStorage.setItem(SEEN_KEY, '1');
    navigate('/personal', { replace: true });
  }

  if (!ready) return null;

  return (
    <div className="goals-page">
      <p className="auth-wordmark">fivera</p>
      <h1 className="goals-page-heading">What matters most to you right now?</h1>
      <p className="goals-page-sub">
        We&apos;ll personalise your dashboard based on your goals. You can update this any time in your profile.
      </p>
      <div className="wizard-goals-grid goals-page-grid">
        {GOAL_OPTIONS.map(({ key, emoji, label }) => (
          <button
            key={key}
            type="button"
            className={`wizard-goal-tile${selected.includes(key) ? ' wizard-goal-tile--selected' : ''}`}
            onClick={() => toggle(key)}
          >
            <span className="wizard-goal-emoji">{emoji}</span>
            <span className="wizard-goal-label">{label}</span>
          </button>
        ))}
      </div>
      <div className="goals-page-actions">
        <button
          type="button"
          className="btn-primary goals-page-btn"
          onClick={handleContinue}
          disabled={saving}
        >
          {saving ? 'Saving…' : 'Continue →'}
        </button>
        <p className="goals-page-skip">
          <button type="button" onClick={handleSkip}>Skip for now</button>
        </p>
      </div>
    </div>
  );
}
