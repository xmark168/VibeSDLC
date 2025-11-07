import { createFileRoute, Outlet } from "@tanstack/react-router"
import { motion } from "framer-motion"
import { CheckCircle, ClipboardList, Code, Workflow } from "lucide-react"
import { requireNoAuth } from "@/utils/auth"

export const Route = createFileRoute("/_auth")({
  beforeLoad: async () => {
    await requireNoAuth()
  },
  component: RouteComponent,
})

function RouteComponent() {
  return (
    <div className="min-h-screen flex">
      {/* Left Side - Animated Agent Circle */}
      <div
        className="relative flex flex-1 items-center justify-center overflow-hidden p-8 lg:p-16"
        style={{
          background:
            "linear-gradient(90deg,rgba(39, 39, 115, 1) 0%, rgba(55, 55, 161, 1) 35%, rgb(34, 35, 39) 100%)",
        }}
      >
        {/* Animated Background Gradient Blobs */}
        <div className="absolute inset-0">
          <motion.div
            className="absolute left-1/4 top-1/4 h-96 w-96 rounded-full bg-white/20 blur-3xl"
            animate={{ y: [0, -10, 0] }}
            transition={{
              duration: 3,
              repeat: Number.POSITIVE_INFINITY,
              ease: "easeInOut",
            }}
          />
          <motion.div
            className="absolute right-1/4 bottom-1/4 h-96 w-96 rounded-full bg-purple-300/30 blur-3xl"
            animate={{ y: [0, -10, 0] }}
            transition={{
              duration: 3,
              repeat: Number.POSITIVE_INFINITY,
              ease: "easeInOut",
              delay: 1,
            }}
          />
        </div>

        <div className="relative z-10 flex flex-col items-center justify-center text-center">
          {/* Rotating Circle with AI Agents */}
          <motion.div
            className="relative mb-12 h-96 w-96"
            animate={{ y: [0, -10, 0] }}
            transition={{
              duration: 3,
              repeat: Number.POSITIVE_INFINITY,
              ease: "easeInOut",
            }}
          >
            <div className="absolute left-1/2 top-1/2 h-72 w-72 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white/15 backdrop-blur-sm" />

            <div
              className="absolute left-1/2 top-1/2 h-48 w-48 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white/25 backdrop-blur-md border border-white/40"
              style={{ boxShadow: "0 10px 40px rgba(0, 0, 0, 0.15)" }}
            >
              <div className="flex h-full w-full items-center justify-center">
                <div className="text-center">
                  <div className="text-5xl font-bold text-white drop-shadow-lg">
                    AI
                  </div>
                  <div className="text-base font-medium text-white/95 drop-shadow-md">
                    Powered
                  </div>
                </div>
              </div>
            </div>

            {/* Rotating Container */}
            <motion.div
              className="absolute inset-0"
              animate={{ rotate: 360 }}
              transition={{
                duration: 20,
                repeat: Number.POSITIVE_INFINITY,
                ease: "linear",
              }}
            >
              {/* Product Owner - Top */}
              <motion.div
                className="absolute left-1/2 top-0 -translate-x-1/2"
                animate={{ rotate: -360 }}
                transition={{
                  duration: 20,
                  repeat: Number.POSITIVE_INFINITY,
                  ease: "linear",
                }}
              >
                <div className="flex flex-col items-center gap-3">
                  <motion.div
                    className="group relative"
                    whileHover={{ scale: 1.1 }}
                    transition={{ type: "spring", stiffness: 300 }}
                  >
                    <motion.div
                      className="absolute inset-0 rounded-full bg-blue-400/40 blur-xl"
                      whileHover={{ opacity: 0.6 }}
                    />
                    <div className="relative flex h-20 w-20 items-center justify-center rounded-full bg-white shadow-lg backdrop-blur-sm border-2 border-white/60">
                      <ClipboardList className="h-10 w-10 text-blue-600" />
                    </div>
                  </motion.div>
                  <p className="whitespace-nowrap rounded-full bg-white px-4 py-1.5 text-sm font-semibold text-blue-600 shadow-md backdrop-blur-sm">
                    Product Owner
                  </p>
                </div>
              </motion.div>

              {/* Scrum Master - Right */}
              <motion.div
                className="absolute right-0 top-1/2 -translate-y-1/2"
                animate={{ rotate: -360 }}
                transition={{
                  duration: 20,
                  repeat: Number.POSITIVE_INFINITY,
                  ease: "linear",
                }}
              >
                <div className="flex flex-col items-center gap-3">
                  <motion.div
                    className="group relative"
                    whileHover={{ scale: 1.1 }}
                    transition={{ type: "spring", stiffness: 300 }}
                  >
                    <motion.div
                      className="absolute inset-0 rounded-full bg-purple-400/40 blur-xl"
                      whileHover={{ opacity: 0.6 }}
                    />
                    <div className="relative flex h-20 w-20 items-center justify-center rounded-full bg-white shadow-lg backdrop-blur-sm border-2 border-white/60">
                      <Workflow className="h-10 w-10 text-purple-600" />
                    </div>
                  </motion.div>
                  <p className="whitespace-nowrap rounded-full bg-white px-4 py-1.5 text-sm font-semibold text-purple-600 shadow-md backdrop-blur-sm">
                    Scrum Master
                  </p>
                </div>
              </motion.div>

              {/* Developer - Bottom */}
              <motion.div
                className="absolute bottom-0 left-1/2 -translate-x-1/2"
                animate={{ rotate: -360 }}
                transition={{
                  duration: 20,
                  repeat: Number.POSITIVE_INFINITY,
                  ease: "linear",
                }}
              >
                <div className="flex flex-col items-center gap-3">
                  <motion.div
                    className="group relative"
                    whileHover={{ scale: 1.1 }}
                    transition={{ type: "spring", stiffness: 300 }}
                  >
                    <motion.div
                      className="absolute inset-0 rounded-full bg-blue-400/40 blur-xl"
                      whileHover={{ opacity: 0.6 }}
                    />
                    <div className="relative flex h-20 w-20 items-center justify-center rounded-full bg-white shadow-lg backdrop-blur-sm border-2 border-white/60">
                      <Code className="h-10 w-10 text-blue-600" />
                    </div>
                  </motion.div>
                  <p className="whitespace-nowrap rounded-full bg-white px-4 py-1.5 text-sm font-semibold text-blue-600 shadow-md backdrop-blur-sm">
                    Developer
                  </p>
                </div>
              </motion.div>

              {/* Tester - Left */}
              <motion.div
                className="absolute left-0 top-1/2 -translate-y-1/2"
                animate={{ rotate: -360 }}
                transition={{
                  duration: 20,
                  repeat: Number.POSITIVE_INFINITY,
                  ease: "linear",
                }}
              >
                <div className="flex flex-col items-center gap-3">
                  <motion.div
                    className="group relative"
                    whileHover={{ scale: 1.1 }}
                    transition={{ type: "spring", stiffness: 300 }}
                  >
                    <motion.div
                      className="absolute inset-0 rounded-full bg-purple-400/40 blur-xl"
                      whileHover={{ opacity: 0.6 }}
                    />
                    <div className="relative flex h-20 w-20 items-center justify-center rounded-full bg-white shadow-lg backdrop-blur-sm border-2 border-white/60">
                      <CheckCircle className="h-10 w-10 text-purple-600" />
                    </div>
                  </motion.div>
                  <p className="whitespace-nowrap rounded-full bg-white px-4 py-1.5 text-sm font-semibold text-purple-600 shadow-md backdrop-blur-sm">
                    Tester
                  </p>
                </div>
              </motion.div>
            </motion.div>

            <svg
              className="absolute inset-0 h-full w-full opacity-30"
              style={{ transform: "rotate(0deg)" }}
            >
              <circle
                cx="50%"
                cy="50%"
                r="35%"
                fill="none"
                stroke="white"
                strokeWidth="1.5"
                strokeDasharray="4 4"
              />
              <circle
                cx="50%"
                cy="50%"
                r="45%"
                fill="none"
                stroke="white"
                strokeWidth="1.5"
                strokeDasharray="8 8"
              />
            </svg>
          </motion.div>

          {/* Heading Text */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4, duration: 0.6 }}
            className="mb-8"
          >
            <h1 className="text-5xl font-bold mb-4 text-balance leading-tight text-white drop-shadow-lg">
              Dream, Chat, Create
              <br />
              Your{" "}
              <span className="text-purple-200 drop-shadow-lg">
                24/7 AI Team
              </span>
            </h1>
            <p className="text-white text-lg font-medium drop-shadow-md">
              Providing the First AI Software Company
            </p>
          </motion.div>
        </div>
      </div>

      {/* Right Side - Login Form */}
      <Outlet />
    </div>
  )
}
