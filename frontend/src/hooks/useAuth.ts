import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useNavigate } from "@tanstack/react-router"
import { useState } from "react"

import {
  type ApiError,
  type AuthenticationLoginData,
  type AuthenticationRegisterData,
  AuthenticationService,
  type UserPublic,
  UsersService,
} from "@/client"
import { handleError } from "@/utils"
import toast from "react-hot-toast"
import { useAppStore } from "@/stores/auth-store"
import { getRedirectPathByRole } from "@/utils/auth"
import { isLoginRequires2FA, type LoginResult } from "@/types/two-factor"
import { setLoggingOut } from "@/config/setup"

const isLoggedIn = () => {
  return localStorage.getItem("access_token") !== null
}

export const useAuth = () => {
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const setUser = useAppStore((state) => state.setUser)

  const { data: user } = useQuery<UserPublic | null, Error>({
    queryKey: ["currentUser"],
    queryFn: UsersService.readUserMe,
    enabled: isLoggedIn(),
    refetchOnWindowFocus: false, // User info rarely changes during session
  })

  const signUpMutation = useMutation({
    mutationFn: (data: AuthenticationRegisterData) =>
      AuthenticationService.register(data),

    onSuccess: (_, variables) => {
      navigate({
        to: "/verify-otp",
        search: { email: variables.requestBody.email },
      })
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
  })

  const login = async (data: AuthenticationLoginData): Promise<{ userData?: UserPublic; requires2FA?: boolean; tempToken?: string }> => {
    const response = await AuthenticationService.login(data) as LoginResult
    
    // Check if 2FA is required
    if (isLoginRequires2FA(response)) {
      return {
        requires2FA: true,
        tempToken: response.temp_token,
      }
    }

    // Normal login flow
    localStorage.setItem("access_token", response.access_token)
    localStorage.setItem("refresh_token", response.refresh_token)

    // Fetch user data after login to get role
    const userData = await UsersService.readUserMe()
    setUser(userData)
    return { userData }
  }

  const loginMutation = useMutation({
    mutationFn: login,
    onSuccess: (result) => {
      // If 2FA is required, redirect to 2FA verification page
      if (result.requires2FA && result.tempToken) {
        navigate({ 
          to: "/verify-2fa",
          search: { token: result.tempToken }
        })
        return
      }

      // Normal login success - redirect based on user role
      if (result.userData) {
        const redirectPath = getRedirectPathByRole(result.userData.role)
        navigate({ to: redirectPath })
      }
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
  })

  const logout = useMutation({
    mutationFn: async () => {
      // Set flag to prevent token refresh during logout
      setLoggingOut(true)
      // Cancel all pending queries to prevent 401 errors triggering refresh
      await queryClient.cancelQueries()
      return AuthenticationService.logout()
    },
    onSuccess: () => {
      toast.success("Logout successful")
      localStorage.removeItem("access_token")
      localStorage.removeItem("refresh_token")
      setUser(undefined)
      queryClient.clear() // Clear all cached data
      navigate({ to: "/login" })
      // Reset flag after navigation
      setTimeout(() => setLoggingOut(false), 100)
    },
    onError: (err: ApiError) => {
      setLoggingOut(false)
      handleError(err)
    },
  })

  return {
    signUpMutation,
    loginMutation,
    logout,
    user,
    error,
    resetError: () => setError(null),
  }
}

export { isLoggedIn }
export default useAuth
