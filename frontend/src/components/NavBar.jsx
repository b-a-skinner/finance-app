import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const NAV_LINKS = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/income', label: 'Income' },
  { to: '/expenses', label: 'Expenses' },
  { to: '/debts', label: 'Debts' },
  { to: '/assets', label: 'Assets' },
  { to: '/savings', label: 'Savings' },
  { to: '/pension', label: 'Pension' },
  { to: '/profile', label: 'Profile' },
];

export default function NavBar() {
  const { logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate('/login', { replace: true });
  }

  return (
    <nav className="navbar">
      <span className="navbar-brand">FinanceApp</span>
      <div className="navbar-links">
        {NAV_LINKS.map(({ to, label }) => (
          <Link key={to} to={to}>{label}</Link>
        ))}
        <button onClick={handleLogout}>Log out</button>
      </div>
    </nav>
  );
}
