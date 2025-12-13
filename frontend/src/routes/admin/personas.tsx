import { createFileRoute } from "@tanstack/react-router"
import { requireRole } from "@/utils/auth"
import { PersonasTab } from "@/components/admin/agents"
import { AdminLayout } from "@/components/admin/AdminLayout"

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
