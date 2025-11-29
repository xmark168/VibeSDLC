import { Link } from "@tanstack/react-router"
import { motion } from "framer-motion"
import { Check, Eye, EyeOff, Facebook, Github, X } from "lucide-react"
import type React from "react"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import useAuth from "@/hooks/useAuth"
import { withToast } from "@/utils"
import { FaGooglePlusG } from "react-icons/fa6"

export function SignUpForm() {
  const [formData, setFormData] = useState({
    fullname: "",
    email: "",
    password: "",
    confirmPassword: "",
  })
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [passwordFocused, setPasswordFocused] = useState(false)
  const { signUpMutation } = useAuth()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    await withToast(
      new Promise((resolve, reject) => {
        signUpMutation.mutate(
          {
            requestBody: {
              full_name: formData.fullname,
              email: formData.email,
              password: formData.password,
              confirm_password: formData.confirmPassword,
            },
          },
          {
            onSuccess: resolve,
            onError: reject,
          },
        )
      }),
      {
        loading: "Đang tạo tài khoản...",
        success: <b>Tạo tài khoản thành công!</b>,
        error: <b>Tạo tài khoản thất bại. Vui lòng thử lại.</b>,
      },
    )
  }
  const handleLoginGoogle = () => {
    console.log('OAuth redirect starting:', `${import.meta.env.VITE_API_URL}/api/v1/auth/google`);
    console.time('oauth-redirect');
    // Redirect to backend OAuth endpoint
    window.location.href = `${import.meta.env.VITE_API_URL}/api/v1/auth/google`;
  };

  const handleLoginGithub = () => {
    console.log('OAuth redirect starting:', `${import.meta.env.VITE_API_URL}/api/v1/auth/github`);
    console.time('oauth-redirect');
    window.location.href = `${import.meta.env.VITE_API_URL}/api/v1/auth/github`;
  };

  const handleLoginFacebook = () => {
    console.log('OAuth redirect starting:', `${import.meta.env.VITE_API_URL}/api/v1/auth/facebook`);
    console.time('oauth-redirect');
    window.location.href = `${import.meta.env.VITE_API_URL}/api/v1/auth/facebook`;
  };
  const passwordRequirements = [
    { label: "Ít nhất 8 ký tự", met: formData.password.length >= 8 },
    {
      label: "Chứa chữ in hoa",
      met: /[A-Z]/.test(formData.password),
    },
    {
      label: "Chứa chữ thường",
      met: /[a-z]/.test(formData.password),
    },
    { label: "Chứa số", met: /[0-9]/.test(formData.password) },
  ]

  const passwordsMatch =
    formData.password === formData.confirmPassword &&
    formData.confirmPassword !== ""

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
          Tạo tài khoản
        </motion.h2>
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="text-muted-foreground"
        >
          Bắt đầu với đội ngũ AI của bạn
        </motion.p>
      </div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
        className="space-y-6"
      >
        {/* Social Login Buttons */}
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row gap-3">
            <Button
              onClick={handleLoginGoogle}
              variant="outline"
              className="flex-1 h-12 border-2 border-border hover:bg-transparent hover:border-border"
            >
              <FaGooglePlusG className="mr-2 h-5 w-5 text-[#EA4335]" />
              <span className="font-medium">Google</span>
            </Button>
            <Button
              onClick={handleLoginGithub}
              variant="outline"
              className="flex-1 h-12 border-2 border-border hover:bg-transparent hover:border-border"
            >
              <Github className="mr-2 h-5 w-5" />
              <span className="font-medium">GitHub</span>
            </Button>
            <Button
              onClick={handleLoginFacebook}
              variant="outline"
              className="flex-1 h-12 border-2 border-border hover:bg-transparent hover:border-border"
            >
              <Facebook className="mr-2 h-5 w-5 text-[#1877F2]" />
              <span className="font-medium">Facebook</span>
            </Button>
          </div>
        </div>

        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <span className="w-full border-t border-border" />
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="bg-card px-4 text-muted-foreground">
              Hoặc tiếp tục với email
            </span>
          </div>
        </div>

        {/* Sign Up Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.6 }}
            className="space-y-2"
          >
            <Label htmlFor="name" className="text-sm font-medium">
              Họ và tên
            </Label>
            <Input
              id="name"
              type="text"
              placeholder="Nguyễn Văn A"
              value={formData.fullname}
              onChange={(e) =>
                setFormData({ ...formData, fullname: e.target.value })
              }
              className="h-12 bg-secondary/50 border-border text-base"
              required
            />
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.7 }}
            className="space-y-2"
          >
            <Label htmlFor="email" className="text-sm font-medium">
              Địa chỉ Email
            </Label>
            <Input
              id="email"
              type="email"
              placeholder="email@example.com"
              value={formData.email}
              onChange={(e) =>
                setFormData({ ...formData, email: e.target.value })
              }
              className="h-12 bg-secondary/50 border-border text-base"
              required
            />
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.8 }}
            className="space-y-2"
          >
            <Label htmlFor="password" className="text-sm font-medium">
              Mật khẩu
            </Label>
            <div className="relative">
              <Input
                id="password"
                type={showPassword ? "text" : "password"}
                placeholder="Tạo mật khẩu mạnh"
                value={formData.password}
                onChange={(e) =>
                  setFormData({ ...formData, password: e.target.value })
                }
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
                {showPassword ? (
                  <EyeOff className="h-5 w-5" />
                ) : (
                  <Eye className="h-5 w-5" />
                )}
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
                    <span
                      className={
                        req.met ? "text-green-500" : "text-muted-foreground"
                      }
                    >
                      {req.label}
                    </span>
                  </motion.div>
                ))}
              </motion.div>
            )}
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.9 }}
            className="space-y-2"
          >
            <Label htmlFor="confirmPassword" className="text-sm font-medium">
              Xác nhận mật khẩu
            </Label>
            <div className="relative">
              <Input
                id="confirmPassword"
                type={showConfirmPassword ? "text" : "password"}
                placeholder="Nhập lại mật khẩu"
                value={formData.confirmPassword}
                onChange={(e) =>
                  setFormData({ ...formData, confirmPassword: e.target.value })
                }
                className={`h-12 bg-secondary/50 border-border text-base pr-10 ${formData.confirmPassword && !passwordsMatch
                  ? "border-red-500"
                  : ""
                  } ${formData.confirmPassword && passwordsMatch ? "border-green-500" : ""}`}
                required
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
              >
                {showConfirmPassword ? (
                  <EyeOff className="h-5 w-5" />
                ) : (
                  <Eye className="h-5 w-5" />
                )}
              </button>
            </div>
            {formData.confirmPassword && !passwordsMatch && (
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-sm text-red-500 flex items-center gap-1"
              >
                <X className="h-4 w-4" />
                Mật khẩu không khớp
              </motion.p>
            )}
            {passwordsMatch && (
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-sm text-green-500 flex items-center gap-1"
              >
                <Check className="h-4 w-4" />
                Mật khẩu khớp
              </motion.p>
            )}
          </motion.div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1 }}
          >
            <Button
              type="submit"
              className="w-full h-12 text-base font-semibold bg-primary hover:bg-primary/90 transition-all"
            >
              Tạo tài khoản
            </Button>
          </motion.div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.1 }}
            className="text-center text-sm text-muted-foreground"
          >
            Đã có tài khoản?{" "}
            <Link
              to="/login"
              className="text-foreground underline hover:text-accent transition-colors"
            >
              Đăng nhập
            </Link>
          </motion.div>
        </form>
      </motion.div>
    </motion.div>
  )
}
