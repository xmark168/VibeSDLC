import { createFileRoute, Outlet } from '@tanstack/react-router'

export const Route = createFileRoute('/_layout')({
  component: LayoutRoot,
})

function LayoutRoot() {
  return (
    <div style={{ fontFamily: "IBM Plex Sans" }}>
      <Outlet />
    </div>
  )
}
