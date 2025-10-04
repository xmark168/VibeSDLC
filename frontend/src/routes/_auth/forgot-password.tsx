import { ForgotPasswordForm } from '@/components/auth/forgot-password-form';
import { createFileRoute } from '@tanstack/react-router'
import { motion } from "framer-motion";
export const Route = createFileRoute('/_auth/forgot-password')({
  component: ForgotPassword,
})

function ForgotPassword() {
  return (
    <div
      className="w-full lg:w-1/2 flex items-center justify-center p-8 bg-card"
    >
      <ForgotPasswordForm />
    </div>
  )
}
