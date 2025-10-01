import { Box, Heading, Input, Text } from "@chakra-ui/react"
import {
  createFileRoute,
  Link as RouterLink,
  redirect,
} from "@tanstack/react-router"
import { useState } from "react"
import { type SubmitHandler, useForm } from "react-hook-form"

import type { Body_login_login_access_token as AccessToken } from "@/client"
import { BrandingSection } from "@/components/ui/branding-section"
import { Button } from "@/components/ui/button"
import { DividerWithText } from "@/components/ui/divider-with-text"
import { Field } from "@/components/ui/field"
import { FormSection } from "@/components/ui/form-section"
import { GoogleButton } from "@/components/ui/google-button"
import { SplitScreenLayout } from "@/components/ui/split-screen-layout"
import useAuth, { isLoggedIn } from "@/hooks/useAuth"
import { emailPattern, passwordRules } from "../utils"

export const Route = createFileRoute("/login")({
  component: Login,
  beforeLoad: async () => {
    if (isLoggedIn()) {
      throw redirect({
        to: "/",
      })
    }
  },
})

function Login() {
  const { loginMutation, error, resetError } = useAuth()
  const [loginError, setLoginError] = useState(false)
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<AccessToken>({
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      username: "",
      password: "",
    },
  })

  const onSubmit: SubmitHandler<AccessToken> = async (data) => {
    if (isSubmitting) return

    resetError()
    setLoginError(false)

    try {
      await loginMutation.mutateAsync(data)
    } catch {
      setLoginError(true)
      setTimeout(() => setLoginError(false), 500)
    }
  }

  return (
    <SplitScreenLayout
      leftSide={<BrandingSection />}
      rightSide={
        <FormSection>
          <Box
            as="form"
            onSubmit={handleSubmit(onSubmit)}
            className={loginError ? "shake-animation" : ""}
          >
            {/* Heading */}
            <Heading size="xl" className="mb-6" fontWeight="bold">
              Welcome Back
            </Heading>

            {/* Google OAuth */}
            <GoogleButton
              text="Sign in with Google"
              onClick={() => {
                console.log("Google OAuth not implemented yet")
              }}
              className="mb-4"
            />

            {/* Divider */}
            <DividerWithText text="Or Sign in with a registered account" />

            {/* Email Field */}
            <Field
              invalid={!!errors.username}
              errorText={errors.username?.message || !!error}
              className="mb-4"
            >
              <Input
                {...register("username", {
                  required: "Email is required",
                  pattern: emailPattern,
                })}
                placeholder="email"
                type="email"
                className="h-12 rounded-lg border-gray-200"
                borderWidth="1px"
              />
            </Field>

            {/* Password Field */}
            <Field
              invalid={!!errors.password}
              errorText={errors.password?.message}
              className="mb-6"
            >
              <Input
                {...register("password", passwordRules())}
                placeholder="password"
                type="password"
                className="h-12 rounded-lg border-gray-200"
                borderWidth="1px"
              />
            </Field>

            {/* Sign Up Link */}
            <Text className="mb-4" fontSize="sm" color="#6B7280">
              Don't have an account?{" "}
              <RouterLink to="/signup">
                <Text
                  as="span"
                  color="black"
                  fontWeight="600"
                  textDecoration="underline"
                >
                  Create your account
                </Text>
              </RouterLink>
            </Text>

            {/* Sign In Button */}
            <Button
              type="submit"
              loading={isSubmitting}
              variant="black"
              className="w-full h-12 rounded-lg mb-3"
            >
              Sign in
            </Button>

            {/* Forgot Password */}
            <RouterLink to="/recover-password">
              <Text
                className="text-center"
                fontSize="sm"
                color="#6B7280"
                textDecoration="underline"
              >
                Forgot password?
              </Text>
            </RouterLink>
          </Box>
        </FormSection>
      }
    />
  )
}