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

// import { handleError } from "@/utils"

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

  const login = async (data: AuthenticationLoginData) => {
    const response = await AuthenticationService.login(data)
    localStorage.setItem("access_token", response.access_token)
    localStorage.setItem("refresh_token", response.refresh_token)

    // Fetch user data after login to get role
    const userData = await UsersService.readUserMe()
    setUser(userData)
    return userData
  }

  const loginMutation = useMutation({
    mutationFn: login,
    onSuccess: (userData) => {
      // Redirect based on user role
      const redirectPath = getRedirectPathByRole(userData.role)
      navigate({ to: redirectPath })
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
  })

  const logout = useMutation({
    mutationFn: () => AuthenticationService.logout(),
    onSuccess: () => {
      toast.success("Logout successful")
      localStorage.removeItem("access_token")
      localStorage.removeItem("refresh_token")
      setUser(undefined)
      queryClient.invalidateQueries({ queryKey: ["currentUser"] })
      navigate({ to: "/login" })
    },
    onError: (err: ApiError) => {
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
