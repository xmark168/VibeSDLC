import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/recover-password')({
  component: RouteComponent,
})

function RouteComponent() {
  return <div>Hello "/recover-password"!</div>
}
