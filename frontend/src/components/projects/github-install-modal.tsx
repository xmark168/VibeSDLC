"use client"

import { motion } from "framer-motion"
import { ArrowRight, CheckCircle2, Github, X } from "lucide-react"
import { useState } from "react"
import { Button } from "@/components/ui/button"

interface GitHubInstallModalProps {
  onClose: () => void
  onInstall: () => void
  onOpen: () => void
}

export function GitHubInstallModal({
  onClose,
  onOpen,
  onInstall,
}: GitHubInstallModalProps) {
  const [isInstalling, _setIsInstalling] = useState(false)

  const handleInstallClick = () => {
    const appName = import.meta.env.VITE_GITHUB_APP_NAME || "vibesdlc"
    const githubAuthUrl = `https://github.com/apps/${appName}/installations/new`
    window.location.href = githubAuthUrl
  }

  const modalVariants = {
    hidden: { opacity: 0, scale: 0.95, y: 20 },
    visible: {
      opacity: 1,
      scale: 1,
      y: 0,
      transition: { duration: 0.4, ease: "easeOut" as const },
    },
    exit: {
      opacity: 0,
      scale: 0.95,
      y: 20,
      transition: { duration: 0.2 },
    },
  }

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        delayChildren: 0.2,
      },
    },
  }

  const itemVariants = {
    hidden: { opacity: 0, x: -10 },
    visible: {
      opacity: 1,
      x: 0,
      transition: { duration: 0.3 },
    },
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.3 }}
        onClick={onClose}
        className="absolute inset-0 bg-black/60 backdrop-blur-md"
      />

      <motion.div
        variants={modalVariants}
        initial="hidden"
        animate="visible"
        exit="exit"
        className="relative max-w-md w-full bg-gradient-to-br from-slate-900 via-slate-850 to-slate-900 border border-purple-500/20 rounded-2xl shadow-2xl overflow-hidden"
      >
        {/* Glow effect */}
        <div className="absolute inset-0 bg-gradient-to-br from-purple-500/5 to-purple-600/5 pointer-events-none" />

        {/* Close Button */}
        <motion.button
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.95 }}
          onClick={onClose}
          disabled={isInstalling}
          className="absolute top-4 right-4 z-10 h-8 w-8 rounded-lg bg-white/10 hover:bg-white/20 flex items-center justify-center text-white/60 hover:text-white transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <X className="h-4 w-4" />
        </motion.button>

        {/* Content */}
        <div className="relative p-8">
          <motion.div
            animate={{ y: [0, -12, 0] }}
            transition={{
              duration: 3,
              repeat: Number.POSITIVE_INFINITY,
              ease: "easeInOut" as const,
            }}
            className="mb-8"
          >
            <div className="h-16 w-16 rounded-full bg-gradient-to-br from-purple-400 to-purple-600 flex items-center justify-center mx-auto shadow-lg">
              <Github className="h-8 w-8 text-white" />
            </div>
          </motion.div>

          <h2 className="text-2xl font-bold text-white text-center mb-3">
            Install GitHub App
          </h2>
          <p className="text-slate-400 text-center text-sm mb-8 leading-relaxed">
            This will open GitHub to install our app on your account. You can
            install it for personal or organization use.
          </p>

          <motion.div
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            className="space-y-3 mb-8"
          >
            {[
              "Read repository information",
              "Create and manage branches",
              "Add pull request comments",
              "Trigger automated workflows",
            ].map((feature, i) => (
              <motion.div
                key={i}
                variants={itemVariants}
                className="flex items-center gap-3 text-sm text-slate-300"
              >
                <motion.div
                  whileHover={{ scale: 1.2 }}
                  className="h-5 w-5 rounded-full bg-purple-500/20 flex items-center justify-center flex-shrink-0 border border-purple-500/30"
                >
                  <CheckCircle2 className="h-3 w-3 text-purple-400" />
                </motion.div>
                <span>{feature}</span>
              </motion.div>
            ))}
          </motion.div>

          <div className="space-y-3">
            <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
              <Button
                onClick={handleInstallClick}
                disabled={isInstalling}
                className="w-full bg-gradient-to-r from-purple-500 to-purple-600 hover:from-purple-600 hover:to-purple-700 text-white font-semibold gap-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
              >
                <Github className="h-5 w-5" />
                {isInstalling ? "Opening GitHub..." : "Continue to GitHub"}
                {!isInstalling && <ArrowRight className="h-4 w-4" />}
              </Button>
            </motion.div>

            <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
              <Button
                onClick={onClose}
                disabled={isInstalling}
                variant="outline"
                className="w-full border-white/10 text-white hover:bg-white/5 disabled:opacity-50 disabled:cursor-not-allowed bg-transparent transition-all duration-200"
              >
                Cancel
              </Button>
            </motion.div>
          </div>
        </div>
      </motion.div>
    </div>
  )
}
