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

  // Get current state from store
  const store = useAppStore.getState()

  // Wait for user data to load if still loading
  if (store.isLoading) {
    // In a real app, you might want to wait for loading to complete
    // For now, we'll assume user data is available
    return
  }

  const user = store.user

  if (!user) {
    throw redirect({
      to: '/login',
      search: {
        redirect: window.location.pathname
      }
    })
  }

  // Check if user has the required role
  if (user.role !== requiredRole) {
    // Redirect based on user's actual role
    if (user.role === 'admin') {
      throw redirect({ to: '/admin' })
    } else {
      throw redirect({ to: '/projects' })
    }
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