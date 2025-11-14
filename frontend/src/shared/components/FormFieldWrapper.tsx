import { type ComponentType, type InputHTMLAttributes } from 'react'
import { type Control, type FieldPath, type FieldValues } from 'react-hook-form'
import {
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/shared/ui/form'
import { Input } from '@/shared/ui/input'
import { PasswordInput } from '@/features/auth/components/PasswordInput'

/**
 * Generic form field wrapper component for React Hook Form
 * Eliminates duplication by providing a reusable form field structure
 *
 * @template TFieldValues - Form values type from react-hook-form
 * @template TName - Field name type (key of TFieldValues)
 *
 * @example
 * ```tsx
 * <FormFieldWrapper
 *   control={form.control}
 *   name="email"
 *   label="Email"
 *   type="email"
 *   placeholder="Enter your email"
 *   autoComplete="email"
 * />
 * ```
 *
 * @example Password field
 * ```tsx
 * <FormFieldWrapper
 *   control={form.control}
 *   name="password"
 *   label="Password"
 *   component={PasswordInput}
 *   placeholder="Enter password"
 *   autoComplete="current-password"
 * />
 * ```
 */
interface FormFieldWrapperProps<
  TFieldValues extends FieldValues = FieldValues,
  TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>
> {
  /** React Hook Form control object */
  control: Control<TFieldValues>
  /** Field name (must match a key in your form schema) */
  name: TName
  /** Label text displayed above the input */
  label: string
  /** Placeholder text for the input */
  placeholder?: string
  /** Input type (text, email, etc.) - only used with default Input component */
  type?: string
  /** HTML autocomplete attribute */
  autoComplete?: string
  /** Whether the input is disabled */
  disabled?: boolean
  /** If true, displays "(Tùy chọn)" next to the label */
  optional?: boolean
  /** Custom input component (defaults to Input, can be PasswordInput or other) */
  component?: ComponentType<InputHTMLAttributes<HTMLInputElement>>
}

export const FormFieldWrapper = <
  TFieldValues extends FieldValues = FieldValues,
  TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>
>({
  control,
  name,
  label,
  placeholder,
  type = 'text',
  autoComplete,
  disabled,
  optional = false,
  component: Component = Input,
}: FormFieldWrapperProps<TFieldValues, TName>) => {
  return (
    <FormField
      control={control}
      name={name}
      render={({ field }) => (
        <FormItem>
          <FormLabel>
            {label}
            {optional && <span className="text-muted-foreground"> (Tùy chọn)</span>}
          </FormLabel>
          <FormControl>
            <Component
              type={type}
              placeholder={placeholder}
              autoComplete={autoComplete}
              disabled={disabled}
              {...field}
            />
          </FormControl>
          <FormMessage />
        </FormItem>
      )}
    />
  )
}
