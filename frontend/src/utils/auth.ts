import { redirect } from '@tanstack/react-router'
import { useAppStore } from '@/stores/auth-store'
import type { Role } from '@/client'

/**
 * Check if user is logged in by checking access token
 */
export const isLoggedIn = (): boolean => {
  return localStorage.getItem('access_token') !== null
}

/**
 * Route protection for authenticated routes
 * Use in beforeLoad hook for protected routes
 */
export const requireAuth = async () => {
  if (!isLoggedIn()) {
    throw redirect({
      to: '/login',
      search: {
        redirect: window.location.pathname
      }
    })
  }

  // Wait for user data to load
  const store = useAppStore.getState()
  if (!store.user && !store.isLoading) {
    throw redirect({
      to: '/login',
      search: {
        redirect: window.location.pathname
      }
    })
  }
}

/**
 * Route protection for role-specific routes
 * Use in beforeLoad hook for role-protected routes
 */
export const requireRole = async (requiredRole: Role) => {
  if (!isLoggedIn()) {
    throw redirect({
      to: '/login',
      search: {
        redirect: window.location.pathname
      }
    })
  }

  // Wait for user data to be available (max 3 seconds)
  const maxWaitTime = 3000
  const checkInterval = 50
  let waited = 0

  while (waited < maxWaitTime) {
    const store = useAppStore.getState()
    
    // If we have user data, break out of loop
    if (store.user) {
      break
    }
    
    // If not loading and no user, authentication failed
    if (!store.isLoading && !store.user) {
      throw redirect({
        to: '/login',
        search: {
          redirect: window.location.pathname
        }
      })
    }
    
    // Wait and check again
    await new Promise(resolve => setTimeout(resolve, checkInterval))
    waited += checkInterval
  }

  const user = useAppStore.getState().user

  if (!user) {
    throw redirect({
      to: '/login',
      search: {
        redirect: window.location.pathname
      }
    })
  }

  // Check if user has the required role
  // Admin can access all pages, so skip check if user is admin
  if (user.role === 'admin') {
    return // Admin has access to everything
  }

  if (user.role !== requiredRole) {
    // Redirect non-admin users to their appropriate page
    throw redirect({ to: '/projects' })
  }
}

/**
 * Route protection for auth pages (login, signup, etc.)
 * Prevents authenticated users from accessing auth pages
 */
export const requireNoAuth = async () => {
  if (isLoggedIn()) {
    const store = useAppStore.getState()
    const user = store.user

    // Redirect based on user role
    if (user?.role === 'admin') {
      throw redirect({ to: '/admin' })
    } else {
      throw redirect({ to: '/projects' })
    }
  }
}

/**
 * Get redirect path based on user role
 */
export const getRedirectPathByRole = (role: Role | undefined): string => {
  switch (role) {
    case 'admin':
      return '/admin'
    case 'user':
      return '/projects'
    default:
      return '/login'
  }
}

/**
 * Check if current user has admin role
 */
export const isAdmin = (): boolean => {
  const store = useAppStore.getState()
  return store.user?.role === 'admin'
}

/**
 * Check if current user has user role
 */
export const isUser = (): boolean => {
  const store = useAppStore.getState()
  return store.user?.role === 'user'
}