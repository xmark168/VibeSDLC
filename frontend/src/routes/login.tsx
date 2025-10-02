import React from 'react'
import { createFileRoute, redirect } from "@tanstack/react-router"
import { Button } from '@/components/ui/button'
import { isLoggedIn } from '@/hooks/useAuth'


export const Route = createFileRoute("/login")({
  component: Login,
  beforeLoad: async () => {
    if (isLoggedIn()) {
      throw redirect({
        to: "/",
      })
    }
  },
})
export default function Login() {
  return (
    <div className="flex min-h-svh flex-col items-center justify-center">
      <Button>Click me</Button>
    </div>
  )
}
