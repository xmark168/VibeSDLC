
import type React from "react"
import { useState } from "react"
import { motion } from "framer-motion"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Eye, EyeOff, Check, X, CheckCircle } from "lucide-react"
import { useNavigate } from "@tanstack/react-router"


export function ResetPasswordForm() {
    const [formData, setFormData] = useState({
        password: "",
        confirmPassword: "",
    })
    const [showPassword, setShowPassword] = useState(false)
    const [showConfirmPassword, setShowConfirmPassword] = useState(false)
    const [passwordFocused, setPasswordFocused] = useState(false)
    const [isLoading, setIsLoading] = useState(false)
    const [isSuccess, setIsSuccess] = useState(false)
    const navigate = useNavigate()

    const passwordRequirements = [
        { label: "At least 8 characters", met: formData.password.length >= 8 },
        { label: "Contains uppercase letter", met: /[A-Z]/.test(formData.password) },
        { label: "Contains lowercase letter", met: /[a-z]/.test(formData.password) },
        { label: "Contains number", met: /[0-9]/.test(formData.password) },
    ]

    const passwordsMatch = formData.password === formData.confirmPassword && formData.confirmPassword !== ""
    const allRequirementsMet = passwordRequirements.every((req) => req.met)

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()

        if (!allRequirementsMet) {
            return
        }

        if (!passwordsMatch) {
            return
        }

        setIsLoading(true)

        // Simulate API call
        await new Promise((resolve) => setTimeout(resolve, 1500))

        console.log("Password reset successful")
        setIsLoading(false)
        setIsSuccess(true)

        // Redirect to login after 2 seconds
        setTimeout(() => {
            navigate({ to: "/" })
        }, 2000)
    }

    if (isSuccess) {
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
                    <h2 className="text-3xl font-bold text-foreground">Password Reset!</h2>
                    <p className="text-muted-foreground">Your password has been successfully reset</p>
                </div>

                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}>
                    <p className="text-sm text-muted-foreground">Redirecting to login...</p>
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

            <div className="space-y-2">
                <motion.h2
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.4 }}
                    className="text-3xl font-bold text-foreground"
                >
                    Create New Password
                </motion.h2>
                <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.5 }}
                    className="text-muted-foreground"
                >
                    Your new password must be different from previously used passwords
                </motion.p>
            </div>

            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.6 }} className="space-y-6">
                <form onSubmit={handleSubmit} className="space-y-4">
                    <motion.div
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.7 }}
                        className="space-y-2"
                    >
                        <Label htmlFor="password" className="text-sm font-medium">
                            New Password
                        </Label>
                        <div className="relative">
                            <Input
                                id="password"
                                type={showPassword ? "text" : "password"}
                                placeholder="Create a strong password"
                                value={formData.password}
                                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                                onFocus={() => setPasswordFocused(true)}
                                onBlur={() => setPasswordFocused(false)}
                                className="h-12 bg-secondary/50 border-border text-base pr-10"
                                required
                            />
                            <button
                                type="button"
                                onClick={() => setShowPassword(!showPassword)}
                                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                            >
                                {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                            </button>
                        </div>

                        {/* Password Requirements */}
                        {(passwordFocused || formData.password) && (
                            <motion.div
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: "auto" }}
                                exit={{ opacity: 0, height: 0 }}
                                className="space-y-2 pt-2"
                            >
                                {passwordRequirements.map((req, index) => (
                                    <motion.div
                                        key={index}
                                        initial={{ opacity: 0, x: -10 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        transition={{ delay: index * 0.1 }}
                                        className="flex items-center gap-2 text-sm"
                                    >
                                        {req.met ? (
                                            <Check className="h-4 w-4 text-green-500" />
                                        ) : (
                                            <X className="h-4 w-4 text-muted-foreground" />
                                        )}
                                        <span className={req.met ? "text-green-500" : "text-muted-foreground"}>{req.label}</span>
                                    </motion.div>
                                ))}
                            </motion.div>
                        )}
                    </motion.div>

                    <motion.div
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.8 }}
                        className="space-y-2"
                    >
                        <Label htmlFor="confirmPassword" className="text-sm font-medium">
                            Confirm New Password
                        </Label>
                        <div className="relative">
                            <Input
                                id="confirmPassword"
                                type={showConfirmPassword ? "text" : "password"}
                                placeholder="Re-enter your password"
                                value={formData.confirmPassword}
                                onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                                className={`h-12 bg-secondary/50 border-border text-base pr-10 ${formData.confirmPassword && !passwordsMatch ? "border-red-500" : ""
                                    } ${formData.confirmPassword && passwordsMatch ? "border-green-500" : ""}`}
                                required
                            />
                            <button
                                type="button"
                                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                            >
                                {showConfirmPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                            </button>
                        </div>
                        {formData.confirmPassword && !passwordsMatch && (
                            <motion.p
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                className="text-sm text-red-500 flex items-center gap-1"
                            >
                                <X className="h-4 w-4" />
                                Passwords do not match
                            </motion.p>
                        )}
                        {passwordsMatch && (
                            <motion.p
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                className="text-sm text-green-500 flex items-center gap-1"
                            >
                                <Check className="h-4 w-4" />
                                Passwords match
                            </motion.p>
                        )}
                    </motion.div>

                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.9 }}>
                        <Button
                            type="submit"
                            disabled={isLoading || !allRequirementsMet || !passwordsMatch}
                            className="w-full h-12 text-base font-semibold bg-primary hover:bg-primary/90 transition-all disabled:opacity-50"
                        >
                            {isLoading ? (
                                <motion.div
                                    animate={{ rotate: 360 }}
                                    transition={{ duration: 1, repeat: Number.POSITIVE_INFINITY, ease: "linear" }}
                                    className="w-5 h-5 border-2 border-white border-t-transparent rounded-full"
                                />
                            ) : (
                                "Reset Password"
                            )}
                        </Button>
                    </motion.div>
                </form>
            </motion.div>
        </motion.div>
    )
}
