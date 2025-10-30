import { ApiError, OpenAPI } from './index'

OpenAPI.BASE = import.meta.env.VITE_API_URL as string
OpenAPI.TOKEN = async () => {
  return localStorage.getItem('access_token') || ''
}

const handleApiError = (error: Error) => {
  if (error instanceof ApiError && [401, 403].includes(error.status)) {
    localStorage.removeItem('access_token')
    window.location.href = '/login'
  }
}

// Optional: attach interceptors if needed
OpenAPI.interceptors.response.use(async (resp) => resp)

