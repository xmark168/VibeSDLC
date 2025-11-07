import { createFileRoute } from "@tanstack/react-router"
import { ResetPasswordForm } from "@/components/auth/reset-password-form"

type ResetPasswordSearch = {
  token: string
}
export const Route = createFileRoute("/_auth/reset-password")({
  validateSearch: (search: Record<string, unknown>): ResetPasswordSearch => {
    return { token: search.token as string }
  },
  component: ResetPassword,
})

function ResetPassword() {
  return (
    <div className="w-full lg:w-1/2 flex items-center justify-center p-8 bg-card">
      <ResetPasswordForm />
    </div>
  )
}
