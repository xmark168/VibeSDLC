import type { APIError, ValidationError } from '@/shared/types/api'

/**
 * Formats API error response into a user-friendly error message
 * Handles both simple string errors and validation error arrays from FastAPI
 *
 * @param detail - Error detail from API response (string or ValidationError[])
 * @param fallbackMessage - Default message if error cannot be parsed
 * @returns Formatted error message string
 *
 * @example
 * // Simple error
 * formatErrorMessage("Invalid credentials")
 * // => "Invalid credentials"
 *
 * @example
 * // Validation errors
 * formatErrorMessage([
 *   { type: "string_type", loc: ["body", "email"], msg: "Invalid email", input: null }
 * ])
 * // => "email: Invalid email"
 */
export const formatErrorMessage = (
  detail: string | ValidationError[] | undefined,
  fallbackMessage = 'An error occurred'
): string => {
  // If no detail, return fallback
  if (!detail) {
    return fallbackMessage
  }

  // If detail is a string, return it directly
  if (typeof detail === 'string') {
    return detail
  }

  // If detail is an array of validation errors, format them
  if (Array.isArray(detail) && detail.length > 0) {
    return detail
      .map((error) => {
        // Extract field name from location path (e.g., ["body", "email"] -> "email")
        const field = error.loc[error.loc.length - 1]
        return `${field}: ${error.msg}`
      })
      .join(', ')
  }

  // Fallback if detail is neither string nor valid array
  return fallbackMessage
}

/**
 * Extracts error message from Axios error response
 * Convenience wrapper around formatErrorMessage for use with AxiosError
 *
 * @param error - Axios error object
 * @param fallbackMessage - Default message if error cannot be parsed
 * @returns Formatted error message string
 *
 * @example
 * try {
 *   await authAPI.login(email, password)
 * } catch (err) {
 *   const message = getErrorMessage(err as AxiosError<APIError>, 'Login failed')
 *   setError(message)
 * }
 */
export const getErrorMessage = (
  error: { response?: { data?: APIError } },
  fallbackMessage = 'An error occurred'
): string => {
  return formatErrorMessage(error.response?.data?.detail, fallbackMessage)
}
