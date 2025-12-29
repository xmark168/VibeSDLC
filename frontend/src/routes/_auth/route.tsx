import { createFileRoute, Outlet } from "@tanstack/react-router"
import { motion } from "framer-motion"
import { requireNoAuth } from "@/utils/auth"

export const Route = createFileRoute("/_auth")({
  beforeLoad: async () => {
    await requireNoAuth()
  },
  component: RouteComponent,
})

function RouteComponent() {
  return (
    <div className="min-h-screen flex overflow-hidden">
      {/* Left Side - Animated Agent Circle */}
      <div
        className="relative hidden lg:flex flex-1 items-center justify-center overflow-hidden p-8 lg:p-16"
        style={{
          background:
            "linear-gradient(to right, #ffffff 0%, #f8fafc 20%, #f1f5f9 40%, #eef2f7 60%, #f0f4fa 100%)",
          willChange: "transform",
        }}
      >
        {/* Animated Background Gradient Blobs */}
        <div className="absolute inset-0">
          <motion.div
            className="absolute left-1/4 top-1/4 h-96 w-96 rounded-full blur-3xl"
            style={{ background: "linear-gradient(to br, rgba(201, 100, 66, 0.25), rgba(61, 57, 41, 0.2))" }}
            animate={{
              y: [0, -20, 0],
              x: [0, 10, 0],
              scale: [1, 1.05, 1]
            }}
            transition={{
              duration: 8,
              repeat: Number.POSITIVE_INFINITY,
              ease: "easeInOut",
            }}
          />
          <motion.div
            className="absolute right-1/4 bottom-1/4 h-96 w-96 rounded-full blur-3xl"
            style={{ background: "linear-gradient(to br, rgba(233, 230, 220, 0.4), rgba(201, 100, 66, 0.25))" }}
            animate={{
              y: [0, 20, 0],
              x: [0, -10, 0],
              scale: [1, 1.08, 1]
            }}
            transition={{
              duration: 10,
              repeat: Number.POSITIVE_INFINITY,
              ease: "easeInOut",
              delay: 1,
            }}
          />
          <motion.div
            className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 h-[500px] w-[500px] rounded-full blur-3xl"
            style={{ background: "linear-gradient(to br, rgba(201, 100, 66, 0.15), rgba(233, 230, 220, 0.2))" }}
            animate={{
              scale: [1, 1.1, 1],
              rotate: [0, 180, 360]
            }}
            transition={{
              duration: 20,
              repeat: Number.POSITIVE_INFINITY,
              ease: "linear",
            }}
          />
        </div>

        <div className="relative z-10 flex flex-col items-center justify-center text-center">
          {/* Rotating Circle with AI Agents */}
          <motion.div
            className="relative mb-12 h-96 w-96"
            animate={{ y: [0, -10, 0] }}
            transition={{
              duration: 4,
              repeat: Number.POSITIVE_INFINITY,
              ease: "easeInOut",
            }}
          >
            {/* Outer glow ring */}
            <div
              className="absolute left-1/2 top-1/2 h-80 w-80 -translate-x-1/2 -translate-y-1/2 rounded-full blur-xl"
              style={{ background: "linear-gradient(to br, rgba(201, 100, 66, 0.3), rgba(233, 230, 220, 0.4))" }}
            />

            {/* Middle ring */}
            <div
              className="absolute left-1/2 top-1/2 h-72 w-72 -translate-x-1/2 -translate-y-1/2 rounded-full backdrop-blur-sm shadow-xl"
              style={{ background: "linear-gradient(to br, rgba(233, 230, 220, 0.8), rgba(255, 255, 255, 0.7))" }}
            />

            {/* Center AI circle */}
            <div
              className="absolute left-1/2 top-1/2 h-48 w-48 -translate-x-1/2 -translate-y-1/2 rounded-full shadow-2xl"
              style={{
                background: "#e9e6dc",
                boxShadow: "0 20px 60px rgba(61, 57, 41, 0.3), inset 0 0 30px rgba(201, 100, 66, 0.1)"
              }}
            >
              <div
                className="absolute inset-2 rounded-full"
                style={{
                  background: "linear-gradient(145deg, #c96442 0%, #b55638 100%)",
                  boxShadow: "0 8px 32px rgba(201, 100, 66, 0.4)"
                }}
              />
              <div className="relative flex h-full w-full items-center justify-center">
                <div className="text-center">
                  <motion.div
                    className="text-5xl font-bold"
                    style={{ color: "#e9e6dc" }}
                    animate={{ scale: [1, 1.05, 1] }}
                    transition={{
                      duration: 2,
                      repeat: Number.POSITIVE_INFINITY,
                      ease: "easeInOut",
                    }}
                  >
                    AI
                  </motion.div>
                  <div
                    className="text-base font-medium"
                    style={{ color: "rgba(233, 230, 220, 0.9)" }}
                  >
                    Agents
                  </div>
                </div>
              </div>
            </div>

            {/* Rotating Container */}
            <motion.div
              className="absolute inset-0"
              animate={{ rotate: 360 }}
              transition={{
                duration: 25,
                repeat: Number.POSITIVE_INFINITY,
                ease: "linear",
              }}
            >
              {/* Teamlead - Top */}
              <motion.div
                className="absolute left-1/2 top-0 -translate-x-1/2"
                animate={{ rotate: -360 }}
                transition={{
                  duration: 25,
                  repeat: Number.POSITIVE_INFINITY,
                  ease: "linear",
                }}
              >
                <div className="flex flex-col items-center gap-3">
                  <motion.div
                    className="group relative"
                    whileHover={{ scale: 1.15 }}
                    transition={{ type: "spring", stiffness: 300 }}
                  >
                    <motion.div
                      className="absolute -inset-2 rounded-full bg-gradient-to-br from-blue-400/60 to-indigo-400/60 blur-xl"
                      initial={{ opacity: 0.5 }}
                      whileHover={{ opacity: 0.9, scale: 1.3 }}
                    />
                    <div className="relative h-20 w-20 rounded-full overflow-hidden shadow-xl ring-4 ring-white/80 ring-offset-2 ring-offset-transparent">
                      <img
                        src="/assets/images/agent/3.png"
                        alt="Teamlead"
                        className="h-full w-full object-cover"
                      />
                      <div className="absolute inset-0 bg-gradient-to-t from-blue-500/20 to-transparent" />
                    </div>
                  </motion.div>
                  <p className="whitespace-nowrap rounded-full bg-white/90 backdrop-blur-sm px-4 py-1.5 text-sm font-semibold text-blue-600 shadow-lg border border-blue-100">
                    Team leader
                  </p>
                </div>
              </motion.div>

              {/* Business Analyst - Right */}
              <motion.div
                className="absolute right-0 top-1/2 -translate-y-1/2"
                animate={{ rotate: -360 }}
                transition={{
                  duration: 25,
                  repeat: Number.POSITIVE_INFINITY,
                  ease: "linear",
                }}
              >
                <div className="flex flex-col items-center gap-3">
                  <motion.div
                    className="group relative"
                    whileHover={{ scale: 1.15 }}
                    transition={{ type: "spring", stiffness: 300 }}
                  >
                    <motion.div
                      className="absolute -inset-2 rounded-full bg-gradient-to-br from-purple-400/60 to-pink-400/60 blur-xl"
                      initial={{ opacity: 0.5 }}
                      whileHover={{ opacity: 0.9, scale: 1.3 }}
                    />
                    <div className="relative h-20 w-20 rounded-full overflow-hidden shadow-xl ">
                      <img
                        src="/assets/images/agent/1.webp"
                        alt="Business Analyst"
                        className="h-full w-full object-cover"
                      />
                      <div className="absolute inset-0 bg-gradient-to-t from-purple-500/20 to-transparent" />
                    </div>
                  </motion.div>
                  <p className="whitespace-nowrap rounded-full bg-white/90 backdrop-blur-sm px-4 py-1.5 text-sm font-semibold text-purple-600 shadow-lg border border-purple-100">
                    Business Analyst
                  </p>
                </div>
              </motion.div>

              {/* Developer - Bottom */}
              <motion.div
                className="absolute bottom-0 left-1/2 -translate-x-1/2"
                animate={{ rotate: -360 }}
                transition={{
                  duration: 25,
                  repeat: Number.POSITIVE_INFINITY,
                  ease: "linear",
                }}
              >
                <div className="flex flex-col items-center gap-3">
                  <motion.div
                    className="group relative"
                    whileHover={{ scale: 1.15 }}
                    transition={{ type: "spring", stiffness: 300 }}
                  >
                    <motion.div
                      className="absolute -inset-2 rounded-full bg-gradient-to-br from-emerald-400/60 to-teal-400/60 blur-xl"
                      initial={{ opacity: 0.5 }}
                      whileHover={{ opacity: 0.9, scale: 1.3 }}
                    />
                    <div className="relative h-20 w-20 rounded-full overflow-hidden shadow-xl ring-4 ring-white/80 ring-offset-2 ring-offset-transparent">
                      <img
                        src="/assets/images/agent/2.png"
                        alt="Developer"
                        className="h-full w-full object-cover"
                      />
                      <div className="absolute inset-0 bg-gradient-to-t from-emerald-500/20 to-transparent" />
                    </div>
                  </motion.div>
                  <p className="whitespace-nowrap rounded-full bg-white/90 backdrop-blur-sm px-4 py-1.5 text-sm font-semibold text-emerald-600 shadow-lg border border-emerald-100">
                    Developer
                  </p>
                </div>
              </motion.div>

              {/* Tester - Left */}
              <motion.div
                className="absolute left-0 top-1/2 -translate-y-1/2"
                animate={{ rotate: -360 }}
                transition={{
                  duration: 25,
                  repeat: Number.POSITIVE_INFINITY,
                  ease: "linear",
                }}
              >
                <div className="flex flex-col items-center gap-3">
                  <motion.div
                    className="group relative"
                    whileHover={{ scale: 1.15 }}
                    transition={{ type: "spring", stiffness: 300 }}
                  >
                    <motion.div
                      className="absolute -inset-2 rounded-full bg-gradient-to-br from-orange-400/60 to-amber-400/60 blur-xl"
                      initial={{ opacity: 0.5 }}
                      whileHover={{ opacity: 0.9, scale: 1.3 }}
                    />
                    <div className="relative h-20 w-20 rounded-full overflow-hidden shadow-xl ring-4 ring-white/80 ring-offset-2 ring-offset-transparent">
                      <img
                        src="/assets/images/agent/4.webp"
                        alt="Tester"
                        className="h-full w-full object-cover"
                      />
                      <div className="absolute inset-0 bg-gradient-to-t from-orange-500/20 to-transparent" />
                    </div>
                  </motion.div>
                  <p className="whitespace-nowrap rounded-full bg-white/90 backdrop-blur-sm px-4 py-1.5 text-sm font-semibold text-orange-600 shadow-lg border border-orange-100">
                    Tester
                  </p>
                </div>
              </motion.div>
            </motion.div>

            {/* Decorative rings */}
            <svg
              className="absolute inset-0 h-full w-full"
              style={{ transform: "rotate(0deg)" }}
            >
              <defs>
                <linearGradient id="ringGradient1" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#c96442" stopOpacity="0.3" />
                  <stop offset="100%" stopColor="#3d3929" stopOpacity="0.3" />
                </linearGradient>
                <linearGradient id="ringGradient2" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#3d3929" stopOpacity="0.2" />
                  <stop offset="100%" stopColor="#c96442" stopOpacity="0.2" />
                </linearGradient>
              </defs>
              <circle
                cx="50%"
                cy="50%"
                r="35%"
                fill="none"
                stroke="url(#ringGradient1)"
                strokeWidth="2"
                strokeDasharray="6 6"
              />
              <circle
                cx="50%"
                cy="50%"
                r="46%"
                fill="none"
                stroke="url(#ringGradient2)"
                strokeWidth="1.5"
                strokeDasharray="10 10"
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
            <h1 className="text-5xl font-bold mb-4 text-balance leading-tight">
              <span className="bg-gradient-to-r from-gray-800 via-gray-700 to-gray-800 bg-clip-text text-transparent">
                Dream, Chat, Create
              </span>
              <br />
              <span className="bg-gradient-to-r from-gray-700 to-gray-600 bg-clip-text text-transparent">
                Your{" "}
              </span>
              <span
                className="bg-clip-text text-transparent"
                style={{ backgroundImage: "linear-gradient(to right, #c96442, #3d3929, #c96442)" }}
              >
                24/7 AI Team
              </span>
            </h1>
            <p className="text-gray-600 text-lg font-medium">
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
