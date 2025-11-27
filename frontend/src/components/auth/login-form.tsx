import { Link } from "@tanstack/react-router"
import { OAuthProvider } from "appwrite"
import { motion } from "framer-motion"
import type React from "react"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import useAuth from "@/hooks/useAuth"
import { account } from "@/lib/appwrite"
import { withToast } from "@/utils"
import { Chrome, Facebook, Github } from "lucide-react"
import { FaGooglePlusG } from "react-icons/fa6";

export function LoginForm() {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const { loginMutation } = useAuth()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    console.log("Login attempt:", { email, password })
    const data = { email, password }

    await withToast(
      new Promise((resolve, reject) => {
        loginMutation.mutate(
          {
            requestBody: {
              ...data,
            },
          },
          {
            onSuccess: resolve,
            onError: reject,
          },
        )
      }),
      {
        loading: "Đang đăng nhập...",
        success: <b>Chào mừng quay trở lại!</b>,
        error: <b>Đăng nhập thất bại. Vui lòng thử lại.</b>,
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


  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3, duration: 0.6 }}
      className="w-full max-w-md space-y-8"
    >
      {/* Logo Mobile */}
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
          Chào mừng quay trở lại
        </motion.h2>
      </div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
        className="space-y-6"
      >

        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <span className="w-full border-t border-border" />
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="bg-card px-4 text-muted-foreground">
              Đăng nhập bằng tài khoản đã đăng ký
            </span>
          </div>
        </div>

        {/* Form Email/Password */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email" className="sr-only">
              Email
            </Label>
            <Input
              id="email"
              type="email"
              placeholder="Email của bạn"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="h-12 bg-secondary/50 border-border text-base"
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="password" className="sr-only">
              Password
            </Label>
            <Input
              id="password"
              type="password"
              placeholder="Mật khẩu"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="h-12 bg-secondary/50 border-border text-base"
              required
            />
          </div>

          <div className="text-center text-sm text-muted-foreground">
            {"Chưa có tài khoản? "}
            <Link
              to="/signup"
              className="text-foreground underline transition-colors"
            >
              Tạo tài khoản mới
            </Link>
          </div>

          <Button
            type="submit"
            disabled={loginMutation.isPending}
            className="w-full h-12 text-base font-semibold bg-primary hover:bg-primary/90 transition-all"
          >
            {loginMutation.isPending ? "Đang đăng nhập..." : "Đăng nhập"}
          </Button>

          {loginMutation.error && (
            <div className="text-sm text-red-500 text-center">
              {loginMutation.error.message || "Đăng nhập thất bại"}
            </div>
          )}

          <div className="relative my-2">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-border"></div>
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-card px-2 text-muted-foreground">
                Hoặc tiếp tục với
              </span>
            </div>
          </div>

          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row gap-3">
              <Button onClick={handleLoginGoogle} variant="outline" className="flex-1 h-12 border-2 border-[#d1d5db] text-foreground hover:bg-google/10 hover:border-google transition-all duration-300 group" style={{ borderColor: '#d1d5db' }} >
                <FaGooglePlusG className="mr-2 h-5 w-5 text-google group-hover:scale-110 transition-transform" />
                <span className="font-medium">Google</span>
              </Button>
              <Button onClick={handleLoginGithub} variant="outline" className="flex-1 h-12 border-2 border-[#d1d5db] text-foreground hover:bg-github/10 hover:border-github transition-all duration-300 group" style={{ borderColor: '#d1d5db' }} >
                <Github className="mr-2 h-5 w-5 text-github group-hover:scale-110 transition-transform" /> <span className="font-medium">GitHub</span> </Button>
              <Button onClick={handleLoginFacebook} variant="outline" className="flex-1 h-12 border-2 border-[#d1d5db] text-foreground hover:bg-facebook/10 hover:border-facebook transition-all duration-300 group" style={{ borderColor: '#d1d5db' }} >
                <Facebook className="mr-2 h-5 w-5 text-facebook group-hover:scale-110 transition-transform" /> <span className="font-medium">Facebook</span> </Button> </div> </div>

          <div className="text-center">
            <Link
              to="/forgot-password"
              className="text-sm text-muted-foreground transition-colors underline"
            >
              Quên mật khẩu?
            </Link>
          </div>
        </form>
      </motion.div>
    </motion.div>
  )
}
