import { type ReactNode } from 'react'
import { Navigate, useLocation, type Location } from 'react-router-dom'
import { useAuth } from '@/core/contexts/AuthContext'
import { LoadingSpinner } from '@/shared/components/LoadingSpinner'

interface LocationState {
  from?: Location
}

interface RouteGuardProps {
  children: ReactNode
}

export const ProtectedRoute = ({ children }: RouteGuardProps) => {
  const { isAuthenticated, isLoading, user, accessToken } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return <LoadingSpinner />
  }

  if (!isAuthenticated) {
    // Redirect to login but save the attempted location
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return <>{children}</>
}

export const PublicRoute = ({ children }: RouteGuardProps) => {
  const { isAuthenticated, isLoading } = useAuth()
  const location = useLocation() as Location & { state: LocationState }

  if (isLoading) {
    return <LoadingSpinner />
  }

  if (isAuthenticated) {
    // Redirect to the page they tried to access or home
    const from = location.state?.from?.pathname || '/'
    return <Navigate to={from} replace />
  }

  return <>{children}</>
}
