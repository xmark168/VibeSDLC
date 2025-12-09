import { motion } from "framer-motion"
import { useState } from "react"
import { useNavigate } from "@tanstack/react-router"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useVerify2FALogin } from "@/queries/two-factor"
import { UsersService } from "@/client"
import { useAppStore } from "@/stores/auth-store"
import { getRedirectPathByRole } from "@/utils/auth"
import { withToast } from "@/utils"
import { ShieldCheck, ArrowLeft } from "lucide-react"
import { Link } from "@tanstack/react-router"

interface TwoFactorVerifyFormProps {
  tempToken: string
}

export function TwoFactorVerifyForm({ tempToken }: TwoFactorVerifyFormProps) {
  const [code, setCode] = useState("")
  const navigate = useNavigate()
  const setUser = useAppStore((state) => state.setUser)
  const verify2FAMutation = useVerify2FALogin()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    await withToast(
      new Promise(async (resolve, reject) => {
        verify2FAMutation.mutate(
          { temp_token: tempToken, code: code.replace(/[-\s]/g, "") },
          {
            onSuccess: async (response) => {
              // Store tokens
              localStorage.setItem("access_token", response.access_token)
              localStorage.setItem("refresh_token", response.refresh_token)

              // Fetch user data
              const userData = await UsersService.readUserMe()
              setUser(userData)

              // Redirect based on role
              const redirectPath = getRedirectPathByRole(userData.role)
              navigate({ to: redirectPath })
              resolve(response)
            },
            onError: (error) => {
              reject(error)
            },
          }
        )
      }),
      {
        loading: "Verifying...",
        success: <b>Verification successful!</b>,
        error: <b>Invalid verification code. Please try again.</b>,
      }
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3, duration: 0.6 }}
      className="w-full max-w-md space-y-6"
    >
      <div className="text-center">
        <div className="mx-auto w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mb-4">
          <ShieldCheck className="w-8 h-8 text-primary" />
        </div>
        <motion.h2
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="text-2xl font-bold text-foreground"
        >
          Two-factor authentication
        </motion.h2>
        <p className="text-muted-foreground mt-2">
          Enter the 6-digit code from your authenticator app
        </p>
      </div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
      >
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="code" className="sr-only">
              Verification code
            </Label>
            <Input
              id="code"
              type="text"
              inputMode="numeric"
              placeholder="000000"
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/[^0-9-]/g, ""))}
              className="h-14 text-center text-2xl tracking-[0.5em] font-mono"
              maxLength={10}
              autoFocus
              required
            />
            <p className="text-xs text-muted-foreground text-center">
              You can also use a backup code (XXXX-XXXX)
            </p>
          </div>

          <Button
            type="submit"
            disabled={verify2FAMutation.isPending || code.replace(/[-\s]/g, "").length < 6}
            className="w-full h-12 text-base font-semibold"
          >
            {verify2FAMutation.isPending ? "Verifying..." : "Confirm"}
          </Button>

          <div className="text-center">
            <Link
              to="/login"
              className="text-sm text-muted-foreground hover:text-foreground inline-flex items-center gap-1"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to login
            </Link>
          </div>
        </form>
      </motion.div>
    </motion.div>
  )
}
