// JWT Token Payload (minimal - only contains user_id)
export interface JWTPayload {
  sub: string // User ID
  exp: number // Expiration timestamp
}

// User object (loaded from /users/me endpoint)
export interface User {
  id: number
  username: string
  email: string
  fullname: string | null
  is_active: boolean
  balance: number
  created_at: string
  updated_at: string
  locked_until: string | null
  failed_login_attempts: number
  two_factor_enabled: boolean
  address: string | null
}

// Auth Context Value
export interface AuthContextValue {
  accessToken: string | null
  refreshToken: string | null // Deprecated - now in httpOnly cookie
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (accessToken: string) => Promise<void>
  logout: () => Promise<void>
  updateAccessToken: (newAccessToken: string) => void
  updateCsrfToken: (newCsrfToken: string) => void
  getAccessToken: () => string | null
  getCsrfToken: () => string | null
  getRefreshToken: () => string | null // Deprecated - always returns null
}

// Login form data
export interface LoginFormData {
  identifier: string
  password: string
}

// Register form data
export interface RegisterFormData {
  username: string
  email: string
  password: string
  confirmPassword: string
  fullName?: string
}
