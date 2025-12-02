import { createFileRoute } from "@tanstack/react-router"
import { z } from "zod"
import { OTPVerificationForm } from "@/components/auth/otp-verification-form"

const verifyOtpSearchSchema = z.object({
  email: z.string().email({ message: "Invalid email format" }).optional(),
})

type VerifyOtpSearch = z.infer<typeof verifyOtpSearchSchema>

export const Route = createFileRoute("/_auth/verify-otp")({
  validateSearch: (search: Record<string, unknown>): VerifyOtpSearch => {
    return verifyOtpSearchSchema.parse(search)
  },
  component: VerifyOtp,
})

function VerifyOtp() {
  return (
    <div 
      className="w-full lg:w-1/2 flex items-center justify-center p-8"
      style={{
        background: "linear-gradient(to right, #f0f4fa 0%, #f5f7fa 30%, #ffffff 100%)",
      }}
    >
      <OTPVerificationForm />
    </div>
  )
}
