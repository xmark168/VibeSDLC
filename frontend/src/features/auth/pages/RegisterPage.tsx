import { useState } from 'react'
import { useForm, type SubmitHandler } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { registerSchema, type RegisterFormValues } from '@/features/auth/validations/auth'
import { authAPI } from '@/features/auth/api/auth'
import { useAuth } from '@/core/contexts/AuthContext'
import { AuthLayout } from '../components/AuthLayout'
import { PasswordInput } from '../components/PasswordInput'
import { Button } from '@/shared/ui/button'
import { Form } from '@/shared/ui/form'
import { FormFieldWrapper } from '@/shared/components/FormFieldWrapper'
import { StatusAlert } from '@/shared/components/StatusAlert'
import { type AxiosError } from 'axios'
import type { APIError } from '@/shared/types/api'
import { ROUTES } from '@/core/constants/routes'
import { getErrorMessage } from '@/core/utils/formatError'

export const RegisterPage = () => {
  const { t } = useTranslation('auth')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const form = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      username: '',
      email: '',
      password: '',
      confirmPassword: '',
      fullName: '',
    },
  })

  const onSubmit: SubmitHandler<RegisterFormValues> = async (data) => {
    setError('')
    setSuccess(false)
    setIsLoading(true)

    try {
      const response = await authAPI.register(data)

      // Extract tokens from nested response
      const { tokens } = response

      // Auto-login user with returned access token (refresh token in httpOnly cookie)
      await login(tokens.access_token)

      setSuccess(true)

      // Redirect to home after brief success message
      setTimeout(() => {
        navigate(ROUTES.HOME)
      }, 1500)
    } catch (err) {
      const axiosError = err as AxiosError<APIError>
      setError(getErrorMessage(axiosError, t('register.error')))
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <AuthLayout
      title={t('register.title')}
      description={t('register.description')}
      footer={
        <p>
          {t('register.hasAccount')}{' '}
          <Link to="/login" className="text-primary hover:underline font-medium">
            {t('register.loginLink')}
          </Link>
        </p>
      }
    >
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          {error && <StatusAlert variant="error" message={error} />}

          {success && (
            <StatusAlert
              variant="success"
              message={t('register.success')}
            />
          )}

          <FormFieldWrapper
            control={form.control}
            name="username"
            label={t('register.username')}
            placeholder={t('register.usernamePlaceholder')}
            autoComplete="username"
            disabled={isLoading}
          />

          <FormFieldWrapper
            control={form.control}
            name="email"
            label={t('register.email')}
            type="email"
            placeholder={t('register.emailPlaceholder')}
            autoComplete="email"
            disabled={isLoading}
          />

          <FormFieldWrapper
            control={form.control}
            name="fullName"
            label={t('register.fullName')}
            placeholder={t('register.fullNamePlaceholder')}
            autoComplete="name"
            disabled={isLoading}
            optional
          />

          <FormFieldWrapper
            control={form.control}
            name="password"
            label={t('register.password')}
            component={PasswordInput}
            placeholder={t('register.passwordPlaceholder')}
            autoComplete="new-password"
            disabled={isLoading}
          />

          <FormFieldWrapper
            control={form.control}
            name="confirmPassword"
            label={t('register.confirmPassword')}
            component={PasswordInput}
            placeholder={t('register.confirmPasswordPlaceholder')}
            autoComplete="new-password"
            disabled={isLoading}
          />

          <Button
            type="submit"
            className="w-full"
            disabled={isLoading || success}
          >
            {isLoading ? t('register.submitting') : t('register.submit')}
          </Button>
        </form>
      </Form>
    </AuthLayout>
  )
}
