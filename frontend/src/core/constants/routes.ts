/**
 * Application route paths
 * Centralized route definitions for type-safety and maintainability
 */
export const ROUTES = {
  // Public routes
  LOGIN: '/login',
  REGISTER: '/register',

  // Protected routes
  HOME: '/',
  DASHBOARD: '/dashboard',
  PROJECTS: '/projects',
  SETTINGS: '/settings',
  PROFILE: '/profile',

  // Admin routes
  ADMIN: '/admin',
  ADMIN_USERS: '/admin/users',
} as const

/**
 * Route helper functions
 */
export const getProjectRoute = (id: string) => `/projects/${id}`
export const getUserProfileRoute = (id: string) => `/profile/${id}`

/**
 * Check if a route is public (doesn't require authentication)
 */
export const isPublicRoute = (path: string): boolean => {
  const publicRoutes = [ROUTES.LOGIN, ROUTES.REGISTER]
  return publicRoutes.includes(path)
}
