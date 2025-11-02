import { useMutation, useQuery } from "@tanstack/react-query"
import { useNavigate } from "@tanstack/react-router"
import { useState } from "react"

import {
  // type Body_login_login_access_token as AccessToken,
  type ApiError,
  type AuthenticationLoginData,
  type AuthenticationRegisterData,
  AuthenticationService,
  type UserPublic,
  UsersService,
} from "@/client"
import { handleError } from "@/utils"

// import { handleError } from "@/utils"

const isLoggedIn = () => {
  return localStorage.getItem("access_token") !== null
}

export const useAuth = () => {
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()
  const { data: user } = useQuery<UserPublic | null, Error>({
    queryKey: ["currentUser"],
    queryFn: UsersService.readUserMe,
    enabled: isLoggedIn(),
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
  }

  const loginMutation = useMutation({
    mutationFn: login,
    onSuccess: () => {
      navigate({ to: "/projects" })
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
  })

  const logout = () => {
    localStorage.removeItem("access_token")
    localStorage.removeItem("refresh_token")
    navigate({ to: "/login" })
  }

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
