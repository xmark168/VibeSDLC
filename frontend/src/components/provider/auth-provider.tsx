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
  })

  useEffect(() => {
    if (user) {
      setUser(user)
    } else if (error) {
      setUser(undefined)
      localStorage.removeItem("access_token")
    }
  }, [user, error, setUser])

  return <>{children}</>
}
