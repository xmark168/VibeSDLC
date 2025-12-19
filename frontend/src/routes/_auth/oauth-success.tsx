import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { Loader2 } from "lucide-react"
import { useEffect } from "react"
import { UsersService } from "@/client"
import { useAppStore } from "@/stores/auth-store"
import { getRedirectPathByRole } from "@/utils/auth"

export const Route = createFileRoute("/_auth/oauth-success")({
  component: OAuthSuccess,
})

function OAuthSuccess() {
  const navigate = useNavigate()
  const setUser = useAppStore((state) => state.setUser)

  useEffect(() => {
    const handleOAuthSuccess = async () => {
      try {
        const params = new URLSearchParams(window.location.search)
        const error = params.get("error")

        // Check for errors first before processing tokens
        if (error) {
          console.error(`OAuth error: ${error}`)
          navigate({ to: `/login?error=${error}` })
          return
        }

        const accessToken = params.get("access_token")
        const refreshToken = params.get("refresh_token")

        if (!accessToken || !refreshToken) {
          throw new Error("Missing tokens in OAuth callback")
        }

        // Save tokens
        localStorage.setItem("access_token", accessToken)
        localStorage.setItem("refresh_token", refreshToken)

        // Fetch user data
        const userData = await UsersService.readUserMe()
        setUser(userData)

        // Redirect based on role
        const redirectPath = getRedirectPathByRole(userData.role)
        navigate({ to: redirectPath })
      } catch (err) {
        console.error("OAuth callback error:", err)
        navigate({ to: "/login?error=oauth_failed" })
      }
    }

    handleOAuthSuccess()
  }, [navigate, setUser])

  return (
    <div className="w-full lg:w-1/2 flex items-center justify-center p-8 bg-card">
      <div className="space-y-4 text-center">
        <Loader2 className="w-8 h-8 animate-spin mx-auto" />
        <h2 className="text-2xl font-bold">Completing OAuth Login</h2>
        <p className="text-muted-foreground">
          Please wait while we authenticate you...
        </p>
      </div>
    </div>
  )
}
