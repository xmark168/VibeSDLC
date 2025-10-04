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
        <div

            className="w-full lg:w-1/2 flex items-center justify-center p-8 bg-card"
        >
            <LoginForm />
        </div>
    )
}
