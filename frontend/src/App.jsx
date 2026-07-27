import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Assets from './pages/Assets';
import Business from './pages/Business';
import Transactions from './pages/Transactions';
import Upcoming from './pages/Upcoming';
import ChooseMode from './pages/ChooseMode';
import ChooseBusinessType from './pages/ChooseBusinessType';
import Dashboard from './pages/Dashboard';
import BusinessProfile from './pages/BusinessProfile';
import PersonalProfile from './pages/PersonalProfile';
import Debts from './pages/Debts';
import Expenses from './pages/Expenses';
import Income from './pages/Income';
import Login from './pages/Login';
import ForgotPassword from './pages/ForgotPassword';
import ResetPassword from './pages/ResetPassword';
import Pension from './pages/Pension';
import Register from './pages/Register';
import Savings from './pages/Savings';
import Admin from './pages/Admin';
import GoalsOnboarding from './pages/GoalsOnboarding';

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
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />

          {/* Business — primary/root experience */}
          <Route path="/" element={<P><Business /></P>} />
          <Route path="/transactions" element={<P><Transactions /></P>} />
          <Route path="/upcoming" element={<P><Upcoming /></P>} />
          <Route path="/profile" element={<P><BusinessProfile /></P>} />

          {/* Personal — subordinate, nested under /personal */}
          <Route path="/personal" element={<P><Dashboard /></P>} />
          <Route path="/personal/income" element={<P><Income /></P>} />
          <Route path="/personal/expenses" element={<P><Expenses /></P>} />
          <Route path="/personal/debts" element={<P><Debts /></P>} />
          <Route path="/personal/assets" element={<P><Assets /></P>} />
          <Route path="/personal/savings" element={<P><Savings /></P>} />
          <Route path="/personal/pension" element={<P><Pension /></P>} />
          <Route path="/personal/profile" element={<P><PersonalProfile /></P>} />

          {/* Shared / onboarding */}
          <Route path="/choose-mode" element={<P><ChooseMode /></P>} />
          <Route path="/choose-business-type" element={<P><ChooseBusinessType /></P>} />
          <Route path="/goals" element={<P><GoalsOnboarding /></P>} />
          <Route path="/admin" element={<Admin />} />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
