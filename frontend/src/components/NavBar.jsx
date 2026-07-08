import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const PERSONAL_LINKS = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/income',    label: 'Income' },
  { to: '/expenses',  label: 'Expenses' },
  { to: '/debts',     label: 'Debts' },
  { to: '/savings',   label: 'Savings & Investments', shortLabel: 'Savings' },
  { to: '/pension',   label: 'Pension' },
  { to: '/assets',    label: 'Assets' },
  { to: '/profile',   label: 'Profile' },
];

const BUSINESS_LINKS = [
  { to: '/business', label: 'Dashboard' },
  { to: '/profile',  label: 'Profile' },
];

export default function NavBar() {
  const { logout, activeMode, businessType, switchMode } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const navRef = useRef(null);

  const navLinks = activeMode === 'business' ? BUSINESS_LINKS : PERSONAL_LINKS;

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
      navigate(businessType ? '/business' : '/choose-business-type', { replace: true });
    } else {
      navigate('/dashboard', { replace: true });
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
          {activeMode && (
            <div className="mode-pill mode-pill--mobile">
              <button
                className={`mode-pill-btn${activeMode === 'personal' ? ' mode-pill-btn--active' : ''}`}
                onClick={() => { handleModeSwitch('personal'); setOpen(false); }}
              >
                Personal
              </button>
              <button
                className={`mode-pill-btn${activeMode === 'business' ? ' mode-pill-btn--active' : ''}`}
                onClick={() => { handleModeSwitch('business'); setOpen(false); }}
              >
                Business
              </button>
            </div>
          )}
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
