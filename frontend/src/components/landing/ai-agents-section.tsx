import { AnimatePresence, motion } from "framer-motion"
import { Sparkles, X } from "lucide-react"
import { useState } from "react"

interface Agent {
  id: string
  name: string
  role: string
  image: string
  description: string
  expertise: string
  skills: string[]
  service: string
}

const agents: Agent[] = [
  {
    id: "mike",
    name: "Mike",
    role: "Product Owner",
    image: "/assets/images/agent/scrum master.png",
    description: "Conflict resolution and decision-making",
    expertise: "Specialized expertise",
    skills: [
      "Overall project schedule monitoring",
      "External communication (primary interface)",
      "Team performance evaluation",
      "Resource optimization",
    ],
    service: "Global Service",
  },
  {
    id: "emma",
    name: "Emma",
    role: "Scrum Master",
    image: "/assets/images/agent/product owner.png",
    description: "Product vision and strategy",
    expertise: "Product Development",
    skills: [
      "Product roadmap planning",
      "Stakeholder management",
      "Feature prioritization",
      "Market analysis",
    ],
    service: "Global Service",
  },
  {
    id: "bob",
    name: "Bob",
    role: "Developer",
    image: "/assets/images/agent/develop.png",
    description: "System design and architecture",
    expertise: "Technical Architecture",
    skills: [
      "System architecture design",
      "Technology stack selection",
      "Code review and quality",
      "Performance optimization",
    ],
    service: "Global Service",
  },
  {
    id: "alex",
    name: "Alex",
    role: "Tester",
    image: "/assets/images/agent/tester.png",
    description: "Quality assurance and testing",
    expertise: "QA & Testing",
    skills: [
      "Test automation",
      "Bug tracking and reporting",
      "Quality metrics",
      "Continuous testing",
    ],
    service: "Global Service",
  },
]

export function AIAgentsSection() {
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null)

  return (
    <section className="relative py-20 px-4 overflow-hidden">
      {/* Subtle background gradient - blends with page background */}
      <div className="absolute inset-0 bg-gradient-to-b from-purple-950/5 via-transparent to-transparent" />

      {/* Fade-out edges for seamless blending */}
      <div className="absolute inset-0 bg-gradient-to-r from-background/80 via-transparent to-background/80" />
      <div className="absolute inset-0 bg-gradient-to-b from-background/60 via-transparent to-background/60" />

      {/* Animated background blobs - more subtle */}
      <motion.div
        animate={{
          scale: [1, 1.2, 1],
          opacity: [0.03, 0.08, 0.03],
        }}
        transition={{
          duration: 8,
          repeat: Number.POSITIVE_INFINITY,
          ease: "easeInOut",
        }}
        className="absolute top-1/4 left-1/4 w-96 h-96 rounded-full bg-purple-500/10 blur-3xl"
      />
      <motion.div
        animate={{
          scale: [1, 1.3, 1],
          opacity: [0.03, 0.06, 0.03],
        }}
        transition={{
          duration: 10,
          repeat: Number.POSITIVE_INFINITY,
          ease: "easeInOut",
          delay: 1,
        }}
        className="absolute bottom-1/4 right-1/4 w-96 h-96 rounded-full bg-violet-500/10 blur-3xl"
      />

      <div className="relative max-w-7xl mx-auto">
        {/* Section Header */}
        <div className="text-center mb-16">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-purple-500/10 border border-purple-500/20 mb-6"
          >
            <Sparkles className="w-4 h-4 text-purple-400" />
            <span className="text-sm font-medium text-purple-300">
              Meet Our AI Team
            </span>
          </motion.div>

          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="text-4xl md:text-5xl font-bold text-foreground mb-4"
          >
            AI Agents Working for You
          </motion.h2>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="text-lg text-muted-foreground max-w-2xl mx-auto"
          >
            Specialized AI agents collaborate seamlessly to deliver exceptional
            results
          </motion.p>
        </div>

        {/* Agents Grid - 4 Cards Layout */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {agents.map((agent, index) => (
            <motion.div
              key={agent.id}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              className={`
                                ${index % 2 === 1 ? "lg:mt-[-50px]" : ""}
                            `}
            >
              <AgentCard
                agent={agent}
                onClick={() => setSelectedAgent(agent)}
              />
            </motion.div>
          ))}
        </div>
      </div>

      {/* Agent Detail Modal */}
      <AnimatePresence>
        {selectedAgent && (
          <AgentModal
            agent={selectedAgent}
            onClose={() => setSelectedAgent(null)}
          />
        )}
      </AnimatePresence>
    </section>
  )
}

interface AgentCardProps {
  agent: Agent
  onClick: () => void
}

