import { useState, useCallback } from 'react'
import { type AxiosError } from 'axios'
import type { APIError } from '@/shared/types/api'

/**
 * Custom hook for handling API requests with loading and error states
 * Eliminates duplicate error handling and loading state management code
 *
 * @template T - Type of the API response data
 *
 * @example Basic usage
 * ```tsx
 * const { error, isLoading, execute } = useApiRequest()
 *
 * const handleSubmit = async (data) => {
 *   await execute(
 *     () => authAPI.login(data.email, data.password),
 *     (response) => {
 *       // Success callback
 *     }
 *   )
 * }
 * ```
 *
 * @example With custom error message
 * ```tsx
 * const { error, isLoading, execute } = useApiRequest()
 *
 * await execute(
 *   () => userAPI.updateProfile(data),
 *   (response) => toast.success('Profile updated!'),
 *   'Failed to update profile. Please try again.'
 * )
 * ```
 *
 * @returns Object containing error state, loading state, and execute function
 */
export const useApiRequest = <T = unknown>() => {
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  /**
   * Execute an API call with automatic error handling and loading states
   *
   * @param apiCall - Function that returns a Promise (the API call)
   * @param onSuccess - Optional callback to run on successful response
   * @param errorMessage - Optional custom error message (defaults to generic message)
   * @returns Promise that resolves with the API response data
   * @throws Re-throws the error after handling, allowing caller to catch if needed
   */
  const execute = useCallback(
    async (
      apiCall: () => Promise<T>,
      onSuccess?: (data: T) => void,
      errorMessage = 'Có lỗi xảy ra. Vui lòng thử lại.'
    ): Promise<T> => {
      // Clear previous error
      setError('')
      setIsLoading(true)

      try {
        const data = await apiCall()
        // Call success callback if provided
        onSuccess?.(data)
        return data
      } catch (err) {
        // Extract error message from axios error or use default
        const axiosError = err as AxiosError<APIError>
        const message = axiosError.response?.data?.detail || errorMessage
        setError(message)
        // Re-throw to allow caller to handle if needed
        throw err
      } finally {
        setIsLoading(false)
      }
    },
    []
  )

  return {
    /** Current error message (empty string if no error) */
    error,
    /** Whether an API request is currently in progress */
    isLoading,
    /** Function to execute an API request */
    execute,
    /** Function to manually set error message */
    setError,
  }
}
