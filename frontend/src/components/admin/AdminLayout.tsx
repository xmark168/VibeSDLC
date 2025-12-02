import { HeaderProject } from "@/components/projects/header"
import { useAppStore } from "@/stores/auth-store"

interface AdminLayoutProps {
  children: React.ReactNode
}

export function AdminLayout({ children }: AdminLayoutProps) {
  const user = useAppStore((state) => state.user)

  return (
    <div className="min-h-screen bg-background">
      <HeaderProject
        userName={user?.full_name || "Admin"}
        userEmail={user?.email || "admin@example.com"}
      />
      <main>{children}</main>
    </div>
  )
}
