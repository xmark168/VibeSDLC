// Auth API Response Types
export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
}

export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
}

export interface RegisterResponse {
  message: string
  tokens: TokenResponse
  user: UserResponse
}

export interface RefreshTokenResponse {
  access_token: string
  token_type: string
  expires_in: number
}

export interface LogoutResponse {
  message: string
}

export interface CsrfTokenResponse {
  csrf_token: string
}

export interface UserResponse {
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

// API Error Response
export interface ValidationError {
  type: string
  loc: (string | number)[]
  msg: string
  input?: any
}

export interface APIError {
  detail: string | ValidationError[]
}
