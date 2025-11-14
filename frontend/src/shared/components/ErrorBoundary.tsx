import { Component, type ReactNode } from 'react'
import { AlertCircle, RefreshCw } from 'lucide-react'
import { Button } from '@/shared/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/shared/ui/card'

/**
 * Props for ErrorBoundary component
 */
interface ErrorBoundaryProps {
  /** Child components to render */
  children: ReactNode
  /** Optional custom fallback UI */
  fallback?: ReactNode
}

/**
 * State for ErrorBoundary component
 */
interface ErrorBoundaryState {
  /** Whether an error has been caught */
  hasError: boolean
  /** The error that was caught */
  error: Error | null
  /** Error stack trace */
  errorInfo: string | null
}

/**
 * Error Boundary component to catch and handle React errors gracefully
 * Prevents the entire app from crashing when an error occurs in a child component
 *
 * @component
 * @example Basic usage
 * ```tsx
 * <ErrorBoundary>
 *   <App />
 * </ErrorBoundary>
 * ```
 *
 * @example With custom fallback
 * ```tsx
 * <ErrorBoundary fallback={<CustomErrorPage />}>
 *   <App />
 * </ErrorBoundary>
 * ```
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    }
  }

  /**
   * Static method called when an error is thrown in a child component
   * Updates state to trigger fallback UI rendering
   */
  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return {
      hasError: true,
      error,
    }
  }

  /**
   * Lifecycle method called after an error is caught
   * Used for error logging and reporting
   */
  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    // Log error details to console in development
    if (process.env.NODE_ENV === 'development') {
      console.error('Error Boundary caught an error:', error)
      console.error('Error Info:', errorInfo)
    }

    // Update state with error info
    this.setState({
      errorInfo: errorInfo.componentStack || null,
    })

    // TODO: Send error to logging service (e.g., Sentry, LogRocket)
    // logErrorToService(error, errorInfo)
  }

  /**
   * Reset error boundary state and retry rendering
   */
  handleReset = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    })
  }

  /**
   * Reload the page to recover from error
   */
  handleReload = (): void => {
    window.location.reload()
  }

  render(): ReactNode {
    const { hasError, error, errorInfo } = this.state
    const { children, fallback } = this.props

    // If an error occurred, render fallback UI
    if (hasError) {
      // Use custom fallback if provided
      if (fallback) {
        return fallback
      }

      // Default fallback UI
      return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900 p-4">
          <Card className="w-full max-w-2xl shadow-lg">
            <CardHeader>
              <div className="flex items-center gap-2">
                <AlertCircle className="h-6 w-6 text-destructive" />
                <CardTitle className="text-2xl">Đã xảy ra lỗi</CardTitle>
              </div>
              <CardDescription>
                Ứng dụng gặp phải một lỗi không mong muốn. Chúng tôi rất xin lỗi về sự bất tiện này.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Error message */}
              {error && (
                <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-md">
                  <p className="font-mono text-sm text-destructive">{error.message}</p>
                </div>
              )}

              {/* Error stack (development only) */}
              {process.env.NODE_ENV === 'development' && errorInfo && (
                <details className="p-4 bg-muted rounded-md">
                  <summary className="cursor-pointer font-medium text-sm mb-2">
                    Chi tiết lỗi (Development Only)
                  </summary>
                  <pre className="text-xs overflow-auto max-h-64 whitespace-pre-wrap">
                    {errorInfo}
                  </pre>
                </details>
              )}

              {/* Action buttons */}
              <div className="flex gap-2 flex-wrap">
                <Button onClick={this.handleReset} variant="default">
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Thử lại
                </Button>
                <Button onClick={this.handleReload} variant="outline">
                  Tải lại trang
                </Button>
                <Button
                  onClick={() => (window.location.href = '/')}
                  variant="ghost"
                >
                  Về trang chủ
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )
    }

    // No error, render children normally
    return children
  }
}
