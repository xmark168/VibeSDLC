import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import jwtDecode from 'jwt-decode';
import { useAuthStore } from '@/stores/authStore';

interface JwtPayload {
  exp?: number;
  [key: string]: any;
}

/**
 * Custom hook to check JWT expiration and redirect to login if expired.
 * Checks on mount and sets a timer for auto-logout.
 */
export function useTokenExpiration() {
  const navigate = useNavigate();
  const { token, logout } = useAuthStore();

  useEffect(() => {
    if (!token) return;
    let timeoutId: NodeJS.Timeout | null = null;
    try {
      const decoded = jwtDecode<JwtPayload>(token);
      if (!decoded.exp) return;
      const expMs = decoded.exp * 1000;
      const now = Date.now();
      if (expMs <= now) {
        logout();
        navigate('/login', { replace: true });
        return;
      }
      // Set timeout to auto-logout at expiration
      timeoutId = setTimeout(() => {
        logout();
        navigate('/login', { replace: true });
      }, expMs - now);
    } catch (e) {
      // Invalid token, force logout
      logout();
      navigate('/login', { replace: true });
    }
    return () => {
      if (timeoutId) clearTimeout(timeoutId);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, logout, navigate]);
}
