import React from 'react';
import { useTokenExpiration } from '@/hooks/useTokenExpiration';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Navbar from '@/components/layout/Navbar';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import ProtectedRoute from '@/routes/ProtectedRoute';
import PublicRoute from '@/routes/PublicRoute';

const App: React.FC = () => {
  useTokenExpiration();
  return (
    <BrowserRouter>
      <Navbar />
      <Routes>
        {/* Public routes */}
        <Route element={<PublicRoute />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
        </Route>
        {/* Protected routes example (add your protected pages here) */}
        <Route element={<ProtectedRoute />}>
          {/* <Route path="/dashboard" element={<DashboardPage />} /> */}
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

export default App;
