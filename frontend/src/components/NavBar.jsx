import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const PERSONAL_LINKS = [
  { to: '/personal',          label: 'Dashboard' },
  { to: '/personal/income',   label: 'Income' },
  { to: '/personal/expenses', label: 'Expenses' },
  { to: '/personal/debts',    label: 'Debts' },
  { to: '/personal/savings',  label: 'Savings & Investments', shortLabel: 'Savings' },
  { to: '/personal/pension',  label: 'Pension' },
  { to: '/personal/assets',   label: 'Assets' },
  { to: '/personal/profile',  label: 'Profile' },
];

const BUSINESS_LINKS = [
  { to: '/',             label: 'Dashboard' },
  { to: '/transactions', label: 'Transactions' },
  { to: '/upcoming',     label: 'Upcoming' },
  { to: '/profile',      label: 'Profile' },
];

export default function NavBar() {
  const { logout, activeMode, businessType, switchMode } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const navRef = useRef(null);

  // Business is the primary/default side — only an explicit 'personal' selection
  // switches the nav away from it.
  const navLinks = activeMode === 'personal' ? PERSONAL_LINKS : BUSINESS_LINKS;

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

  function handleModeSwitch(mode) {
    switchMode(mode);
    if (mode === 'business') {
      navigate(businessType ? '/' : '/choose-business-type', { replace: true });
    } else {
      navigate('/personal', { replace: true });
    }
  }

  return (
    <nav className="navbar" ref={navRef}>
      {/* Left group: logo + pill — always anchored left */}
      <div className="navbar-left">
        <span className="navbar-brand">fivera</span>
        {activeMode && (
          <div className="mode-pill">
            <button
              className={`mode-pill-btn${activeMode === 'personal' ? ' mode-pill-btn--active' : ''}`}
              onClick={() => handleModeSwitch('personal')}
            >
              Personal
            </button>
            <button
              className={`mode-pill-btn${activeMode === 'business' ? ' mode-pill-btn--active' : ''}`}
              onClick={() => handleModeSwitch('business')}
            >
              Business
            </button>
          </div>
        )}
      </div>

      {/* Desktop nav — hidden on mobile via CSS */}
      <div className="navbar-links">
        {navLinks.map(({ to, label, shortLabel }) => (
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
          {navLinks.map(({ to, label }) => (
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
