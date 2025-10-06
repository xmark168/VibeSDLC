
import { createFileRoute, Outlet, redirect } from "@tanstack/react-router"


import { isLoggedIn } from "@/hooks/useAuth"

function Layout() {
  return (
    <div>
      <Outlet />
    </div>
  )
}

export const Route = createFileRoute("/_layout")({
  component: Layout,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({
        to: "/login",
      })
    }
  },
})
