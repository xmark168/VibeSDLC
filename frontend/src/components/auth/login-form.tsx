import { Link } from "@tanstack/react-router"
import { motion } from "framer-motion"
import type React from "react"
import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import useAuth from "@/hooks/useAuth"
import { toast } from "@/lib/toast"
import { Facebook, Github, Loader2, Eye, EyeOff } from "lucide-react"
import { FaGooglePlusG } from "react-icons/fa6";

const REMEMBER_EMAIL_KEY = "vibeSDLC_remembered_email"

type OAuthLoadingProvider = "google" | "github" | "facebook" | null

export function LoginForm() {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [showPassword, setShowPassword] = useState(false)
  const [rememberMe, setRememberMe] = useState(false)
  const [oauthLoading, setOauthLoading] = useState<OAuthLoadingProvider>(null)
  const [oauthError, setOauthError] = useState<string | null>(null)
  const { loginMutation } = useAuth()


  useEffect(() => {
    const rememberedEmail = localStorage.getItem(REMEMBER_EMAIL_KEY)
    if (rememberedEmail) {
      setEmail(rememberedEmail)
      setRememberMe(true)
    }

    // Check for OAuth error in URL
    const params = new URLSearchParams(window.location.search)
    const error = params.get('error')
    if (error) {
      // Map error codes to user-friendly messages
      const errorMessages: Record<string, string> = {
        'account_locked': 'Your account has been locked. Please contact support.',
        'account_deactivated': 'Your account has been deactivated. Please contact support.',
        'oauth_failed': 'OAuth authentication failed. Please try again.',
      }
      setOauthError(errorMessages[error] || 'An error occurred during login. Please try again.')
      
      // Clear error from URL without reloading
      window.history.replaceState({}, '', window.location.pathname)
    }
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (rememberMe) {
      localStorage.setItem(REMEMBER_EMAIL_KEY, email)
    } else {
      localStorage.removeItem(REMEMBER_EMAIL_KEY)
    }

    loginMutation.mutate(
      {
        requestBody: { email, password },
      },
      {
        onSuccess: () => {
          toast.success("Welcome back!")
        },
        onError: (error: any) => {
          // handleError already shows toast in useAuth, but we can add more specific message here
          const errorMessage = error?.body?.detail || "Invalid email or password"
          console.error("Login error:", error)
        },
      },
    )
  }

  const handleLoginGoogle = () => {
    if (oauthLoading) return
    setOauthLoading("google")
    window.location.href = `${import.meta.env.VITE_API_URL}/api/v1/auth/google`;
  };

  const handleLoginGithub = () => {
    if (oauthLoading) return
    setOauthLoading("github")
    window.location.href = `${import.meta.env.VITE_API_URL}/api/v1/auth/github`;
  };

  const handleLoginFacebook = () => {
    if (oauthLoading) return
    setOauthLoading("facebook")
    window.location.href = `${import.meta.env.VITE_API_URL}/api/v1/auth/facebook`;
  };

  const isOAuthDisabled = oauthLoading !== null


  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3, duration: 0.6 }}
      className="w-full max-w-md space-y-2"
    >
      {/* Logo Mobile */}
      <div className="lg:hidden flex items-center justify-center mb-8">
        <img 
          src="/assets/images/logov2.png" 
          alt="VibeSDLC Logo" 
          className="h-12 w-auto"
        />
      </div>

      <div className="">
        <motion.h2
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="text-3xl font-bold text-foreground"
        >
          Welcome back
        </motion.h2>
      </div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
        className="space-y-6"
      >

        <div className="relative">
          {/* <div className="relative flex justify-center text-sm"> */}
          <span className="bg-card text-muted-foreground">
            Sign in to start with your AI team
          </span>
        </div>
        {/* </div> */}

        {/* Form Email/Password */}
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="space-y-2">
            <Label htmlFor="email" className="sr-only">
              Email
            </Label>
            <Input
              id="email"
              type="email"
              placeholder="Your email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="h-12"
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="password" className="sr-only">
              Password
            </Label>
            <div className="relative">
              <Input
                id="password"
                type={showPassword ? "text" : "password"}
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="h-12 pr-10"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                tabIndex={-1}
              >
                {showPassword ? (
                  <EyeOff className="h-5 w-5" />
                ) : (
                  <Eye className="h-5 w-5" />
                )}
              </button>
            </div>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Checkbox
                id="remember"
                checked={rememberMe}
                onCheckedChange={(checked) => setRememberMe(checked as boolean)}
                className="border-muted-foreground data-[state=checked]:bg-primary data-[state=checked]:border-primary"
              />
              <Label
                htmlFor="remember"
                className="text-sm text-muted-foreground cursor-pointer select-none"
              >
                Remember me
              </Label>
            </div>
            <Link
              to="/forgot-password"
              className="text-sm text-muted-foreground transition-colors underline hover:text-foreground"
            >
              Forgot password?
            </Link>
          </div>

          <Button
            type="submit"
            disabled={loginMutation.isPending}
            className="w-full h-12 text-base font-semibold bg-primary hover:bg-primary/90 transition-all"
          >
            {loginMutation.isPending ? "Signing in..." : "Sign in"}
          </Button>

          <div className="relative my-2">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-border"></div>
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-card px-2 text-muted-foreground">
                Or continue with
              </span>
            </div>
          </div>

          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row gap-3">
              <Button
                type="button"
                onClick={handleLoginGoogle}
                variant="outline"
                disabled={isOAuthDisabled}
                className="flex-1 h-12 border-2 border-border hover:bg-transparent hover:border-border disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {oauthLoading === "google" ? (
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                ) : (
                  <FaGooglePlusG className="mr-2 h-5 w-5 text-[#EA4335]" />
                )}
                <span className="font-medium">Google</span>
              </Button>
              <Button
                type="button"
                onClick={handleLoginGithub}
                variant="outline"
                disabled={isOAuthDisabled}
                className="flex-1 h-12 border-2 border-border hover:bg-transparent hover:border-border disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {oauthLoading === "github" ? (
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                ) : (
                  <Github className="mr-2 h-5 w-5" />
                )}
                <span className="font-medium">GitHub</span>
              </Button>
              <Button
                type="button"
                onClick={handleLoginFacebook}
                variant="outline"
                disabled={isOAuthDisabled}
                className="flex-1 h-12 border-2 border-border hover:bg-transparent hover:border-border disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {oauthLoading === "facebook" ? (
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                ) : (
                  <Facebook className="mr-2 h-5 w-5 text-[#1877F2]" />
                )}
                <span className="font-medium">Facebook</span>
              </Button>
            </div>
          </div>
          <div className="text-center text-sm text-muted-foreground">
            {"Don't have an account? "}
            <Link
              to="/signup"
              className="text-foreground underline transition-colors"
            >
              Create new account
            </Link>
          </div>
        </form>
      </motion.div>
    </motion.div>
  )
}
