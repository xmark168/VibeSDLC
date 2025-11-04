"use client"

import { AnimatePresence, motion } from "framer-motion"
import { ArrowRight, CheckCircle2, Github, Loader2, X } from "lucide-react"
import { useState } from "react"
import { Button } from "@/components/ui/button"

interface GitHubLinkModalProps {
  onClose: () => void
  onLinked: (installationId?: number | null) => Promise<void>
  installationId?: number | null
  isSuccess?: boolean
}

export function GitHubLinkModal({
  onClose,
  onLinked,
  isSuccess = false,
}: GitHubLinkModalProps) {
  const [isLoading, setIsLoading] = useState(false)

  const handleLink = async () => {
    setIsLoading(true)
    try {
      await onLinked()
    } finally {
      setIsLoading(false)
    }
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

  const contentVariants = {
    hidden: { opacity: 0, y: 10 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.3 } },
    exit: { opacity: 0, y: -10, transition: { duration: 0.2 } },
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.3 }}
        onClick={() => (isSuccess ? null : onClose())}
        className="absolute inset-0 bg-black/60 backdrop-blur-md"
      />

      <motion.div
        variants={modalVariants}
        initial="hidden"
        animate="visible"
        exit="exit"
        className="relative max-w-md w-full bg-gradient-to-br from-slate-900 via-slate-850 to-slate-900 border border-white/10 rounded-2xl shadow-2xl overflow-hidden"
      >
        {!isSuccess && (
          <motion.button
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.95 }}
            onClick={onClose}
            disabled={isLoading}
            className="absolute top-4 right-4 z-10 h-8 w-8 rounded-lg bg-white/10 hover:bg-white/20 flex items-center justify-center text-white/60 hover:text-white transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <X className="h-4 w-4" />
          </motion.button>
        )}

        {/* Content */}
        <div className="relative p-8">
          <AnimatePresence mode="wait">
            {!isSuccess && (
              <motion.div
                key="linking"
                variants={contentVariants}
                initial="hidden"
                animate="visible"
                exit="exit"
              >
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{
                    duration: 2,
                    repeat: Number.POSITIVE_INFINITY,
                    ease: "linear" as const,
                  }}
                  className="mb-8 flex justify-center"
                >
                  <div className="h-16 w-16 rounded-full bg-gradient-to-br from-purple-400 to-purple-600 flex items-center justify-center">
                    <Github className="h-8 w-8 text-white" />
                  </div>
                </motion.div>

                <h2 className="text-2xl font-bold text-white text-center mb-3">
                  Link GitHub Account
                </h2>
                <p className="text-slate-400 text-center text-sm mb-8">
                  GitHub App has been installed successfully. Link it with your
                  VibeSDLC account to get started.
                </p>

                <motion.div className="space-y-3 mb-8">
                  {[
                    { label: "Access your repositories", delay: 0 },
                    { label: "Collaborate with AI agents", delay: 0.2 },
                    { label: "Automate your workflow", delay: 0.4 },
                  ].map((item, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: item.delay }}
                      className="flex items-center gap-3"
                    >
                      <CheckCircle2 className="h-4 w-4 text-purple-400 flex-shrink-0" />
                      <span className="text-sm text-slate-300">
                        {item.label}
                      </span>
                    </motion.div>
                  ))}
                </motion.div>

                <div className="flex gap-3">
                  <Button
                    onClick={onClose}
                    variant="outline"
                    disabled={isLoading}
                    className="flex-1 border-white/10 text-white hover:bg-white/5 disabled:opacity-50 transition-colors bg-transparent"
                  >
                    Later
                  </Button>
                  <motion.div
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    className="flex-1"
                  >
                    <Button
                      onClick={handleLink}
                      disabled={isLoading}
                      className="w-full bg-gradient-to-r from-purple-500 to-purple-600 hover:from-purple-600 hover:to-purple-700 text-white font-semibold gap-2 disabled:opacity-50 transition-all duration-200"
                    >
                      {isLoading ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin" />
                          Linking...
                        </>
                      ) : (
                        <>
                          Link Now
                          <ArrowRight className="h-4 w-4" />
                        </>
                      )}
                    </Button>
                  </motion.div>
                </div>
              </motion.div>
            )}

            {isSuccess && (
              <motion.div
                key="success"
                variants={contentVariants}
                initial="hidden"
                animate="visible"
                exit="exit"
                className="text-center"
              >
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: "spring", stiffness: 200, damping: 15 }}
                  className="mb-8 flex justify-center"
                >
                  <motion.div
                    className="h-16 w-16 rounded-full bg-gradient-to-br from-emerald-400 to-green-600 flex items-center justify-center"
                    animate={{
                      scale: [1, 1.05, 1],
                    }}
                    transition={{
                      duration: 1.5,
                      repeat: Number.POSITIVE_INFINITY,
                    }}
                  >
                    <CheckCircle2 className="h-8 w-8 text-white" />
                  </motion.div>
                </motion.div>

                <h2 className="text-2xl font-bold text-white mb-3">
                  Account Linked!
                </h2>
                <p className="text-slate-400 text-sm leading-relaxed">
                  Your GitHub account is successfully linked. Your AI team is
                  ready to help you build amazing projects.
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    </div>
  )
}
