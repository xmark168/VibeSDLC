import { createFileRoute, Outlet } from "@tanstack/react-router"
import { Header } from "@/components/landing/header"
import { Footer } from "@/components/ui/footer"

export const Route = createFileRoute("/_public")({
  component: PublicLayout,
})

function PublicLayout() {
  return (
    <div className="min-h-screen bg-background relative overflow-hidden">
      <div className="relative z-10">
        <main className="max-w-[1320px] mx-auto relative">
          <Header />
          <Outlet />
        </main>
        <Footer />
      </div>
    </div>
  )
}
