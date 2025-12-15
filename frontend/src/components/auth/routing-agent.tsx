import { motion } from "framer-motion"
import { CheckCircle, ClipboardList, Code, Workflow } from "lucide-react"

const agents = [
  {
    name: "Product Owner",
    icon: ClipboardList,
    iconColor: "text-blue-500",
    position: 0, // Top
  },
  {
    name: "Scrum Master",
    icon: Workflow,
    iconColor: "text-purple-500",
    position: 90, // Right
  },
  {
    name: "Developer",
    icon: Code,
    iconColor: "text-blue-500",
    position: 180, // Bottom
  },
  {
    name: "Tester",
    icon: CheckCircle,
    iconColor: "text-purple-500",
    position: 270, // Left
  },
]

export function RotatingAgents() {
  return (
    <div className="relative w-full max-w-lg aspect-square mx-auto">
      <motion.div
        animate={{ rotate: 360 }}
        transition={{
          duration: 40,
          repeat: Number.POSITIVE_INFINITY,
          ease: "linear",
        }}
        className="absolute inset-0"
      >
        {/* Outer ring with glassmorphism */}
        <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[400px] h-[400px] rounded-full border-2 border-white/20" />

        {agents.map((agent, index) => {
          const angle = (agent.position * Math.PI) / 180
          const radius = 200
          const x = Math.cos(angle) * radius
          const y = Math.sin(angle) * radius

          return (
            <motion.div
              key={agent.name}
              style={{
                position: "absolute",
                left: "50%",
                top: "50%",
                x: x - 40, // Center the 80px wide icon
                y: y - 40, // Center the 80px tall icon
              }}
              className="w-20 h-20"
            >
              <motion.div
                animate={{ rotate: -360 }}
                initial={{ scale: 0, opacity: 0 }}
                whileInView={{
                  scale: 1,
                  opacity: 1,
                }}
                viewport={{ once: true }}
                transition={{
                  scale: {
                    delay: 0.6 + index * 0.15,
                    duration: 0.5,
                    type: "spring",
                    stiffness: 200,
                  },
                  opacity: {
                    delay: 0.6 + index * 0.15,
                    duration: 0.5,
                  },
                  default: { ease: "linear" },
                }}
                className="flex flex-col items-center gap-3"
              >
                <motion.div
                  animate={{
                    y: [0, -8, 0],
                  }}
                  transition={{
                    duration: 3 + index * 0.5,
                    repeat: Number.POSITIVE_INFINITY,
                    ease: "easeInOut",
                    delay: index * 0.5,
                  }}
                  whileHover={{ scale: 1.1 }}
                  className="relative w-20 h-20 rounded-full bg-white shadow-xl flex items-center justify-center cursor-pointer"
                >
                  <agent.icon
                    className={`w-10 h-10 ${agent.iconColor}`}
                    strokeWidth={2.5}
                  />

                  {/* Subtle glow on hover */}
                  <motion.div
                    initial={{ opacity: 0 }}
                    whileHover={{ opacity: 0.3 }}
                    className={`absolute inset-0 rounded-full ${agent.iconColor.replace("text-", "bg-")} blur-xl -z-10`}
                  />
                </motion.div>

                <motion.div
                  initial={{ opacity: 0, y: -5 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.8 + index * 0.15, duration: 0.5 }}
                  className="px-4 py-1.5 bg-white rounded-full shadow-lg"
                >
                  <span className="text-sm font-medium text-purple-600 whitespace-nowrap">
                    {agent.name}
                  </span>
                </motion.div>
              </motion.div>
            </motion.div>
          )
        })}
      </motion.div>

      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <motion.div
          animate={{
            scale: [1, 1.02, 1],
          }}
          transition={{
            duration: 4,
            repeat: Number.POSITIVE_INFINITY,
            ease: "easeInOut",
          }}
          className="relative w-56 h-56 rounded-full backdrop-blur-xl bg-white/10 border border-white/30 shadow-2xl flex flex-col items-center justify-center"
        >
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.8 }}
            className="text-center"
          >
            <div className="text-5xl font-bold text-white mb-1">AI</div>
            <div className="text-lg text-white/80 font-light">Powered</div>
          </motion.div>
        </motion.div>
      </div>

      {/* Background glow effect */}
      <motion.div
        animate={{
          scale: [1, 1.1, 1],
          opacity: [0.2, 0.3, 0.2],
        }}
        transition={{
          duration: 5,
          repeat: Number.POSITIVE_INFINITY,
          ease: "easeInOut",
        }}
        className="absolute inset-0 flex items-center justify-center -z-10"
      >
        <div className="w-96 h-96 rounded-full bg-purple-400/20 blur-3xl" />
      </motion.div>
    </div>
  )
}
