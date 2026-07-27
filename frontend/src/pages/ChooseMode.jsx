import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function ChooseMode() {
  const { switchMode, businessType } = useAuth();
  const navigate = useNavigate();

  function choose(mode) {
    switchMode(mode);
    if (mode === 'business') {
      // Show business type setup if not yet captured
      navigate(businessType ? '/' : '/choose-business-type', { replace: true });
    } else {
      navigate('/personal', { replace: true });
    }
  }

  return (
    <div className="choose-mode-page">
      <h1>What would you like to see?</h1>
      <div className="choose-mode-cards">
        <button className="choose-mode-card" onClick={() => choose('personal')}>
          <span className="choose-mode-card__title">Personal</span>
          <span className="choose-mode-card__desc">
            Track your income, savings, debts and net worth
          </span>
        </button>
        <button className="choose-mode-card" onClick={() => choose('business')}>
          <span className="choose-mode-card__title">Business</span>
          <span className="choose-mode-card__desc">
            Track your business income, expenses and profit
          </span>
        </button>
      </div>
    </div>
  );
}
