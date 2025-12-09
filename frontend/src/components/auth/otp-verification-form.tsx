import { useMutation } from "@tanstack/react-query"
import { Link, useNavigate } from "@tanstack/react-router"
import { motion } from "framer-motion"
import { ArrowLeft } from "lucide-react"
import type React from "react"
import { useEffect, useRef, useState } from "react"
import {
  type ApiError,
  type AuthenticationConfirmCodeData,
  type AuthenticationResendCodeData,
  AuthenticationService,
} from "@/client"
import { Button } from "@/components/ui/button"
import { Route } from "@/routes/_auth/verify-otp"
import { handleError, withToast } from "@/utils"

export function OTPVerificationForm() {
  const [otp, setOtp] = useState(["", "", "", "", "", ""])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")
  const [resendTimer, setResendTimer] = useState(60)
  const inputRefs = useRef<(HTMLInputElement | null)[]>([])
  const navigate = useNavigate()
  const search = Route.useSearch()
  const email = search?.email || ""
  const verifyOtpMutation = useMutation({
    mutationFn: (data: AuthenticationConfirmCodeData) =>
      AuthenticationService.confirmCode(data),

    onSuccess: () => {
      navigate({ to: "/login" })
    },
  })
  const resendCodeMutation = useMutation({
    mutationFn: (data: AuthenticationResendCodeData) =>
      AuthenticationService.resendCode(data),

    onSuccess: () => {
      setResendTimer(60)
      setOtp(["", "", "", "", "", ""])
      setError("")
      inputRefs.current[0]?.focus()
    },
  })
  useEffect(() => {
    // Focus first input on mount
    inputRefs.current[0]?.focus()

    // Countdown timer for resend
    const timer = setInterval(() => {
      setResendTimer((prev) => (prev > 0 ? prev - 1 : 0))
    }, 1000)

    return () => clearInterval(timer)
  }, [])

  const handleChange = (index: number, value: string) => {
    // Only allow numbers
    if (value && !/^\d$/.test(value)) return

    const newOtp = [...otp]
    newOtp[index] = value
    setOtp(newOtp)
    setError("")

    // Auto-focus next input
    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus()
    }

    // Auto-submit when all fields are filled
    if (index === 5 && value) {
      const fullOtp = [...newOtp.slice(0, 5), value].join("")
      handleSubmit(fullOtp)
    }
  }

  const handleKeyDown = (
    index: number,
    e: React.KeyboardEvent<HTMLInputElement>,
  ) => {
    if (e.key === "Backspace" && !otp[index] && index > 0) {
      inputRefs.current[index - 1]?.focus()
    }
  }

  const handlePaste = (e: React.ClipboardEvent) => {
    e.preventDefault()
    const pastedData = e.clipboardData.getData("text").slice(0, 6)

    if (!/^\d+$/.test(pastedData)) return

    const newOtp = pastedData.split("")
    while (newOtp.length < 6) newOtp.push("")

    setOtp(newOtp)

    // Focus last filled input or last input
    const lastFilledIndex = Math.min(pastedData.length, 5)
    inputRefs.current[lastFilledIndex]?.focus()

    // Auto-submit if complete
    if (pastedData.length === 6) {
      handleSubmit(pastedData)
    }
  }

  const handleSubmit = async (code?: string) => {
    const otpCode = code || otp.join("")

    if (otpCode.length !== 6) {
      setError("Please enter all 6 digits")
      return
    }

    setIsLoading(true)
    setError("")

    try {
      await withToast(
        new Promise((resolve, reject) => {
          verifyOtpMutation.mutate(
            {
              requestBody: {
                email,
                code: otpCode,
              },
            },
            {
              onSuccess: resolve,
              onError: (err: Error) => {
                handleError(err as ApiError)
                reject(err)
              },
            },
          )
        }),
        {
          loading: "Verifying code...",
          success: <b>Code verified successfully!</b>,
          error: <b>Code verification failed. Please try again.</b>,
        },
      )
    } catch (err) {
      // Error is already handled by handleError in mutation onError
      // Just ensure loading state is reset
      console.error("OTP verification error:", err)
    } finally {
      setIsLoading(false)
    }
  }

  const handleResend = async () => {
    if (resendTimer > 0) return

    // Simulate resend API call
    try {
      await withToast(
        new Promise((resolve, reject) => {
          resendCodeMutation.mutate(
            {
              requestBody: {
                email,
              },
            },
            {
              onSuccess: resolve,
              onError: (err: Error) => {
                handleError(err as ApiError)
                reject(err)
              },
            },
          )
        }),
        {
          loading: "Resending code...",
          success: <b>Code resent successfully!</b>,
          error: <b>Failed to resend code. Please try again.</b>,
        },
      )
    } catch (error) {
      console.error("Resend error:", error)
    }

    console.log("OTP resent")
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3, duration: 0.6 }}
      className="w-full max-w-md space-y-8"
    >
      {/* Mobile logo */}
      <div className="lg:hidden flex items-center gap-2 mb-8">
        <div className="w-10 h-10 bg-primary rounded-lg flex items-center justify-center">
          <span className="text-primary-foreground font-bold text-xl">M</span>
        </div>
        <span className="text-2xl font-bold">MGX</span>
      </div>

      {/* Back button */}
      <Link
        to="/forgot-password"
        className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back
      </Link>

      <div className="space-y-2">
        <motion.h2
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="text-3xl font-bold text-foreground"
        >
          Enter verification code
        </motion.h2>
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="text-muted-foreground"
        >
          {"We've sent a 6-digit code to your email"}
        </motion.p>
      </div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.6 }}
        className="space-y-6"
      >
        {/* OTP Input */}
        <div className="flex gap-3 justify-center">
          {otp.map((digit, index) => (
            <motion.input
              key={index}
              ref={(el) => {
                inputRefs.current[index] = el
              }}
              type="text"
              inputMode="numeric"
              maxLength={1}
              value={digit}
              onChange={(e) => handleChange(index, e.target.value)}
              onKeyDown={(e) => handleKeyDown(index, e)}
              onPaste={handlePaste}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.7 + index * 0.05 }}
              className={`w-12 h-14 text-center text-2xl font-bold rounded-lg border-2 bg-secondary/50 transition-all focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary ${
                error ? "border-red-500" : "border-border"
              } ${digit ? "border-primary" : ""}`}
            />
          ))}
        </div>

        {/* Error Message */}
        {error && (
          <motion.p
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-sm text-red-500 text-center"
          >
            {error}
          </motion.p>
        )}

        {/* Verify Button */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.9 }}
        >
          <Button
            onClick={() => handleSubmit()}
            disabled={isLoading || otp.join("").length !== 6}
            className="w-full h-12 text-base font-semibold bg-primary hover:bg-primary/90 transition-all disabled:opacity-50"
          >
            {isLoading ? (
              <motion.div
                animate={{ rotate: 360 }}
                transition={{
                  duration: 1,
                  repeat: Number.POSITIVE_INFINITY,
                  ease: "linear",
                }}
                className="w-5 h-5 border-2 border-white border-t-transparent rounded-full"
              />
            ) : (
              "Verify"
            )}
          </Button>
        </motion.div>

        {/* Resend Code */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1 }}
          className="text-center text-sm"
        >
          <p className="text-muted-foreground mb-2">
            {"Didn't receive the code?"}
          </p>
          {resendTimer > 0 ? (
            <p className="text-muted-foreground">
              Resend code in{" "}
              <span className="font-semibold text-foreground">
                {resendTimer}s
              </span>
            </p>
          ) : (
            <button
              onClick={handleResend}
              className="text-foreground underline font-medium cursor-pointer"
            >
              Resend code
            </button>
          )}
        </motion.div>
      </motion.div>
    </motion.div>
  )
}
