import { useQuery } from "@tanstack/react-query"
import type React from "react"
import { useEffect } from "react"
import { type UserPublic, UsersService } from "@/client"
import { useAppStore } from "@/stores/auth-store"

export default function AuthProvider({
  children,
}: {
  children: React.ReactNode
}) {
  const setUser = useAppStore((state) => state.setUser)
  const setIsLoading = useAppStore((state) => state.setIsLoading)

  const accessToken = localStorage.getItem("access_token")

  const {
    data: user,
    isLoading,
    error,
  } = useQuery<UserPublic | null, Error>({
    queryKey: ["currentUser"],
    queryFn: UsersService.readUserMe,
    enabled: !!accessToken,
    retry: false,
    refetchOnWindowFocus: false,
  })

  useEffect(() => {
    // No token - set loading to false immediately
    if (!accessToken) {
      setIsLoading(false)
      return
    }

    if (user) {
      setUser(user)
    } else if (error) {
      setUser(undefined)
      localStorage.removeItem("access_token")
    } else if (!isLoading) {
      // Query finished but no user and no error
      setIsLoading(false)
    }
  }, [user, error, isLoading, accessToken, setUser, setIsLoading])

  return <>{children}</>
}
