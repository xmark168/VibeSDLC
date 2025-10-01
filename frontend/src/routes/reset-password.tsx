import { Box, Heading, Input, Text } from "@chakra-ui/react"
import { useMutation } from "@tanstack/react-query"
import { createFileRoute, redirect, useNavigate } from "@tanstack/react-router"
import { useState } from "react"
import { type SubmitHandler, useForm } from "react-hook-form"

import { type ApiError, LoginService, type NewPassword } from "@/client"
import { BrandingSection } from "@/components/ui/branding-section"
import { Button } from "@/components/ui/button"
import { Field } from "@/components/ui/field"
import { FormSection } from "@/components/ui/form-section"
import { PasswordRequirements } from "@/components/ui/password-requirements"
import { PasswordStrengthIndicator } from "@/components/ui/password-strength-indicator"
import { SplitScreenLayout } from "@/components/ui/split-screen-layout"
import { isLoggedIn } from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import {
  calculatePasswordStrength,
  confirmPasswordRules,
  getPasswordRequirements,
  handleError,
  passwordRules,
} from "@/utils"

interface NewPasswordForm extends NewPassword {
  confirm_password: string
}

export const Route = createFileRoute("/reset-password")({
  component: ResetPassword,
  beforeLoad: async () => {
    if (isLoggedIn()) {
      throw redirect({
        to: "/",
      })
    }
  },
})

function ResetPassword() {
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")

  const {
    register,
    handleSubmit,
    getValues,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<NewPasswordForm>({
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      new_password: "",
    },
  })
  const { showSuccessToast } = useCustomToast()
  const navigate = useNavigate()

  const passwordStrength = calculatePasswordStrength(newPassword)
  const requirements = getPasswordRequirements(newPassword)
  const passwordsMatch = confirmPassword && newPassword === confirmPassword

  const resetPassword = async (data: NewPassword) => {
    const token = new URLSearchParams(window.location.search).get("token")
    if (!token) return
    await LoginService.resetPassword({
      requestBody: { new_password: data.new_password, token: token },
    })
  }

  const mutation = useMutation({
    mutationFn: resetPassword,
    onSuccess: () => {
      showSuccessToast("Password updated successfully.")
      reset()
      navigate({ to: "/login" })
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
  })

  const onSubmit: SubmitHandler<NewPasswordForm> = async (data) => {
    mutation.mutate(data)
  }

  return (
    <SplitScreenLayout
      leftSide={<BrandingSection />}
      rightSide={
        <FormSection>
          <Box as="form" onSubmit={handleSubmit(onSubmit)}>
            {/* Heading */}
            <Heading size="xl" className="mb-3" fontWeight="bold">
              Reset Your Password
            </Heading>

            {/* Instructions */}
            <Text className="mb-6" color="#6B7280" fontSize="sm">
              Please enter your new password and confirm it to reset your
              password
            </Text>

            {/* New Password Field */}
            <Field
              invalid={!!errors.new_password}
              errorText={errors.new_password?.message}
              className="mb-1"
            >
              <Input
                {...register("new_password", passwordRules())}
                placeholder="New Password"
                type="password"
                className="h-12 rounded-lg border-gray-200"
                borderWidth="1px"
                onChange={(e) => setNewPassword(e.target.value)}
              />
            </Field>

            {/* Password Strength Indicator */}
            {newPassword && (
              <PasswordStrengthIndicator strength={passwordStrength} />
            )}

            {/* Password Requirements */}
            {newPassword && <PasswordRequirements requirements={requirements} />}

            {/* Confirm Password Field */}
            <Field
              invalid={!!errors.confirm_password}
              errorText={errors.confirm_password?.message}
              className="mt-3 mb-1"
            >
              <Input
                {...register("confirm_password", confirmPasswordRules(getValues))}
                placeholder="Confirm Password"
                type="password"
                className="h-12 rounded-lg border-gray-200"
                borderWidth="1px"
                onChange={(e) => setConfirmPassword(e.target.value)}
              />
            </Field>

            {/* Password Match Indicator */}
            {confirmPassword && (
              <Text
                fontSize="sm"
                color={passwordsMatch ? "#10B981" : "#EF4444"}
                className="mt-1 mb-4"
              >
                {passwordsMatch
                  ? "✓ Passwords match"
                  : "✗ Passwords do not match"}
              </Text>
            )}

            {/* Reset Password Button */}
            <Button
              type="submit"
              loading={isSubmitting}
              variant="black"
              className="w-full h-12 rounded-lg mt-4"
            >
              Reset Password
            </Button>
          </Box>
        </FormSection>
      }
    />
  )
}