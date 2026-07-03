import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const NAV_LINKS = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/income', label: 'Income' },
  { to: '/expenses', label: 'Expenses' },
  { to: '/debts', label: 'Debts' },
  { to: '/savings', label: 'Savings & Investments', shortLabel: 'Savings' },
  { to: '/pension', label: 'Pension' },
  { to: '/assets', label: 'Assets' },
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
      <span className="navbar-brand">fivera</span>
      <div className="navbar-links">
        {NAV_LINKS.map(({ to, label, shortLabel }) => (
          <Link key={to} to={to}>
            {shortLabel ? (
              <>
                <span className="nav-label-mobile">{shortLabel}</span>
                <span className="nav-label-desktop">{label}</span>
              </>
            ) : label}
          </Link>
        ))}
        <button onClick={handleLogout}>Log out</button>
      </div>
    </nav>
  );
}
