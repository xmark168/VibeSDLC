import { useState } from 'react'
import { useForm, type SubmitHandler } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Link, useNavigate, useLocation, type Location } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { loginSchema, type LoginFormValues } from '@/features/auth/validations/auth'
import { useAuth } from '@/core/contexts/AuthContext'
import { authAPI } from '@/features/auth/api/auth'
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

interface LocationState {
  from?: Location
}

export const LoginPage = () => {
  const { t } = useTranslation('auth')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation() as Location & { state: LocationState }

  const form = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      identifier: '',
      password: '',
    },
  })

  const onSubmit: SubmitHandler<LoginFormValues> = async (data) => {
    setError('')
    setIsLoading(true)

    try {
      const response = await authAPI.login(data.identifier, data.password)
      await login(response.access_token) // Refresh token now in httpOnly cookie

      // Redirect to the page they tried to access or home
      const from = location.state?.from?.pathname || '/'
      navigate(from, { replace: true })
    } catch (err) {
      const axiosError = err as AxiosError<APIError>
      setError(getErrorMessage(axiosError, t('login.error')))
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <AuthLayout
      title={t('login.title')}
      description={t('login.description')}
      footer={
        <p>
          {t('login.noAccount')}{' '}
          <Link to="/register" className="text-primary hover:underline font-medium">
            {t('login.registerLink')}
          </Link>
        </p>
      }
    >
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          {error && <StatusAlert variant="error" message={error} />}

          <FormFieldWrapper
            control={form.control}
            name="identifier"
            label={t('login.identifier')}
            placeholder={t('login.identifierPlaceholder')}
            autoComplete="username"
            disabled={isLoading}
          />

          <FormFieldWrapper
            control={form.control}
            name="password"
            label={t('login.password')}
            component={PasswordInput}
            placeholder={t('login.passwordPlaceholder')}
            autoComplete="current-password"
            disabled={isLoading}
          />

          <Button
            type="submit"
            className="w-full"
            disabled={isLoading}
          >
            {isLoading ? t('login.submitting') : t('login.submit')}
          </Button>
        </form>
      </Form>
    </AuthLayout>
  )
}
