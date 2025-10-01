import { Box, Heading, Input, Text } from "@chakra-ui/react"
import {
  createFileRoute,
  Link as RouterLink,
  redirect,
} from "@tanstack/react-router"
import { useState } from "react"
import { type SubmitHandler, useForm } from "react-hook-form"

import type { UserRegister } from "@/client"
import { BrandingSection } from "@/components/ui/branding-section"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { DividerWithText } from "@/components/ui/divider-with-text"
import { Field } from "@/components/ui/field"
import { FormSection } from "@/components/ui/form-section"
import { GoogleButton } from "@/components/ui/google-button"
import { PasswordRequirements } from "@/components/ui/password-requirements"
import { PasswordStrengthIndicator } from "@/components/ui/password-strength-indicator"
import { SplitScreenLayout } from "@/components/ui/split-screen-layout"
import useAuth, { isLoggedIn } from "@/hooks/useAuth"
import {
  calculatePasswordStrength,
  confirmPasswordRules,
  emailPattern,
  getPasswordRequirements,
  passwordRules,
} from "@/utils"

interface UserRegisterForm extends UserRegister {
  confirm_password: string
}

function SignUp() {
  const { signUpMutation } = useAuth()
  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [agreedToTerms, setAgreedToTerms] = useState(false)

  const {
    register,
    handleSubmit,
    getValues,
    formState: { errors, isSubmitting },
  } = useForm<UserRegisterForm>({
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      email: "",
      full_name: "",
      password: "",
      confirm_password: "",
    },
  })

  const passwordStrength = calculatePasswordStrength(password)
  const requirements = getPasswordRequirements(password)
  const passwordsMatch = confirmPassword && password === confirmPassword

  const onSubmit: SubmitHandler<UserRegisterForm> = (data) => {
    if (!agreedToTerms) {
      return
    }
    signUpMutation.mutate(data)
  }

  return (
    <SplitScreenLayout
      leftSide={<BrandingSection />}
      rightSide={
        <FormSection>
          <Box as="form" onSubmit={handleSubmit(onSubmit)}>
            {/* Heading */}
            <Heading size="xl" className="mb-6" fontWeight="bold">
              Create Your Account
            </Heading>

            {/* Google OAuth */}
            <GoogleButton
              text="Sign up with Google"
              onClick={() => {
                console.log("Google OAuth not implemented yet")
              }}
              className="mb-4"
            />

            {/* Divider */}
            <DividerWithText text="Or Sign up with a registered account" />

            {/* Full Name Field */}
            <Field
              invalid={!!errors.full_name}
              errorText={errors.full_name?.message}
              className="mb-3"
            >
              <Input
                minLength={3}
                {...register("full_name", {
                  required: "Full name is required",
                })}
                placeholder="Full Name"
                type="text"
                className="h-12 rounded-lg border-gray-200"
                borderWidth="1px"
              />
            </Field>

            {/* Email Field */}
            <Field
              invalid={!!errors.email}
              errorText={errors.email?.message}
              className="mb-3"
            >
              <Input
                {...register("email", {
                  required: "Email is required",
                  pattern: emailPattern,
                })}
                placeholder="Email"
                type="email"
                className="h-12 rounded-lg border-gray-200"
                borderWidth="1px"
              />
            </Field>

            {/* Password Field */}
            <Field
              invalid={!!errors.password}
              errorText={errors.password?.message}
              className="mb-1"
            >
              <Input
                {...register("password", passwordRules())}
                placeholder="Password"
                type="password"
                className="h-12 rounded-lg border-gray-200"
                borderWidth="1px"
                onChange={(e) => setPassword(e.target.value)}
              />
            </Field>

            {/* Password Strength Indicator */}
            {password && (
              <PasswordStrengthIndicator strength={passwordStrength} />
            )}

            {/* Password Requirements */}
            {password && <PasswordRequirements requirements={requirements} />}

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
                className="mt-1 mb-3"
              >
                {passwordsMatch
                  ? "✓ Passwords match"
                  : "✗ Passwords do not match"}
              </Text>
            )}

            {/* Terms Checkbox */}
            <Box className="mt-4 mb-4">
              <Checkbox
                checked={agreedToTerms}
                onCheckedChange={(e) => setAgreedToTerms(!!e.checked)}
              >
                <Text fontSize="sm" color="#6B7280">
                  I agree to the{" "}
                  <Text
                    as="span"
                    color="black"
                    fontWeight="600"
                    textDecoration="underline"
                  >
                    Terms of Service
                  </Text>{" "}
                  and{" "}
                  <Text
                    as="span"
                    color="black"
                    fontWeight="600"
                    textDecoration="underline"
                  >
                    Privacy Policy
                  </Text>
                </Text>
              </Checkbox>
            </Box>

            {/* Create Account Button */}
            <Button
              type="submit"
              loading={isSubmitting}
              disabled={!agreedToTerms}
              variant="black"
              className="w-full h-12 rounded-lg mb-3"
            >
              Create Account
            </Button>

            {/* Login Link */}
            <Text className="text-center" fontSize="sm" color="#6B7280">
              Already have an account?{" "}
              <RouterLink to="/login">
                <Text
                  as="span"
                  color="black"
                  fontWeight="600"
                  textDecoration="underline"
                >
                  Sign in
                </Text>
              </RouterLink>
            </Text>
          </Box>
        </FormSection>
      }
    />
  )
}

export const Route = createFileRoute("/signup")({
  component: SignUp,
  beforeLoad: async () => {
    if (isLoggedIn()) {
      throw redirect({
        to: "/",
      })
    }
  },
})