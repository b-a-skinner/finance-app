import { useEffect, useRef, useState } from 'react';
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
  const [open, setOpen] = useState(false);
  const navRef = useRef(null);

  useEffect(() => {
    function handleOutside(e) {
      if (navRef.current && !navRef.current.contains(e.target)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleOutside);
    document.addEventListener('touchstart', handleOutside);
    return () => {
      document.removeEventListener('mousedown', handleOutside);
      document.removeEventListener('touchstart', handleOutside);
    };
  }, []);

  function handleLogout() {
    setOpen(false);
    logout();
    navigate('/login', { replace: true });
  }

  return (
    <nav className="navbar" ref={navRef}>
      <span className="navbar-brand">fivera</span>

      {/* Desktop nav — hidden on mobile via CSS */}
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

      {/* Hamburger — hidden on desktop via CSS */}
      <button
        className="navbar-hamburger"
        onClick={() => setOpen(prev => !prev)}
        aria-label="Toggle navigation menu"
        aria-expanded={open}
      >
        ☰
      </button>

      {/* Mobile dropdown */}
      {open && (
        <div className="navbar-mobile-menu">
          {NAV_LINKS.map(({ to, label }) => (
            <Link key={to} to={to} onClick={() => setOpen(false)}>
              {label}
            </Link>
          ))}
          <button onClick={handleLogout}>Log out</button>
        </div>
      )}
    </nav>
  );
}
