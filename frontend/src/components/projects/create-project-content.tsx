import { motion } from "framer-motion"
import { GitBranch, Github, Zap } from "lucide-react"
import { Button } from "@/components/ui/button"

interface CreateProjectContentProps {
  onInstallGitHub: () => void
  githubLinked: boolean
}

export function CreateProjectContent({
  onInstallGitHub,
  githubLinked,
}: CreateProjectContentProps) {
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
            Connect your GitHub repository and let our AI agents collaborate on
            your project. Get instant code reviews, automated testing, and smart
            project management.
          </p>
        </motion.div>

        {/* GitHub Setup Card */}
        <motion.div variants={itemVariants} className="relative">
          <div className="relative bg-card backdrop-blur-xl border border-primary/30 rounded-2xl p-8 md:p-12 hover:border-primary/50 transition-colors duration-300 shadow-[var(--shadow-md)]">
            <div className="flex items-start gap-4 mb-8">
              <motion.div
                whileHover={{ scale: 1.1, rotate: 5 }}
                whileTap={{ scale: 0.95 }}
                className="h-14 w-14 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0"
              >
                <Github className="h-7 w-7 text-primary" />
              </motion.div>

              <div>
                <h2 className="text-3xl font-bold text-foreground mb-2">
                  Connect GitHub
                </h2>
                <p className="text-muted-foreground text-sm">
                  Install our GitHub app to unlock AI-powered collaboration
                </p>
              </div>
            </div>

            <div className="mb-8">
              <div className="flex items-center gap-3 mb-6">
                <motion.div
                  whileHover={{ scale: 1.1 }}
                  className="h-10 w-10 rounded-full bg-[var(--gradient-primary)] flex items-center justify-center shadow-[var(--shadow-hover)]"
                >
                  <span className="text-primary-foreground font-bold">1</span>
                </motion.div>
                <h3 className="text-xl font-bold text-foreground">
                  Install GitHub App
                </h3>
              </div>
              <p className="text-muted-foreground ml-16 mb-8 text-sm leading-relaxed">
                Click the button below to install our GitHub app on your account
                or organization. This gives us permission to analyze your
                repositories and provide intelligent code reviews.
              </p>
              <motion.div
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="ml-16"
              >
                <Button
                  onClick={onInstallGitHub}
                  disabled={githubLinked}
                  size="lg"
                  className="gap-2 px-8"
                >
                  <Github className="h-5 w-5" />
                  {githubLinked ? "GitHub Connected ✓" : "Install GitHub App"}
                </Button>
              </motion.div>
            </div>

            {githubLinked && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="border-t border-border pt-8"
              >
                <div className="flex items-center gap-3 mb-6">
                  <motion.div
                    whileHover={{ scale: 1.1 }}
                    className="h-10 w-10 rounded-full bg-[var(--gradient-primary)] flex items-center justify-center border border-primary/50 shadow-[var(--shadow-hover)]"
                  >
                    <span className="text-primary-foreground font-bold">2</span>
                  </motion.div>
                  <h3 className="text-xl font-bold text-foreground">
                    Create Project
                  </h3>
                </div>
                <p className="text-muted-foreground ml-16 mb-8 text-sm leading-relaxed">
                  Set up your project name and choose whether it's private or
                  public for your AI team to start collaborating.
                </p>
              </motion.div>
            )}
          </div>
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
              icon: Github,
              title: "Full Integration",
              desc: "Seamless GitHub workflow integration",
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
