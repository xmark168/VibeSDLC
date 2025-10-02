import { ForgotPasswordForm } from '@/components/auth/forgot-password-form';
import { createFileRoute } from '@tanstack/react-router'
import { motion } from "framer-motion";
export const Route = createFileRoute('/_auth/forgot-password')({
  component: ForgotPassword,
})

function ForgotPassword() {
  return (
    <motion.div
      initial={{ opacity: 0, x: 50 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.8, ease: "easeOut" }}
      className="w-full lg:w-1/2 flex items-center justify-center p-8 bg-card"
    >
      <ForgotPasswordForm />
    </motion.div>
  )
}
