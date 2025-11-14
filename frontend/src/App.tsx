import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from '@/core/contexts/AuthContext'
import { ProtectedRoute, PublicRoute } from '@/shared/components/RouteGuards'
import { LoadingSpinner } from '@/shared/components/LoadingSpinner'
import { AppLayout } from '@/shared/layouts/AppLayout'
import { Toaster } from 'sonner'
import { ROUTES } from '@/core/constants/routes'

/**
 * Lazy-loaded route components for code splitting
 * This improves initial page load performance by splitting the bundle
 */
const LoginPage = lazy(() =>
  import('@/features/auth/pages/LoginPage').then((module) => ({
    default: module.LoginPage,
  }))
)
const RegisterPage = lazy(() =>
  import('@/features/auth/pages/RegisterPage').then((module) => ({
    default: module.RegisterPage,
  }))
)
const DashboardPage = lazy(() =>
  import('@/pages/DashboardPage').then((module) => ({
    default: module.DashboardPage,
  }))
)
const ProjectsPage = lazy(() =>
  import('@/features/projects/pages/ProjectsPage').then((module) => ({
    default: module.ProjectsPage,
  }))
)
const ProjectDetailPage = lazy(() =>
  import('@/features/projects/pages/ProjectDetailPage').then((module) => ({
    default: module.ProjectDetailPage,
  }))
)

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Suspense fallback={<LoadingSpinner />}>
          <Routes>
            {/* Public routes */}
            <Route
              path={ROUTES.LOGIN}
              element={
                <PublicRoute>
                  <LoginPage />
                </PublicRoute>
              }
            />
            <Route
              path={ROUTES.REGISTER}
              element={
                <PublicRoute>
                  <RegisterPage />
                </PublicRoute>
              }
            />

            {/* Protected routes with AppLayout */}
            <Route
              path={ROUTES.HOME}
              element={
                <ProtectedRoute>
                  <AppLayout>
                    <DashboardPage />
                  </AppLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path={ROUTES.DASHBOARD}
              element={
                <ProtectedRoute>
                  <AppLayout>
                    <DashboardPage />
                  </AppLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path={ROUTES.PROJECTS}
              element={
                <ProtectedRoute>
                  <AppLayout>
                    <ProjectsPage />
                  </AppLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/projects/:id"
              element={
                <ProtectedRoute>
                  <ProjectDetailPage />
                </ProtectedRoute>
              }
            />

            {/* Fallback */}
            <Route path="*" element={<Navigate to={ROUTES.HOME} replace />} />
          </Routes>
        </Suspense>
      </BrowserRouter>

      <Toaster position="top-right" richColors />
    </AuthProvider>
  )
}

export default App
