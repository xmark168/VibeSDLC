import { OTPVerificationForm } from '@/components/auth/otp-verification-form';
import { createFileRoute } from '@tanstack/react-router'
import { motion } from "framer-motion";
export const Route = createFileRoute('/_auth/verify-otp')({
  component: VerifyOtp,
})

function VerifyOtp() {
  return (
    <div
      className="w-full lg:w-1/2 flex items-center justify-center p-8 bg-card"
    >
      <OTPVerificationForm />
    </div>
  )
}
