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

  const accessToken = localStorage.getItem("accessToken")

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
      localStorage.removeItem("accessToken")
    }
  }, [user, error, setUser])

  return <>{children}</>
}
