import { createFileRoute, Outlet } from "@tanstack/react-router"
import { requireAuth } from "@/utils/auth"

export const Route = createFileRoute("/_layout")({
  beforeLoad: async () => {
    await requireAuth()
  },
  component: LayoutRoot,
})

function LayoutRoot() {
  return (
    <div style={{ fontFamily: "IBM Plex Sans" }}  >
      <Outlet />
    </div>
  )
}
