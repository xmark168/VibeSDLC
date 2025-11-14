import { type ReactNode } from 'react'
import { Alert, AlertDescription } from '@/shared/ui/alert'
import { AlertCircle, CheckCircle2 } from 'lucide-react'
import { cn } from '@/core/utils/cn'

/**
 * Status alert component for displaying error and success messages
 * Provides consistent styling and icons for different alert types
 *
 * @example Error alert
 * ```tsx
 * <StatusAlert variant="error" message="Login failed. Please try again." />
 * ```
 *
 * @example Success alert
 * ```tsx
 * <StatusAlert
 *   variant="success"
 *   message="Registration successful! Redirecting..."
 * />
 * ```
 *
 * @example With custom children
 * ```tsx
 * <StatusAlert variant="error">
 *   <p>An error occurred.</p>
 *   <button>Retry</button>
 * </StatusAlert>
 * ```
 */
export interface StatusAlertProps {
  /** Type of alert - error or success */
  variant: 'error' | 'success'
  /** Alert message (can use message prop or children) */
  message?: string
  /** Custom content for the alert */
  children?: ReactNode
  /** Additional className for customization */
  className?: string
}

export const StatusAlert = ({
  variant,
  message,
  children,
  className,
}: StatusAlertProps) => {
  // Icon and styling based on variant
  const Icon = variant === 'error' ? AlertCircle : CheckCircle2

  const variantStyles = {
    error: '',
    success: 'border-green-500 bg-green-50 text-green-900',
  }

  const iconStyles = {
    error: '',
    success: 'text-green-600',
  }

  return (
    <Alert
      variant={variant === 'error' ? 'destructive' : undefined}
      className={cn(variantStyles[variant], className)}
    >
      <Icon className={cn('h-4 w-4', iconStyles[variant])} />
      <AlertDescription>{children || message}</AlertDescription>
    </Alert>
  )
}
