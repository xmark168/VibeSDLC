import { createFileRoute, Outlet, redirect } from '@tanstack/react-router'
import { isLoggedIn } from '@/hooks/useAuth'

export const Route = createFileRoute('/_layout')({
  beforeLoad: () => {
    if (!isLoggedIn()) {
      throw redirect({ to: '/login' })
    }
  },
  component: LayoutRoot,
})

function LayoutRoot() {
  return (
    <div style={{ fontFamily: "IBM Plex Sans" }}>
      <Outlet />
    </div>
  )
}
