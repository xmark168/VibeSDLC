import type { JSX } from "react"
import toast from "react-hot-toast"
import type { ApiError } from "./client"
import type { ToastMessages } from "@/types"

/**
 * Wraps an async operation with react-hot-toast loading states
 * @param promise - Promise or async function to execute
 * @param messages - Toast messages for loading, success, and error states
 * @returns Promise that resolves with the operation result
 *
 * @example
 * ```tsx
 * const result = await withToast(
 *   saveSettings(settings),
 *   {
 *     loading: 'Saving settings...',
 *     success: <b>Settings saved successfully!</b>,
 *     error: <b>Failed to save settings.</b>,
 *   }
 * );
 * ```
 */
export const withToast = async <T>(
  promise: Promise<T> | (() => Promise<T>),
  messages: ToastMessages,
): Promise<T> => {
  // If a function is passed, execute it to get the promise
  const actualPromise = typeof promise === "function" ? promise() : promise

  return toast.promise(actualPromise, {
    loading: messages.loading,
    success: messages.success,
    error: messages.error,
  })
}

export const emailPattern = {
  value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
  message: "Invalid email address",
}

export const namePattern = {
  value: /^[A-Za-z\s\u00C0-\u017F]{1,30}$/,
  message: "Invalid name",
}

export const passwordRules = (isRequired = true) => {
  const rules: any = {
    minLength: {
      value: 8,
      message: "Password must be at least 8 characters",
    },
  }

  if (isRequired) {
    rules.required = "Password is required"
  }

  return rules
}

export const confirmPasswordRules = (
  getValues: () => any,
  isRequired = true,
) => {
  const rules: any = {
    validate: (value: string) => {
      const password = getValues().password || getValues().new_password
      return value === password ? true : "The passwords do not match"
    },
  }

  if (isRequired) {
    rules.required = "Password confirmation is required"
  }

  return rules
}

export const handleError = (err: ApiError) => {
  const errDetail = (err.body as any)?.detail
  let errorMessage = errDetail || "Something went wrong."
  if (Array.isArray(errDetail) && errDetail.length > 0) {
    errorMessage = errDetail[0].msg
  }
  toast.error(errorMessage)
}

// Password validation utilities
export const hasMinLength = (password: string): boolean => {
  return password.length >= 8
}

export const hasUppercase = (password: string): boolean => {
  return /[A-Z]/.test(password)
}

export const hasLowercase = (password: string): boolean => {
  return /[a-z]/.test(password)
}

export const hasNumber = (password: string): boolean => {
  return /[0-9]/.test(password)
}

export const hasSpecialChar = (password: string): boolean => {
  return /[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]/.test(password)
}

export const calculatePasswordStrength = (password: string): number => {
  if (!password) return 0

  let strength = 0
  if (hasMinLength(password)) strength++
  if (hasUppercase(password)) strength++
  if (hasLowercase(password)) strength++
  if (hasNumber(password)) strength++
  if (hasSpecialChar(password)) strength++

  // Map 0-5 to 0-4 scale
  if (strength === 0) return 0
  if (strength <= 2) return 1
  if (strength === 3) return 2
  if (strength === 4) return 3
  return 4
}

export const getPasswordRequirements = (password: string) => {
  return [
    { label: "At least 8 characters", met: hasMinLength(password) },
    { label: "One uppercase letter", met: hasUppercase(password) },
    { label: "One lowercase letter", met: hasLowercase(password) },
    { label: "One number", met: hasNumber(password) },
    { label: "One special character", met: hasSpecialChar(password) },
  ]
}
