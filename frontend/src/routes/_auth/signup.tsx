import { SignUpForm } from '@/components/auth/signup-form';
import { createFileRoute } from '@tanstack/react-router'
import { motion } from "framer-motion";

export const Route = createFileRoute('/_auth/signup')({
  component: Signup,
})

function Signup() {
  return (
    <div

      className="w-full lg:w-1/2 flex items-center justify-center p-8 bg-card"
    >
      <SignUpForm />
    </div>
  )
}
