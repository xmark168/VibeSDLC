import { createFileRoute, redirect, useNavigate, useSearch } from "@tanstack/react-router"
import { isLoggedIn } from "@/hooks/useAuth"
import { TwoFactorVerifyForm } from "@/components/auth/two-factor-verify-form"

export const Route = createFileRoute("/_auth/verify-2fa")({
  component: Verify2FA,
  validateSearch: (search: Record<string, unknown>) => ({
    token: (search.token as string) || "",
  }),
  beforeLoad: async ({ search }) => {
    if (isLoggedIn()) {
      throw redirect({ to: "/" })
    }
    if (!search.token) {
      throw redirect({ to: "/login" })
    }
  },
})

function Verify2FA() {
  const { token } = useSearch({ from: "/_auth/verify-2fa" })

  return (
    <div 
      className="w-full lg:w-1/2 flex items-center justify-center p-8"
      style={{
        background: "linear-gradient(to right, #f0f4fa 0%, #f5f7fa 30%, #ffffff 100%)",
      }}
    >
      <TwoFactorVerifyForm tempToken={token} />
    </div>
  )
}
