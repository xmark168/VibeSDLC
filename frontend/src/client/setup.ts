import axios from 'axios'
import type { AxiosInstance, AxiosResponse } from 'axios'
import { OpenAPI } from './index'
import { AuthenticationService } from './sdk.gen'

OpenAPI.BASE = import.meta.env.VITE_API_URL as string
OpenAPI.TOKEN = async () => {
    return localStorage.getItem('access_token') || ''
}

// Track if we're currently refreshing to avoid multiple simultaneous refresh calls
let isRefreshing = false
let refreshSubscribers: Array<(token: string) => void> = []

// Add subscribers waiting for new token
const subscribeTokenRefresh = (callback: (token: string) => void) => {
    refreshSubscribers.push(callback)
}

// Notify all subscribers when new token is available
const onTokenRefreshed = (token: string) => {
    refreshSubscribers.forEach((callback) => callback(token))
    refreshSubscribers = []
}

// Refresh the access token
const refreshAccessToken = async (): Promise<string | null> => {
    const refreshToken = localStorage.getItem('refresh_token')

    if (!refreshToken) {
        return null
    }

    try {
        const response = await AuthenticationService.refreshToken({
            requestBody: {
                refresh_token: refreshToken
            }
        })

        // Store new tokens
        localStorage.setItem('access_token', response.access_token)
        localStorage.setItem('refresh_token', response.refresh_token)

        return response.access_token
    } catch (error) {
        // Refresh token failed or expired
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
        return null
    }
}

// Response interceptor to handle 401 errors and retry with refreshed token
OpenAPI.interceptors.response.use(
    async (response: AxiosResponse): Promise<AxiosResponse> => {
        // Check if response contains a 401 error status
        if (response.status === 401) {
            const originalRequest = response.config as any

            // Check if we haven't already tried to refresh
            if (!originalRequest._retry) {
                if (isRefreshing) {
                    // If already refreshing, wait for the new token
                    return new Promise((resolve, reject) => {
                        subscribeTokenRefresh(async (token: string) => {
                            originalRequest.headers['Authorization'] = `Bearer ${token}`
                            try {
                                // Retry the request with new token
                                const axiosInstance: AxiosInstance = axios.create()
                                const retryResponse = await axiosInstance.request(originalRequest)
                                resolve(retryResponse)
                            } catch (error) {
                                reject(error)
                            }
                        })
                    })
                }

                originalRequest._retry = true
                isRefreshing = true

                const newToken = await refreshAccessToken()
                isRefreshing = false

                if (newToken) {
                    // Notify all subscribers
                    onTokenRefreshed(newToken)

                    // Retry the original request with new token
                    originalRequest.headers['Authorization'] = `Bearer ${newToken}`
                    const axiosInstance: AxiosInstance = axios.create()
                    return axiosInstance.request(originalRequest)
                }
            }
        }

        return response
    }
)

