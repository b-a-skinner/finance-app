import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const BUSINESS_TYPES = [
  { value: 'sole_trader',      label: 'Sole trader' },
  { value: 'limited_company',  label: 'Limited company' },
  { value: 'partnership',      label: 'Partnership' },
  { value: 'llp',              label: 'Limited liability partnership (LLP)' },
  { value: 'not_sure',         label: 'Not sure yet' },
];

export default function ChooseBusinessType() {
  const { setBusinessType } = useAuth();
  const navigate = useNavigate();
  const [selected, setSelected] = useState('');
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!selected) return;
    setSaving(true);
    setBusinessType(selected);
    navigate('/', { replace: true });
  }

  return (
    <div className="choose-mode-page">
      <h1>What type of business are you?</h1>
      <form className="choose-business-type-form" onSubmit={handleSubmit}>
        <div className="choose-mode-cards choose-mode-cards--column">
          {BUSINESS_TYPES.map(({ value, label }) => (
            <button
              key={value}
              type="button"
              className={`choose-mode-card choose-mode-card--type${selected === value ? ' choose-mode-card--selected' : ''}`}
              onClick={() => setSelected(value)}
            >
              <span className="choose-mode-card__title">{label}</span>
            </button>
          ))}
        </div>
        <button
          type="submit"
          className="btn-primary choose-business-type-submit"
          disabled={!selected || saving}
        >
          {saving ? 'Continuing…' : 'Continue'}
        </button>
      </form>
    </div>
  );
}
