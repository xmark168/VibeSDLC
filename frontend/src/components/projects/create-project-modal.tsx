import { motion } from "framer-motion"
import { Globe, Lock, X, Layers } from "lucide-react"
import { useId, useState } from "react"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { ProjectCreate, ProjectsService } from "@/client"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useAppStore } from "@/stores/auth-store"
import toast from "react-hot-toast"
import { withToast } from "@/utils"

interface CreateProjectModalProps {
  isOpen: boolean
  onClose: () => void
  setIsOpen: React.Dispatch<React.SetStateAction<boolean>>
}

const TECH_STACK_OPTIONS = [
  {
    value: "nodejs-react",
    label: "Node.js + Express + React Vite",
    icon: "/assets/images/icon/1.png",
    description: "Fast development with modern tooling",
    template_owner: "trong03",
    template_repo: "boilerplate-vibe-sdlc"
  }
]

export function CreateProjectModal({
  isOpen,
  onClose,
  setIsOpen,
}: CreateProjectModalProps) {
  const projectNameId = useId()
  const descriptionId = useId()
  const [projectName, setProjectName] = useState("")
  const [description, setDescription] = useState("")
  const [isPrivate, setIsPrivate] = useState(true)
  const [techStack, setTechStack] = useState("nodejs-react")
  const [isLoading, setIsLoading] = useState(false)
  const user = useAppStore((state) => state.user)
  const queryClient = useQueryClient()

  const createProjectMutation = useMutation({
    mutationFn: (data: ProjectCreate) =>
      ProjectsService.createProject({
        requestBody: data,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["list-project"] })
    },
  })

  // Validation function for project name
  const validateProjectName = (name: string): { isValid: boolean; error?: string } => {
    if (!name.trim()) {
      return { isValid: false, error: "Project name is required" }
    }

    if (name.length < 1 || name.length > 50) {
      return { isValid: false, error: "Project name must be between 1 and 50 characters" }
    }

    // Check if starts or ends with hyphen
    if (name.startsWith("-") || name.endsWith("-")) {
      return { isValid: false, error: "Project name cannot start or end with a hyphen" }
    }

    // Check for consecutive hyphens
    if (name.includes("--")) {
      return { isValid: false, error: "Project name cannot contain consecutive hyphens" }
    }

    // Check for valid characters (a-z, A-Z, 0-9, -, _)
    if (!/^[a-zA-Z0-9\-_]+$/.test(name)) {
      return { isValid: false, error: "Project name can only contain letters, numbers, hyphens, and underscores" }
    }

    return { isValid: true }
  }

  const handleCreate = async () => {
    // Validate project name
    const validation = validateProjectName(projectName)
    if (!validation.isValid) {
      toast.error(validation.error || "Invalid project name")
      return
    }

    setIsLoading(true)
    try {
      const dataProjectCreate: ProjectCreate = {
        name: projectName,
        is_private: isPrivate,
        tech_stack: techStack,
      }

      await withToast(
        createProjectMutation.mutateAsync(dataProjectCreate),
        {
          loading: "Creating project...",
          success: <b>Project created successfully!</b>,
          error: <b>Project creation failed. Please try again.</b>,
        },
      )
    } catch (error) {
      console.error("Error creating project:", error)
      toast.error("Failed to create project. Please try again.")
    } finally {
      setProjectName("")
      setDescription("")
      setTechStack("nodejs-react")
      setIsLoading(false)
      setIsOpen(false)
    }

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

  if (!isOpen) return null

  return (
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
        className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-2xl max-h-[90vh] overflow-y-auto z-50"
      >
        <div className="relative bg-card border border-border rounded-2xl p-8 shadow-[var(--shadow-lg)]">
          {/* Close Button */}
          <motion.button
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.95 }}
            onClick={onClose}
            disabled={isLoading}
            className="absolute top-4 right-4 p-2 rounded-lg hover:bg-accent transition-colors disabled:opacity-50"
          >
            <X className="h-5 w-5 text-muted-foreground hover:text-foreground transition-colors" />
          </motion.button>

          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-6"
          >
            <h2 className="text-2xl font-bold text-foreground mb-2">
              Create New Project
            </h2>
            <p className="text-sm text-muted-foreground">
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
              <Label htmlFor={projectNameId} className="text-foreground mb-2">
                Project Name
              </Label>
              <Input
                id={projectNameId}
                type="text"
                placeholder="Enter project name"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                disabled={isLoading}
                className="disabled:opacity-50"
              />
            </div>

            {/* Description Input */}
            <div>
              <Label htmlFor={descriptionId} className="text-foreground mb-2">
                Description
              </Label>
              <Textarea
                id={descriptionId}
                placeholder="Enter project description (optional)"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                disabled={isLoading}
                className="disabled:opacity-50 min-h-[80px]"
              />
            </div>

            {/* Privacy Toggle */}
            <div className="space-y-3">
              <Label className="text-foreground">Visibility</Label>

              <div className="grid grid-cols-2 gap-3">
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => setIsPrivate(true)}
                  disabled={isLoading}
                  className={`relative p-4 rounded-lg border-2 transition-all ${isPrivate
                    ? "border-primary bg-primary/10"
                    : "border-border bg-muted hover:border-primary/50"
                    } disabled:opacity-50`}
                >
                  <Lock
                    className={`h-5 w-5 mx-auto mb-2 ${isPrivate ? "text-primary" : "text-muted-foreground"}`}
                  />
                  <p
                    className={`text-sm font-semibold ${isPrivate ? "text-foreground" : "text-muted-foreground"}`}
                  >
                    Private
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Only you can access
                  </p>
                </motion.button>

                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => setIsPrivate(false)}
                  disabled={isLoading}
                  className={`relative p-4 rounded-lg border-2 transition-all ${!isPrivate
                    ? "border-primary bg-primary/10"
                    : "border-border bg-muted hover:border-primary/50"
                    } disabled:opacity-50`}
                >
                  <Globe
                    className={`h-5 w-5 mx-auto mb-2 ${!isPrivate ? "text-primary" : "text-muted-foreground"}`}
                  />
                  <p
                    className={`text-sm font-semibold ${!isPrivate ? "text-foreground" : "text-muted-foreground"}`}
                  >
                    Public
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Everyone can see
                  </p>
                </motion.button>
              </div>
            </div>

            {/* Tech Stack Selection */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Layers className="h-4 w-4 text-primary" />
                <Label className="text-foreground">Tech Stack</Label>
              </div>
              <RadioGroup value={techStack} onValueChange={setTechStack} disabled={isLoading}>
                <div className="space-y-3">
                  {TECH_STACK_OPTIONS.map((option) => (
                    <motion.div
                      key={option.value}
                      whileHover={{ scale: 1.01 }}
                      className={`flex items-center space-x-3 p-4 rounded-lg border transition-all ${techStack === option.value
                        ? "border-primary bg-primary/5"
                        : "border-border hover:border-primary/50"
                        }`}
                    >
                      <RadioGroupItem value={option.value} id={option.value} />
                      <Label
                        htmlFor={option.value}
                        className="cursor-pointer flex-1"
                      >
                        <div className="flex items-center gap-2 mb-1">
                          <img
                            src={option.icon}
                            alt={option.label}
                            className="h-6 w-6"
                          />
                          <span className="text-sm font-semibold">{option.label}</span>
                        </div>
                        <p className="text-xs text-muted-foreground">{option.description}</p>
                      </Label>
                    </motion.div>
                  ))}
                </div>
              </RadioGroup>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3 pt-4">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={onClose}
                disabled={isLoading}
                className="flex-1 px-4 py-3 rounded-lg border border-border text-foreground font-semibold hover:bg-accent transition-colors disabled:opacity-50"
              >
                Cancel
              </motion.button>
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={handleCreate}
                disabled={!projectName.trim() || isLoading}
                className="flex-1 px-4 py-3 rounded-lg bg-primary text-primary-foreground font-semibold hover:bg-primary/90 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? "Creating..." : "Create Project"}
              </motion.button>
            </div>
          </motion.div>
        </div>
      </motion.div>
    </>
  )
}
