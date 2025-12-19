import { createFileRoute, redirect } from "@tanstack/react-router"
import { isLoggedIn } from "@/hooks/useAuth"
import { LoginForm } from "../../components/auth/login-form"
export const Route = createFileRoute("/_auth/login")({
  component: Login,
  beforeLoad: async () => {
    if (isLoggedIn()) {
      throw redirect({
        to: "/",
      })
    }
  },
})

function Login() {
  return (
    <div
      className="w-full lg:w-1/2 flex items-center justify-center p-8"
      style={{
        background:
          "linear-gradient(to right, #f0f4fa 0%, #f5f7fa 30%, #ffffff 100%)",
      }}
    >
      <LoginForm />
    </div>
  )
}
