import { createFileRoute } from "@tanstack/react-router"

export const Route = createFileRoute("/_admin/admin")({
  component: RouteComponent,
})

function RouteComponent() {
  return <div>Hello "/_layout/admin"!</div>
}
