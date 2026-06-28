import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

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
        <Link to="/dashboard">Dashboard</Link>
        <button onClick={handleLogout}>Log out</button>
      </div>
    </nav>
  );
}
