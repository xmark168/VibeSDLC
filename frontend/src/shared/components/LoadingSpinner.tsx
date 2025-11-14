import { type HTMLAttributes } from 'react'
import { cn } from '@/core/utils/cn'

/**
 * Loading spinner component with customizable size and layout
 * Used across the app for loading states and async operations
 *
 * @example Default (fullscreen)
 * ```tsx
 * <LoadingSpinner />
 * ```
 *
 * @example Inline spinner
 * ```tsx
 * <LoadingSpinner fullScreen={false} size="sm" />
 * ```
 *
 * @example Custom className
 * ```tsx
 * <LoadingSpinner className="my-4" />
 * ```
 */
export interface LoadingSpinnerProps extends HTMLAttributes<HTMLDivElement> {
  /** Size of the spinner */
  size?: 'sm' | 'md' | 'lg'
  /** If true, centers the spinner in a full-screen container */
  fullScreen?: boolean
}

export const LoadingSpinner = ({
  size = 'md',
  fullScreen = true,
  className,
  ...props
}: LoadingSpinnerProps) => {
  // Size classes for the spinner
  const sizeClasses = {
    sm: 'h-6 w-6',
    md: 'h-12 w-12',
    lg: 'h-16 w-16',
  }

  // The spinner element
  const spinner = (
    <div
      className={cn(
        'animate-spin rounded-full border-b-2 border-primary',
        sizeClasses[size],
        !fullScreen && className
      )}
      role="status"
      aria-label="Loading"
      {...(!fullScreen && props)}
    />
  )

  // If fullScreen is true, wrap in a centered container
  if (fullScreen) {
    return (
      <div
        className={cn('flex items-center justify-center min-h-screen', className)}
        {...props}
      >
        {spinner}
      </div>
    )
  }

  // Otherwise, return just the spinner
  return spinner
}
