import { memo, useState } from 'react'
import { Eye, EyeOff } from 'lucide-react'
import { Input, type InputProps } from '@/shared/ui/input'
import { Button } from '@/shared/ui/button'
import { cn } from '@/core/utils/cn'

/**
 * Password input component with show/hide toggle
 * Extends the base Input component with password visibility toggle functionality
 *
 * @component
 * @example
 * ```tsx
 * <PasswordInput
 *   placeholder="Enter password"
 *   autoComplete="current-password"
 *   {...field}
 * />
 * ```
 */
export const PasswordInput = memo(({ className, ...props }: InputProps) => {
  const [showPassword, setShowPassword] = useState(false)

  return (
    <div className="relative">
      <Input
        type={showPassword ? 'text' : 'password'}
        className={cn('pr-10', className)}
        {...props}
      />
      {/* Toggle visibility button */}
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
        onClick={() => setShowPassword(!showPassword)}
        tabIndex={-1}
        aria-label={showPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
      >
        {showPassword ? (
          <EyeOff className="h-4 w-4 text-muted-foreground" />
        ) : (
          <Eye className="h-4 w-4 text-muted-foreground" />
        )}
        <span className="sr-only">
          {showPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
        </span>
      </Button>
    </div>
  )
})
