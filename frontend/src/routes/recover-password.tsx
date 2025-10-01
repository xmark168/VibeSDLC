import { Box, Heading, Input, Text } from "@chakra-ui/react"
import { useMutation } from "@tanstack/react-query"
import {
  createFileRoute,
  Link as RouterLink,
  redirect,
} from "@tanstack/react-router"
import { useEffect, useState } from "react"
import { type SubmitHandler, useForm } from "react-hook-form"
import { FiArrowLeft, FiCheck } from "react-icons/fi"

import { type ApiError, LoginService } from "@/client"
import { BrandingSection } from "@/components/ui/branding-section"
import { Button } from "@/components/ui/button"
import { Field } from "@/components/ui/field"
import { FormSection } from "@/components/ui/form-section"
import { SplitScreenLayout } from "@/components/ui/split-screen-layout"
import { isLoggedIn } from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import { emailPattern, handleError } from "@/utils"

interface FormData {
  email: string
}

export const Route = createFileRoute("/recover-password")({
  component: RecoverPassword,
  beforeLoad: async () => {
    if (isLoggedIn()) {
      throw redirect({
        to: "/",
      })
    }
  },
})

function RecoverPassword() {
  const [emailSent, setEmailSent] = useState(false)
  const [submittedEmail, setSubmittedEmail] = useState("")
  const [countdown, setCountdown] = useState(0)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>()
  const { showSuccessToast } = useCustomToast()

  useEffect(() => {
    if (countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000)
      return () => clearTimeout(timer)
    }
  }, [countdown])

  const recoverPassword = async (data: FormData) => {
    await LoginService.recoverPassword({
      email: data.email,
    })
  }

  const mutation = useMutation({
    mutationFn: recoverPassword,
    onSuccess: () => {
      showSuccessToast("Password recovery email sent successfully.")
      setEmailSent(true)
      setCountdown(60)
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
  })

  const onSubmit: SubmitHandler<FormData> = async (data) => {
    setSubmittedEmail(data.email)
    mutation.mutate(data)
  }

  const handleResend = () => {
    if (countdown === 0) {
      mutation.mutate({ email: submittedEmail })
      setCountdown(60)
    }
  }

  if (emailSent) {
    return (
      <SplitScreenLayout
        leftSide={<BrandingSection />}
        rightSide={
          <FormSection>
            <Box className="text-center">
              {/* Success Icon */}
              <Box className="flex justify-center mb-6">
                <Box
                  className="w-20 h-20 rounded-full flex items-center justify-center"
                  bg="#10B981"
                >
                  <FiCheck size={40} color="white" />
                </Box>
              </Box>

              {/* Heading */}
              <Heading size="xl" className="mb-3" fontWeight="bold">
                Check Your Email
              </Heading>

              {/* Message */}
              <Text className="mb-2" color="#6B7280" fontSize="sm">
                We've sent a password reset link to
              </Text>
              <Text className="mb-4" color="black" fontWeight="600">
                {submittedEmail}
              </Text>

              {/* Subtext */}
              <Text className="mb-6" color="#6B7280" fontSize="sm">
                Didn't receive the email? Check your spam folder
              </Text>

              {/* Resend Button */}
              <Button
                onClick={handleResend}
                disabled={countdown > 0}
                variant="outline"
                className="w-full h-12 rounded-lg mb-4"
              >
                {countdown > 0
                  ? `Resend Email (${countdown}s)`
                  : "Resend Email"}
              </Button>

              {/* Back to Login */}
              <RouterLink to="/login">
                <Text
                  className="flex items-center justify-center gap-2"
                  color="#6B7280"
                  fontSize="sm"
                  textDecoration="underline"
                >
                  <FiArrowLeft size={16} />
                  Back to Login
                </Text>
              </RouterLink>
            </Box>
          </FormSection>
        }
      />
    )
  }

  return (
    <SplitScreenLayout
      leftSide={<BrandingSection />}
      rightSide={
        <FormSection>
          <Box as="form" onSubmit={handleSubmit(onSubmit)}>
            {/* Heading */}
            <Heading size="xl" className="mb-3" fontWeight="bold">
              Forgot Password?
            </Heading>

            {/* Instructions */}
            <Text className="mb-6" color="#6B7280" fontSize="sm">
              Enter your email address and we'll send you a link to reset your
              password
            </Text>

            {/* Email Field */}
            <Field
              invalid={!!errors.email}
              errorText={errors.email?.message}
              className="mb-6"
            >
              <Input
                {...register("email", {
                  required: "Email is required",
                  pattern: emailPattern,
                })}
                placeholder="email"
                type="email"
                className="h-12 rounded-lg border-gray-200"
                borderWidth="1px"
              />
            </Field>

            {/* Send Reset Link Button */}
            <Button
              type="submit"
              loading={isSubmitting}
              variant="black"
              className="w-full h-12 rounded-lg mb-6"
            >
              Send Reset Link
            </Button>

            {/* Back to Login */}
            <RouterLink to="/login">
              <Text
                className="flex items-center justify-center gap-2"
                color="#6B7280"
                fontSize="sm"
                textDecoration="underline"
              >
                <FiArrowLeft size={16} />
                Back to Login
              </Text>
            </RouterLink>
          </Box>
        </FormSection>
      }
    />
  )
}