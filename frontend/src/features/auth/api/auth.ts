import axiosInstance from '@/core/lib/axios'
import { getDeviceFingerprint } from '@/core/lib/fingerprint'
import type {
  LoginResponse,
  RegisterResponse,
  RefreshTokenResponse,
  LogoutResponse,
  UserResponse,
  CsrfTokenResponse,
} from '@/shared/types/api'
import type { RegisterFormData } from '@/features/auth/types/auth'

export const authAPI = {
  // Get CSRF token
  async getCsrfToken(): Promise<CsrfTokenResponse> {
    const response = await axiosInstance.get<CsrfTokenResponse>('/auth/csrf-token')
    return response.data
  },

  // Login
  async login(identifier: string, password: string): Promise<LoginResponse> {
    const deviceFingerprint = await getDeviceFingerprint()

    const response = await axiosInstance.post<LoginResponse>(
      '/auth/login',
      {
        username_or_email: identifier,
        password,
      },
      {
        headers: {
          'X-Device-Fingerprint': deviceFingerprint,
        },
        withCredentials: true, // Enable cookies
      }
    )

    return response.data
  },

  // Register
  async register(userData: RegisterFormData): Promise<RegisterResponse> {
    const deviceFingerprint = await getDeviceFingerprint()

    const response = await axiosInstance.post<RegisterResponse>(
      '/auth/register',
      {
        username: userData.username,
        email: userData.email,
        password: userData.password,
        fullname: userData.fullName,
      },
      {
        headers: {
          'X-Device-Fingerprint': deviceFingerprint,
        },
        withCredentials: true, // Enable cookies
      }
    )

    return response.data
  },

  // Refresh token (reads refresh token from httpOnly cookie)
  async refreshToken(): Promise<RefreshTokenResponse> {
    const deviceFingerprint = await getDeviceFingerprint()

    const response = await axiosInstance.post<RefreshTokenResponse>(
      '/auth/refresh',
      {}, // No body needed - refresh token is in cookie
      {
        headers: {
          'X-Device-Fingerprint': deviceFingerprint,
        },
        withCredentials: true, // Enable cookies
      }
    )

    return response.data
  },

  // Logout (revokes refresh token from cookie)
  async logout(): Promise<LogoutResponse> {
    const response = await axiosInstance.post<LogoutResponse>(
      '/auth/logout',
      {}, // No body needed - refresh token is in cookie
      {
        withCredentials: true, // Enable cookies
      }
    )

    return response.data
  },

  // Get current user profile
  async getCurrentUser(): Promise<UserResponse> {
    const response = await axiosInstance.get<UserResponse>('/users/me')
    return response.data
  },
}
