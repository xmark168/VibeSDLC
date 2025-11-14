import { memo, type ReactNode } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/shared/ui/card'

/**
 * Layout wrapper for authentication pages (login, register)
 * Provides consistent styling and branding across auth flows
 *
 * @component
 * @example
 * ```tsx
 * <AuthLayout
 *   title="Login"
 *   description="Enter your credentials"
 *   footer={<p>Don't have an account? <Link to="/register">Sign up</Link></p>}
 * >
 *   <LoginForm />
 * </AuthLayout>
 * ```
 */
interface AuthLayoutProps {
  /** Page title displayed in the card header */
  title: string
  /** Optional description text below the title */
  description?: string
  /** Form or content to display in the card body */
  children: ReactNode
  /** Optional footer content (e.g., links to other auth pages) */
  footer?: ReactNode
}

export const AuthLayout = memo(({
  title,
  description,
  children,
  footer
}: AuthLayoutProps) => {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900 p-4">
      <div className="w-full max-w-md">
        {/* App branding */}
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-primary mb-2">VibeSDLC</h1>
          <p className="text-sm text-muted-foreground">Kanban-based Software Development Lifecycle Management</p>
        </div>

        {/* Auth card */}
        <Card className="shadow-lg">
          <CardHeader className="space-y-1">
            <CardTitle className="text-2xl font-bold text-center">
              {title}
            </CardTitle>
            {description && (
              <CardDescription className="text-center">
                {description}
              </CardDescription>
            )}
          </CardHeader>
          <CardContent>
            {children}
          </CardContent>
        </Card>

        {/* Footer (e.g., register link) */}
        {footer && (
          <div className="mt-4 text-center text-sm text-muted-foreground">
            {footer}
          </div>
        )}
      </div>
    </div>
  )
})
