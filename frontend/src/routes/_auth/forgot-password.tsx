import { createFileRoute } from "@tanstack/react-router"
import { ForgotPasswordForm } from "@/components/auth/forgot-password-form"
export const Route = createFileRoute("/_auth/forgot-password")({
  component: ForgotPassword,
})

function ForgotPassword() {
  return (
    <div 
      className="w-full lg:w-1/2 flex items-center justify-center p-8"
      style={{
        background: "linear-gradient(to right, #f0f4fa 0%, #f5f7fa 30%, #ffffff 100%)",
      }}
    >
      <ForgotPasswordForm />
    </div>
  )
}
