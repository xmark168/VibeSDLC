import { createFileRoute } from "@tanstack/react-router"
import { AdminLayout } from "@/components/admin/AdminLayout"
import { PersonasTab } from "@/components/admin/agents"
import { requireRole } from "@/utils/auth"

export const Route = createFileRoute("/admin/personas")({
  beforeLoad: async () => {
    await requireRole("admin")
  },
  component: PersonasAdminPage,
})

function PersonasAdminPage() {
  return (
    <AdminLayout>
      <div className="container mx-auto p-6">
        <PersonasTab />
      </div>
    </AdminLayout>
  )
}
