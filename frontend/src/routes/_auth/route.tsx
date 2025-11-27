import { createFileRoute, Outlet } from "@tanstack/react-router"
import { motion } from "framer-motion"
import { CheckCircle, ClipboardList, Code, Workflow } from "lucide-react"
import { requireNoAuth } from "@/utils/auth"

export const Route = createFileRoute("/_auth")({
  beforeLoad: async () => {
    await requireNoAuth()
  },
  component: RouteComponent,
})

function RouteComponent() {
  return (
    <div className="min-h-screen antialiased flex items-stretch justify-center">
      {/* Left Side - Animated Agent Circle */}
      <div
        className="relative flex flex-1 items-center justify-center overflow-hidden p-8 lg:p-16"
      >
      </div>

      {/* Right Side - Login Form */}
      <Outlet />
    </div>
  )
}
