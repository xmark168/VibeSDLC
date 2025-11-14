import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import type { AuthContextValue } from '@/features/auth/types/auth'
import type { RefreshTokenResponse } from '@/shared/types/api'
import { getDeviceFingerprint } from '@/core/lib/fingerprint'
import { API_CONFIG } from '@/core/constants/config'

// Create axios instance
const axiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Enable cookies for httpOnly refresh tokens
  timeout: API_CONFIG.TIMEOUT, // 30 seconds
})

// Store auth context setter (will be set from AuthProvider)
let authContextSetter: AuthContextValue | null = null

// Store CSRF token
let csrfToken: string | null = null

export const setAuthContext = (setter: AuthContextValue) => {
  authContextSetter = setter
}

export const setCsrfToken = (token: string) => {
  csrfToken = token
}

// Request interceptor - add access token and CSRF token to requests
axiosInstance.interceptors.request.use(
  (config) => {
    const accessToken = authContextSetter?.getAccessToken?.()

    // Add Authorization header if access token exists
    if (accessToken) {
      config.headers.Authorization = `Bearer ${accessToken}`
    }

    // Add CSRF token to state-changing requests (POST, PUT, PATCH, DELETE)
    const isStateMutating = ['post', 'put', 'patch', 'delete'].includes(
      config.method?.toLowerCase() || ''
    )
    if (isStateMutating && csrfToken) {
      config.headers['X-CSRF-Token'] = csrfToken
    }

    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor - handle 401 and auto refresh token
let isRefreshing = false

interface QueueItem {
  resolve: (token: string) => void
  reject: (error: any) => void
}

let failedQueue: QueueItem[] = []

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error)
    } else {
      prom.resolve(token!)
    }
  })
  failedQueue = []
}

interface CustomAxiosRequestConfig extends InternalAxiosRequestConfig {
  _retry?: boolean
}

axiosInstance.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as CustomAxiosRequestConfig

    // If error is not 401 or request already retried, reject
    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error)
    }

    // If already refreshing, queue this request
    if (isRefreshing) {
      return new Promise<string>((resolve, reject) => {
        failedQueue.push({ resolve, reject })
      })
        .then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`
          return axiosInstance(originalRequest)
        })
        .catch((err) => {
          return Promise.reject(err)
        })
    }

    originalRequest._retry = true
    isRefreshing = true

    try {
      // Get device fingerprint for tracking
      const deviceFingerprint = await getDeviceFingerprint()

      // Call refresh token endpoint (refresh token is in httpOnly cookie)
      const response = await axios.post<RefreshTokenResponse>(
        `${axiosInstance.defaults.baseURL}/auth/refresh`,
        {}, // No body - refresh token is in cookie
        {
          headers: {
            'Content-Type': 'application/json',
            'X-Device-Fingerprint': deviceFingerprint,
            'X-CSRF-Token': csrfToken || '', // Include CSRF token
          },
          withCredentials: true, // Enable cookies
        }
      )

      const { access_token } = response.data

      // Update access token in auth context
      authContextSetter?.updateAccessToken?.(access_token)

      // Process queued requests
      processQueue(null, access_token)

      // Retry original request with new token
      originalRequest.headers.Authorization = `Bearer ${access_token}`
      return axiosInstance(originalRequest)
    } catch (refreshError) {
      processQueue(refreshError, null)
      // Logout on refresh failure
      authContextSetter?.logout?.()
      return Promise.reject(refreshError)
    } finally {
      isRefreshing = false
    }
  }
)

export default axiosInstance
