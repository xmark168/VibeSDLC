import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';

const Navbar: React.FC = () => {
  const { isAuthenticated, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <nav className="bg-white shadow px-4 py-3 flex items-center justify-between">
      <div className="flex items-center space-x-4">
        <Link to="/" className="text-lg font-bold text-indigo-600">VibeApp</Link>
        {isAuthenticated && (
          <Link to="/dashboard" className="text-gray-700 hover:text-indigo-600">Dashboard</Link>
        )}
      </div>
      <div className="flex items-center space-x-4">
        {!isAuthenticated ? (
          <>
            <Link to="/login" className="text-gray-700 hover:text-indigo-600">Login</Link>
            <Link to="/register" className="text-gray-700 hover:text-indigo-600">Register</Link>
          </>
        ) : (
          <button
            onClick={handleLogout}
            className="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700 focus:outline-none"
          >
            Logout
          </button>
        )}
      </div>
    </nav>
  );
};

export default Navbar;
