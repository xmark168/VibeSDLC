import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useMemo,
  useRef,
  type ReactNode,
} from 'react'
import axiosInstance, { setAuthContext, setCsrfToken } from '@/core/lib/axios'
import { authAPI } from '@/features/auth/api/auth'
import type { User, JWTPayload, AuthContextValue } from '@/features/auth/types/auth'

const AuthContext = createContext<AuthContextValue | null>(null)

/**
 * Hook to access authentication context
 * Must be used within an AuthProvider
 *
 * @example
 * ```tsx
 * const { user, login, logout, isAuthenticated } = useAuth()
 * ```
 */
export const useAuth = (): AuthContextValue => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

/**
 * Decodes JWT token to extract payload
 * Helper function moved outside component to avoid recreation on each render
 *
 * @param token - JWT token string
 * @returns Decoded payload or null if invalid
 */
const decodeToken = (token: string): JWTPayload | null => {
  try {
    const base64Url = token.split('.')[1]
    if (!base64Url) return null

    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    )
    return JSON.parse(jsonPayload) as JWTPayload
  } catch {
    return null
  }
}

/**
 * Checks if JWT token is expired or will expire soon
 * Includes 60-second buffer to proactively refresh before expiry
 *
 * @param token - JWT token string or null
 * @returns true if token is null, expired, or will expire within 60 seconds
 */
const isTokenExpired = (token: string | null): boolean => {
  if (!token) return true
  const decoded = decodeToken(token)
  if (!decoded || !decoded.exp) return true
  // Add 60-second buffer before expiry to prevent edge-case failures
  const bufferMs = 60 * 1000
  return decoded.exp * 1000 < Date.now() + bufferMs
}

interface AuthProviderProps {
  children: ReactNode
}

/**
 * Authentication context provider
 * Manages user authentication state, tokens, and provides auth methods
 * Refresh token stored as httpOnly cookie (not in state)
 *
 * @example
 * ```tsx
 * <AuthProvider>
 *   <App />
 * </AuthProvider>
 * ```
 */
export const AuthProvider = ({ children }: AuthProviderProps) => {
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [csrfToken, setCsrfTokenState] = useState<string | null>(null)

  // Prevent double initialization in React Strict Mode
  const isInitialized = useRef(false)

  // Initialize auth state on mount
  useEffect(() => {
    // Guard against double initialization in React 18 Strict Mode
    if (isInitialized.current) {
      return
    }
    isInitialized.current = true

    const initializeAuth = async () => {
      try {
        // 1. Get CSRF token first
        try {
          const csrfResponse = await authAPI.getCsrfToken()
          setCsrfTokenState(csrfResponse.csrf_token)
          setCsrfToken(csrfResponse.csrf_token)
        } catch {
          // Continue without CSRF for read-only operations
        }

        // 2. Try to refresh token from cookie (backend will check httpOnly cookie)
        try {
          const response = await authAPI.refreshToken()
          const newAccessToken = response.access_token
          setAccessToken(newAccessToken)

          // 3. Load user data with the new token
          const userResponse = await axiosInstance.get('/users/me', {
            headers: {
              Authorization: `Bearer ${newAccessToken}`
            }
          })
          setUser(userResponse.data)
        } catch {
          // No valid refresh token cookie - user needs to login
          setAccessToken(null)
          setUser(null)
        }
      } catch {
        // Initialization error - treat as logged out
        setAccessToken(null)
        setUser(null)
      } finally {
        setIsLoading(false)
      }
    }

    initializeAuth()
  }, [])

  /**
   * Login function - stores access token (refresh token in httpOnly cookie)
   * @param newAccessToken - JWT access token
   */
  const login = useCallback(async (newAccessToken: string) => {
    setAccessToken(newAccessToken)

    // Load user data
    try {
      const userData = await authAPI.getCurrentUser()
      setUser(userData)
    } catch {
      // If can't load user, clear auth state
      logout()
    }
  }, [])

  /**
   * Logout function - clears all auth state and calls logout API
   */
  const logout = useCallback(async () => {
    // Clear state first for immediate UI update
    setAccessToken(null)
    setUser(null)

    // Call logout API to revoke refresh token and clear cookie
    try {
      await authAPI.logout()
    } catch {
      // Logout endpoint may fail if no token, but that's okay
    }
  }, [])

  /**
   * Update access token (used by axios interceptor after token refresh)
   * @param newAccessToken - New JWT access token
   */
  const updateAccessToken = useCallback((newAccessToken: string) => {
    setAccessToken(newAccessToken)
  }, [])

  /**
   * Update CSRF token (used by axios interceptor after token refresh)
   * @param newCsrfToken - New CSRF token
   */
  const updateCsrfToken = useCallback((newCsrfToken: string) => {
    setCsrfTokenState(newCsrfToken)
    setCsrfToken(newCsrfToken)
  }, [])

  /**
   * Get current access token
   * @returns Current access token or null
   */
  const getAccessToken = useCallback((): string | null => accessToken, [accessToken])

  /**
   * Get current CSRF token
   * @returns Current CSRF token or null
   */
  const getCsrfToken = useCallback((): string | null => csrfToken, [csrfToken])

  // Memoize the context value to prevent unnecessary re-renders
  const value: AuthContextValue = useMemo(
    () => ({
      accessToken,
      refreshToken: null, // Refresh token no longer exposed (in httpOnly cookie)
      user,
      isLoading,
      isAuthenticated: !!accessToken && !!user && !isTokenExpired(accessToken),
      login,
      logout,
      updateAccessToken,
      updateCsrfToken,
      getAccessToken,
      getCsrfToken,
      getRefreshToken: () => null, // Deprecated - refresh token in httpOnly cookie
    }),
    [
      accessToken,
      user,
      isLoading,
      csrfToken,
      login,
      logout,
      updateAccessToken,
      updateCsrfToken,
      getAccessToken,
      getCsrfToken,
    ]
  )

  // Connect axios interceptor with auth context
  // Only update when value changes (memoized above)
  useEffect(() => {
    setAuthContext(value)
  }, [value])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
