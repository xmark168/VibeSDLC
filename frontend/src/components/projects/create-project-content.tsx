import { motion } from "framer-motion"
import { Bot, GitBranch, Zap } from "lucide-react"

type CreateProjectContentProps = {}

export function CreateProjectContent({}: CreateProjectContentProps) {
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.08,
        delayChildren: 0.2,
      },
    },
  }

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.5, ease: "easeOut" as const },
    },
  }

  return (
    <div className="min-h-screen pt-10 pb-20 px-6">
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="mx-auto max-w-3xl"
      >
        {/* Header Section */}
        <motion.div variants={itemVariants} className="text-center mb-16">
          <h1 className="text-5xl font-bold text-foreground mb-4">
            Create a New{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-purple-600">
              {" "}
              Project{" "}
            </span>
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto leading-relaxed">
            Let our AI agents collaborate on your project. Get instant code
            reviews, automated testing, and smart project management.
          </p>
        </motion.div>

        {/* Features Grid */}
        <motion.div
          variants={itemVariants}
          className="grid md:grid-cols-3 gap-6 mt-12"
        >
          {[
            {
              icon: Zap,
              title: "Instant Reviews",
              desc: "Get AI-powered code reviews instantly",
            },
            {
              icon: GitBranch,
              title: "Smart Branching",
              desc: "Automatic branch creation and management",
            },
            {
              icon: Bot,
              title: "AI Agents",
              desc: "Intelligent automation for your project",
            },
          ].map((feature, i) => (
            <motion.div
              key={i}
              whileHover={{ y: -6 }}
              transition={{ duration: 0.2 }}
              className="group"
            >
              <div className="relative bg-card backdrop-blur-xl border border-border rounded-xl p-6 hover:border-primary/30 hover:shadow-[var(--shadow-hover)] transition-all duration-300 h-full">
                <feature.icon className="h-8 w-8 text-primary mb-3" />
                <h3 className="text-foreground font-semibold mb-2">
                  {feature.title}
                </h3>
                <p className="text-sm text-muted-foreground">{feature.desc}</p>
              </div>
            </motion.div>
          ))}
        </motion.div>
      </motion.div>
    </div>
  )
}
