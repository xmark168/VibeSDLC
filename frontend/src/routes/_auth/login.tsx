import { isLoggedIn } from '@/hooks/useAuth'
import { createFileRoute, redirect } from '@tanstack/react-router'
import { LoginForm } from '../../components/auth/login-form'
import { motion } from "framer-motion";
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
        <motion.div
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, ease: "easeOut" }}
            className="w-full lg:w-1/2 flex items-center justify-center p-8 bg-card"
        >
            <LoginForm />
        </motion.div>
    )
}