function AgentCard({ agent, onClick }: AgentCardProps) {
  return (
    <motion.div
      whileHover={{ scale: 1.05, y: -5 }}
      whileTap={{ scale: 0.98 }}
      onClick={onClick}
      className="relative group cursor-pointer"
    >
      <div className="relative rounded-3xl overflow-hidden">
        <div
          className="absolute inset-0 rounded-3xl"
          style={{
            background: "rgba(139, 92, 246, 0.1)",
            backdropFilter: "blur(12px)",
            WebkitBackdropFilter: "blur(12px)",
          }}
        />

        <div className="absolute inset-0 rounded-3xl border border-purple-500/30 group-hover:border-purple-400/50 transition-colors" />

        <div className="absolute inset-0 rounded-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-300">
          <div className="absolute inset-0 bg-gradient-to-b from-purple-500/20 to-transparent rounded-3xl" />
        </div>

        <div className="relative p-6 flex flex-col items-center">
          <div className="relative mb-4">
            <div className="w-32 h-32 rounded-2xl bg-gradient-to-br from-purple-900/40 to-purple-950/40 p-3 backdrop-blur-sm border border-purple-500/20">
              <img
                src={agent.image}
                alt={agent.name}
                className="w-full h-full object-contain"
              />
            </div>

            {/* Floating icon */}
            <motion.div
              animate={{ y: [0, -5, 0] }}
              transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY }}
              className="absolute -bottom-2 -right-2 w-8 h-8 rounded-full bg-purple-500/80 backdrop-blur-sm border border-purple-400/50 flex items-center justify-center"
            >
              <Sparkles className="w-4 h-4 text-white" />
            </motion.div>
          </div>

          {/* Pixel Text below image */}
          <div className="mb-3">
            <p
              className="text-xs text-purple-300 tracking-wider"
              style={{
                fontFamily: '"Courier New", Courier, monospace',
                textShadow:
                  "0 0 8px rgba(168, 85, 247, 0.4), 0 0 2px rgba(168, 85, 247, 0.6)",
                letterSpacing: "0.15em",
              }}
            >
              &lt;{agent.name.toUpperCase()}/&gt;
            </p>
          </div>

          {/* Agent Info */}
          <div className="text-center space-y-2 w-full">
            <div className="flex items-center justify-center gap-2">
              {/* Agent Name Badge */}
              {/* <div className="px-3 py-1.5 rounded-lg bg-purple-500/20 border border-purple-500/30 backdrop-blur-sm">
                                <h3 className="text-lg font-bold text-foreground">{agent.name}</h3>
                            </div> */}
              <span className="px-2 py-0.5 text-[10px] font-semibold rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
                CARD
              </span>
            </div>
            <p className="text-sm text-muted-foreground">{agent.role}</p>
          </div>
        </div>
      </div>
    </motion.div>
  )
}

interface AgentModalProps {
  agent: Agent
  onClose: () => void
}

function AgentModal({ agent, onClose }: AgentModalProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0, y: 20 }}
        animate={{ scale: 1, opacity: 1, y: 0 }}
        exit={{ scale: 0.9, opacity: 0, y: 20 }}
        transition={{ type: "spring", duration: 0.5 }}
        onClick={(e) => e.stopPropagation()}
        className="relative w-full max-w-md"
      >
        {/* Glassmorphism Modal */}
        <div className="relative rounded-3xl overflow-hidden">
          {/* Background with blur */}
          <div
            className="absolute inset-0 rounded-3xl"
            style={{
              background:
                "linear-gradient(135deg, rgba(139, 92, 246, 0.2) 0%, rgba(109, 40, 217, 0.15) 100%)",
              backdropFilter: "blur(20px)",
              WebkitBackdropFilter: "blur(20px)",
            }}
          />

          {/* Border */}
          <div className="absolute inset-0 rounded-3xl border border-purple-500/40" />

          {/* Gradient overlay */}
          <div className="absolute inset-0 bg-gradient-to-b from-purple-500/10 via-transparent to-transparent rounded-3xl" />

          {/* Watermark Agent Image - Positioned at bottom right */}
          <div className="absolute bottom-0 right-0 w-64 h-64 pointer-events-none overflow-hidden rounded-3xl">
            <img
              src={agent.image}
              alt=""
              className="w-full h-full object-contain opacity-[0.12] blur-[2px]"
              style={{
                transform: "translate(20%, 20%) scale(1.2)",
              }}
            />
          </div>

          {/* Content */}
          <div className="relative p-8">
            {/* Header with Service Badge */}
            <div className="flex items-center gap-3 mb-6">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500/30 to-purple-600/30 backdrop-blur-sm border border-purple-500/30 flex items-center justify-center">
                <Sparkles className="w-6 h-6 text-purple-300" />
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-purple-300">
                    VibeSDLC
                  </span>
                  <span className="px-2 py-0.5 text-xs rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30">
                    {agent.service}
                  </span>
                </div>
              </div>
              <motion.div
                animate={{ rotate: 360 }}
                transition={{
                  duration: 20,
                  repeat: Number.POSITIVE_INFINITY,
                  ease: "linear",
                }}
                className="w-8 h-8 rounded-full bg-purple-500/20 border border-purple-500/30 flex items-center justify-center"
              >
                <Sparkles className="w-4 h-4 text-purple-400" />
              </motion.div>
            </div>

            {/* Agent Name and Role */}
            <div className="mb-6">
              <h2 className="text-4xl font-bold text-foreground mb-2">
                {agent.name}
              </h2>
              <p className="text-lg text-purple-300">{agent.role}</p>
            </div>

            {/* Expertise Section */}
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-purple-300 mb-2 uppercase tracking-wider">
                Specialized expertise
              </h3>
              <p className="text-base text-foreground/90">
                {agent.description}
              </p>
            </div>

            {/* Professional Skills */}
            <div>
              <h3 className="text-sm font-semibold text-purple-300 mb-3 uppercase tracking-wider">
                Professional skills
              </h3>
              <ul className="space-y-2">
                {agent.skills.map((skill, index) => (
                  <motion.li
                    key={index}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.1 }}
                    className="text-sm text-foreground/80 flex items-start gap-2"
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-purple-400 mt-1.5 flex-shrink-0" />
                    <span>{skill}</span>
                  </motion.li>
                ))}
              </ul>
            </div>
          </div>
        </div>

        {/* Close hint */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="absolute -bottom-12 left-1/2 -translate-x-1/2 flex items-center gap-2 text-sm text-muted-foreground"
        >
          <div className="w-8 h-8 rounded-full bg-purple-500/10 border border-purple-500/20 flex items-center justify-center">
            <X className="w-4 h-4 text-purple-400" />
          </div>
          <span>Click outside to close</span>
        </motion.div>
      </motion.div>
    </motion.div>
  )
}
