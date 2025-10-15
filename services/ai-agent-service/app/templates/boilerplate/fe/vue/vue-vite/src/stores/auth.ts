import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/services/api'
import type { User, LoginCredentials, RegisterData } from '@/types/auth'

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref<User | null>(null)
  const token = ref<string | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const isAuthenticated = computed(() => !!token.value && !!user.value)

  // Actions
  const login = async (credentials: LoginCredentials) => {
    isLoading.value = true
    error.value = null

    try {
      const response = await authApi.login(credentials)
      const { user: userData, access_token } = response.data

      user.value = userData
      token.value = access_token

      // Store in localStorage
      localStorage.setItem('auth_token', access_token)
      localStorage.setItem('auth_user', JSON.stringify(userData))

      return response.data
    } catch (err: any) {
      const errorMessage = err.response?.data?.message || 'Login failed'
      error.value = errorMessage
      throw err
    } finally {
      isLoading.value = false
    }
  }

  const register = async (data: RegisterData) => {
    isLoading.value = true
    error.value = null

    try {
      const response = await authApi.register(data)
      return response.data
    } catch (err: any) {
      const errorMessage = err.response?.data?.message || 'Registration failed'
      error.value = errorMessage
      throw err
    } finally {
      isLoading.value = false
    }
  }

  const logout = () => {
    user.value = null
    token.value = null
    error.value = null

    // Clear localStorage
    localStorage.removeItem('auth_token')
    localStorage.removeItem('auth_user')
  }

  const clearError = () => {
    error.value = null
  }

  const initializeAuth = () => {
    const storedToken = localStorage.getItem('auth_token')
    const storedUser = localStorage.getItem('auth_user')

    if (storedToken && storedUser) {
      try {
        token.value = storedToken
        user.value = JSON.parse(storedUser)
      } catch (err) {
        // Invalid stored data, clear it
        logout()
      }
    }
  }

  const updateUser = (userData: Partial<User>) => {
    if (user.value) {
      user.value = { ...user.value, ...userData }
      localStorage.setItem('auth_user', JSON.stringify(user.value))
    }
  }

  const refreshToken = async () => {
    if (!token.value) return

    try {
      const response = await authApi.refreshToken(token.value)
      const { access_token } = response.data

      token.value = access_token
      localStorage.setItem('auth_token', access_token)

      return access_token
    } catch (err) {
      // Refresh failed, logout user
      logout()
      throw err
    }
  }

  return {
    // State
    user,
    token,
    isLoading,
    error,
    
    // Getters
    isAuthenticated,
    
    // Actions
    login,
    register,
    logout,
    clearError,
    initializeAuth,
    updateUser,
    refreshToken,
  }
}, {
  persist: {
    key: 'auth-store',
    storage: localStorage,
    paths: ['user', 'token'],
  },
})
