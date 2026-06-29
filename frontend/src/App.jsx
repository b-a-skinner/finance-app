import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Dashboard from './pages/Dashboard';
import Debts from './pages/Debts';
import Expenses from './pages/Expenses';
import Income from './pages/Income';
import Login from './pages/Login';
import Pension from './pages/Pension';
import Register from './pages/Register';
import Savings from './pages/Savings';

function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? children : <Navigate to="/login" replace />;
}

function P({ children }) {
  return <ProtectedRoute>{children}</ProtectedRoute>;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/dashboard" element={<P><Dashboard /></P>} />
          <Route path="/income" element={<P><Income /></P>} />
          <Route path="/expenses" element={<P><Expenses /></P>} />
          <Route path="/debts" element={<P><Debts /></P>} />
          <Route path="/savings" element={<P><Savings /></P>} />
          <Route path="/pension" element={<P><Pension /></P>} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
