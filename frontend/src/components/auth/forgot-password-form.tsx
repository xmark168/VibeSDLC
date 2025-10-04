
import type React from "react"
import { useState } from "react"
import { motion } from "framer-motion"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Mail, ArrowLeft, CheckCircle, Link } from "lucide-react"
import { useNavigate } from "@tanstack/react-router"


export function ForgotPasswordForm() {
    const [email, setEmail] = useState("")
    const [isSubmitted, setIsSubmitted] = useState(false)
    const [isLoading, setIsLoading] = useState(false)
    const navigate = useNavigate()
    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setIsLoading(true)

        await new Promise((resolve) => setTimeout(resolve, 1500))

        console.log("Password reset requested for:", email)
        setIsLoading(false)
        setIsSubmitted(true)

        setTimeout(() => {

            navigate({ to: "/verify-otp" })
        }, 2000)
    }

    if (isSubmitted) {
        return (
            <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.5 }}
                className="w-full max-w-md space-y-8 text-center"
            >
                <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
                    className="mx-auto w-20 h-20 bg-green-100 rounded-full flex items-center justify-center"
                >
                    <CheckCircle className="w-10 h-10 text-green-600" />
                </motion.div>

                <div className="space-y-2">
                    <h2 className="text-3xl font-bold text-foreground">Check Your Email</h2>
                    <p className="text-muted-foreground">
                        {"We've sent a verification code to"}
                        <br />
                        <span className="font-semibold text-foreground">{email}</span>
                    </p>
                </div>

                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }} className="space-y-4">
                    <p className="text-sm text-muted-foreground">{"Didn't receive the code? Check your spam folder or"}</p>
                    <Button variant="outline" onClick={() => setIsSubmitted(false)} className="w-full h-12">
                        Try Another Email
                    </Button>
                </motion.div>
            </motion.div>
        )
    }

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.6 }}
            className="w-full max-w-md space-y-8"
        >
            {/* Mobile logo */}
            <div className="lg:hidden flex items-center gap-2 mb-8">
                <div className="w-10 h-10 bg-primary rounded-lg flex items-center justify-center">
                    <span className="text-primary-foreground font-bold text-xl">M</span>
                </div>
                <span className="text-2xl font-bold">MGX</span>
            </div>

            {/* Back button */}
            {/* <Link
                to="/"
                className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
                <ArrowLeft className="w-4 h-4" />
                Back to login
            </Link> */}

            <div className="space-y-2">
                <motion.h2
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.4 }}
                    className="text-3xl font-bold text-foreground"
                >
                    Forgot Password?
                </motion.h2>
                <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.5 }}
                    className="text-muted-foreground"
                >
                    {"No worries, we'll send you reset instructions"}
                </motion.p>
            </div>

            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.6 }} className="space-y-6">
                <form onSubmit={handleSubmit} className="space-y-6">
                    <motion.div
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.7 }}
                        className="space-y-2"
                    >
                        <Label htmlFor="email" className="text-sm font-medium">
                            Email Address
                        </Label>
                        <div className="relative">
                            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                            <Input
                                id="email"
                                type="email"
                                placeholder="Enter your email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                className="h-12 bg-secondary/50 border-border text-base pl-10"
                                required
                            />
                        </div>
                        <p className="text-xs text-muted-foreground">{"We'll send a verification code to this email"}</p>
                    </motion.div>

                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.8 }}
                        className="space-y-4"
                    >
                        <Button
                            type="submit"
                            disabled={isLoading}
                            className="w-full h-12 text-base font-semibold bg-primary hover:bg-primary/90 transition-all"
                        >
                            {isLoading ? (
                                <motion.div
                                    animate={{ rotate: 360 }}
                                    transition={{ duration: 1, repeat: Number.POSITIVE_INFINITY, ease: "linear" }}
                                    className="w-5 h-5 border-2 border-white border-t-transparent rounded-full"
                                />
                            ) : (
                                "Send Reset Code"
                            )}
                        </Button>

                        <div className="text-center text-sm text-muted-foreground">
                            Remember your password?{" "}
                        </div>
                    </motion.div>
                </form>
            </motion.div>
        </motion.div>
    )
}
