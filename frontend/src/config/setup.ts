import axios from 'axios'
import type { AxiosInstance, AxiosResponse } from 'axios'
import { OpenAPI } from '../client/index'
import { AuthenticationService } from '../client/sdk.gen'

OpenAPI.BASE = import.meta.env.VITE_API_URL as string
OpenAPI.TOKEN = async () => {
    return localStorage.getItem('access_token') || ''
}

let isRefreshing = false
let refreshSubscribers: Array<(token: string) => void> = []

const subscribeTokenRefresh = (callback: (token: string) => void) => {
    refreshSubscribers.push(callback)
}

const onTokenRefreshed = (token: string) => {
    refreshSubscribers.forEach((callback) => callback(token))
    refreshSubscribers = []
}

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

        localStorage.setItem('access_token', response.access_token)
        localStorage.setItem('refresh_token', response.refresh_token)

        return response.access_token
    } catch (error) {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
        return null
    }
}

OpenAPI.interceptors.response.use(
    async (response: AxiosResponse): Promise<AxiosResponse> => {
        if (response.status === 401) {
            const originalRequest = response.config as any

            if (!originalRequest._retry) {
                if (isRefreshing) {
                    return new Promise((resolve, reject) => {
                        subscribeTokenRefresh(async (token: string) => {
                            originalRequest.headers['Authorization'] = `Bearer ${token}`
                            try {
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
                    onTokenRefreshed(newToken)

                    originalRequest.headers['Authorization'] = `Bearer ${newToken}`
                    const axiosInstance: AxiosInstance = axios.create()
                    return axiosInstance.request(originalRequest)
                }
            }
        }

        return response
    }
)

