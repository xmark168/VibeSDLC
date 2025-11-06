import { createFileRoute } from "@tanstack/react-router"
import { requireRole } from "@/utils/auth"

export const Route = createFileRoute("/_admin/admin")({
  beforeLoad: async () => {
    await requireRole('admin')
  },
  component: RouteComponent,
})

function RouteComponent() {
  return (
    <div className="container mx-auto p-6">
      <h1 className="text-3xl font-bold mb-4">Admin Dashboard</h1>
      <p className="text-gray-600">Welcome to the admin panel. This area is restricted to administrators only.</p>
    </div>
  )
}
