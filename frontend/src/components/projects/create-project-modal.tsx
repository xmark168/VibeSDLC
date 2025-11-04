import { AnimatePresence, motion } from "framer-motion"
import { Globe, Lock, X } from "lucide-react"
import { useId, useState } from "react"
import { Input } from "@/components/ui/input"

interface CreateProjectModalProps {
  isOpen: boolean
  onClose: () => void
  onCreateProject: (name: string, isPrivate: boolean) => void
}

export function CreateProjectModal({
  isOpen,
  onClose,
  onCreateProject,
}: CreateProjectModalProps) {
  const projectNameId = useId()
  const [projectName, setProjectName] = useState("")
  const [isPrivate, setIsPrivate] = useState(true)
  const [isLoading, setIsLoading] = useState(false)

  const handleCreate = async () => {
    if (!projectName.trim()) return

    setIsLoading(true)
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 800))
    onCreateProject(projectName, isPrivate)
    setProjectName("")
    setIsLoading(false)
  }

  const modalVariants = {
    hidden: { opacity: 0, scale: 0.95 },
    visible: {
      opacity: 1,
      scale: 1,
      transition: { duration: 0.3, ease: "easeOut" as const },
    },
    exit: {
      opacity: 0,
      scale: 0.95,
      transition: { duration: 0.2 },
    },
  }

  const backdropVariants = {
    hidden: { opacity: 0 },
    visible: { opacity: 1 },
    exit: { opacity: 0 },
  }

  return (
    // <AnimatePresence>
    <div>
      {isOpen && (
        <>
          <motion.div
            variants={backdropVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            onClick={onClose}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50"
          />

          <motion.div
            variants={modalVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-md z-50"
          >
            <div className="relative bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-purple-500/30 rounded-2xl p-8 shadow-2xl">
              {/* Close Button */}
              <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.95 }}
                onClick={onClose}
                disabled={isLoading}
                className="absolute top-4 right-4 p-2 rounded-lg hover:bg-white/10 transition-colors disabled:opacity-50"
              >
                <X className="h-5 w-5 text-slate-400 hover:text-white transition-colors" />
              </motion.button>

              {/* Header */}
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mb-6"
              >
                <h2 className="text-2xl font-bold text-white mb-2">
                  Create New Project
                </h2>
                <p className="text-sm text-slate-400">
                  Set up your project with AI agents
                </p>
              </motion.div>

              {/* Form */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.1 }}
                className="space-y-6"
              >
                {/* Project Name Input */}
                <div>
                  <label
                    htmlFor={projectNameId}
                    className="block text-sm font-semibold text-white mb-2"
                  >
                    Project Name
                  </label>
                  <Input
                    id={projectNameId}
                    type="text"
                    placeholder="Enter project name"
                    value={projectName}
                    onChange={(e) => setProjectName(e.target.value)}
                    disabled={isLoading}
                    className="bg-slate-800/50 border-purple-500/30 text-white placeholder:text-slate-500 focus:border-purple-500/50 disabled:opacity-50"
                  />
                </div>

                {/* Privacy Toggle */}
                <div className="space-y-3">
                  <span className="block text-sm font-semibold text-white">
                    Visibility
                  </span>

                  <div className="grid grid-cols-2 gap-3">
                    {/* Private Option */}
                    <motion.button
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={() => setIsPrivate(true)}
                      disabled={isLoading}
                      className={`relative p-4 rounded-lg border-2 transition-all ${isPrivate
                          ? "border-purple-500/50 bg-purple-500/10"
                          : "border-slate-700 bg-slate-800/30 hover:border-slate-600"
                        } disabled:opacity-50`}
                    >
                      <Lock
                        className={`h-5 w-5 mx-auto mb-2 ${isPrivate ? "text-purple-400" : "text-slate-400"}`}
                      />
                      <p
                        className={`text-sm font-semibold ${isPrivate ? "text-white" : "text-slate-400"}`}
                      >
                        Private
                      </p>
                      <p className="text-xs text-slate-500 mt-1">
                        Only you can access
                      </p>
                    </motion.button>

                    {/* Public Option */}
                    <motion.button
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={() => setIsPrivate(false)}
                      disabled={isLoading}
                      className={`relative p-4 rounded-lg border-2 transition-all ${!isPrivate
                          ? "border-purple-500/50 bg-purple-500/10"
                          : "border-slate-700 bg-slate-800/30 hover:border-slate-600"
                        } disabled:opacity-50`}
                    >
                      <Globe
                        className={`h-5 w-5 mx-auto mb-2 ${!isPrivate ? "text-purple-400" : "text-slate-400"}`}
                      />
                      <p
                        className={`text-sm font-semibold ${!isPrivate ? "text-white" : "text-slate-400"}`}
                      >
                        Public
                      </p>
                      <p className="text-xs text-slate-500 mt-1">
                        Everyone can see
                      </p>
                    </motion.button>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex gap-3 pt-4">
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={onClose}
                    disabled={isLoading}
                    className="flex-1 px-4 py-3 rounded-lg border border-slate-700 text-white font-semibold hover:border-slate-600 transition-colors disabled:opacity-50"
                  >
                    Cancel
                  </motion.button>
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={handleCreate}
                    disabled={!projectName.trim() || isLoading}
                    className="flex-1 px-4 py-3 rounded-lg bg-gradient-to-r from-purple-500 to-purple-600 hover:from-purple-600 hover:to-purple-700 text-white font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isLoading ? "Creating..." : "Create Project"}
                  </motion.button>
                </div>
              </motion.div>
            </div>
          </motion.div>
        </>
      )}
    </div>
    // </AnimatePresence>
  )
}
