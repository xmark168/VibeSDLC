import { createFileRoute, redirect, useNavigate } from "@tanstack/react-router"
import { useEffect, useState, useRef } from "react"
import { account } from "@/lib/appwrite"
import useAuth from "@/hooks/useAuth"
import { withToast } from "@/utils"
import { Loader2 } from "lucide-react"

export const Route = createFileRoute("/_auth/oauth-callback")({
  component: OAuthCallback,
})

function OAuthCallback() {
  const navigate = useNavigate()
  const { loginMutation } = useAuth()
  const [isProcessing, setIsProcessing] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const hasCalledRef = useRef(false)

  useEffect(() => {
    // Prevent duplicate calls using ref
    if (hasCalledRef.current) {
      return
    }
    hasCalledRef.current = true

    const handleOAuthCallback = async () => {
      try {
        // Get user info from Appwrite after OAuth redirect
        const user = await account.get()

        if (!user.email) {
          throw new Error("Email not found in OAuth response")
        }

        // Call backend login with OAuth provider data
        await withToast(
          new Promise((resolve, reject) => {
            loginMutation.mutate(
              {
                requestBody: {
                  email: user.email,
                  fullname: user.name || user.email.split("@")[0],
                  login_provider: true,
                },
              },
              {
                onSuccess: () => {
                  setIsProcessing(false)
                  resolve(null)
                  // Navigate after successful login
                  navigate({ to: "/projects" })
                },
                onError: (err) => {
                  setIsProcessing(false)
                  reject(err)
                },
              },
            )
          }),
          {
            loading: "Completing OAuth login...",
            success: <b>OAuth login successful!</b>,
            error: <b>OAuth login failed. Please try again.</b>,
          },
        )
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "OAuth callback failed"
        setError(errorMessage)
        setIsProcessing(false)
        console.error("OAuth callback error:", err)

        setTimeout(() => {
          navigate({ to: "/login" })
        }, 3000)
      }
    }

    handleOAuthCallback()
  }, [])

  if (error) {
    return (
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8 bg-card">
        <div className="space-y-4 text-center">
          <h2 className="text-2xl font-bold text-red-500">Login Failed</h2>
          <p className="text-muted-foreground">{error}</p>
          <p className="text-sm text-muted-foreground">
            Redirecting to login page...
          </p>
        </div>
      </div>
    )
  }

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

