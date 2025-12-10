import { motion } from "framer-motion"
import { Globe, X, Layers, Users, Search, Check, ChevronDown, Shuffle, Settings } from "lucide-react"
import { useId, useState, useMemo, useEffect } from "react"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { ProjectCreate, ProjectsService } from "@/client"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useAppStore } from "@/stores/auth-store"
import toast from "react-hot-toast"
import { withToast } from "@/utils"
import { usePersonasByRole } from "@/queries/personas"
import { useStacks } from "@/queries/stacks"
import { cn } from "@/lib/utils"
import type { PersonaTemplate, RoleType } from "@/types/persona"
import type { TechStack } from "@/types/stack"

interface CreateProjectModalProps {
  isOpen: boolean
  onClose: () => void
  setIsOpen: React.Dispatch<React.SetStateAction<boolean>>
}

const TECH_STACK_CATEGORIES = ["All", "Full Stack", "Frontend", "Backend", "Mobile", "Desktop"]

const AGENT_ROLES: { role: RoleType; label: string; description: string; icon: string }[] = [
  {
    role: "team_leader",
    label: "Team Leader",
    description: "Manages project workflow and coordinates team",
    icon: "👨‍💼"
  },
  {
    role: "developer",
    label: "Developer",
    description: "Implements features and writes code",
    icon: "👨‍💻"
  },
  {
    role: "business_analyst",
    label: "Business Analyst",
    description: "Analyzes requirements and creates documentation",
    icon: "📊"
  },
  {
    role: "tester",
    label: "Tester",
    description: "Creates test plans and ensures quality",
    icon: "🧪"
  },
]

interface AgentSelection {
  role: RoleType
  personaId: string | null
}

function PersonaSelector({
  role,
  selectedPersonaId,
  onSelect,
  disabled,
}: {
  role: RoleType
  selectedPersonaId: string | null
  onSelect: (personaId: string | null) => void
  disabled?: boolean
}) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState("")
  const { data: personas = [], isLoading } = usePersonasByRole(role)

  const filteredPersonas = useMemo(() => {
    if (!search) return personas
    return personas.filter(p =>
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.communication_style?.toLowerCase().includes(search.toLowerCase())
    )
  }, [personas, search])

  const selectedPersona = personas.find(p => p.id === selectedPersonaId)

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          disabled={disabled || isLoading}
          className="w-full justify-between h-auto min-h-[40px] py-2"
        >
          {selectedPersona ? (
            <div className="flex flex-col items-start text-left">
              <span className="font-medium">{selectedPersona.name}</span>
              <span className="text-xs text-muted-foreground truncate max-w-[200px]">
                {selectedPersona.communication_style}
              </span>
            </div>
          ) : (
            <span className="text-muted-foreground">
              {isLoading ? "Loading..." : "Select persona..."}
            </span>
          )}
          <ChevronDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[300px] p-0" align="start">
        <Command shouldFilter={false}>
          <CommandInput
            placeholder="Search persona..."
            value={search}
            onValueChange={setSearch}
          />
          <CommandList>
            <CommandEmpty>No persona found.</CommandEmpty>
            <CommandGroup>
              <ScrollArea className="h-[200px]">
                {filteredPersonas.map((persona) => (
                  <CommandItem
                    key={persona.id}
                    value={persona.id}
                    onSelect={() => {
                      onSelect(persona.id === selectedPersonaId ? null : persona.id)
                      setOpen(false)
                    }}
                    className="flex flex-col items-start py-2 cursor-pointer"
                  >
                    <div className="flex items-center w-full">
                      <Check
                        className={cn(
                          "mr-2 h-4 w-4",
                          selectedPersonaId === persona.id ? "opacity-100" : "opacity-0"
                        )}
                      />
                      <div className="flex-1">
                        <div className="font-medium">{persona.name}</div>
                        <div className="text-xs text-muted-foreground line-clamp-1">
                          {persona.communication_style}
                        </div>
                        {persona.personality_traits?.length > 0 && (
                          <div className="flex gap-1 mt-1 flex-wrap">
                            {persona.personality_traits.slice(0, 3).map((trait, i) => (
                              <Badge key={i} variant="secondary" className="text-[10px] px-1 py-0">
                                {trait}
                              </Badge>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </CommandItem>
                ))}
              </ScrollArea>
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}

export function CreateProjectModal({
  isOpen,
  onClose,
  setIsOpen,
}: CreateProjectModalProps) {
  const projectNameId = useId()
  const descriptionId = useId()
  const [activeTab, setActiveTab] = useState("info")
  const [projectName, setProjectName] = useState("")
  const [description, setDescription] = useState("")
  const [agentMode, setAgentMode] = useState<"random" | "custom">("random")
  const [techStack, setTechStack] = useState("")
  const [techStackSearch, setTechStackSearch] = useState("")
  const [techStackCategory, setTechStackCategory] = useState("All")
  const [isLoading, setIsLoading] = useState(false)
  const [agentSelections, setAgentSelections] = useState<AgentSelection[]>(
    AGENT_ROLES.map(r => ({ role: r.role, personaId: null }))
  )

  const user = useAppStore((state) => state.user)
  const queryClient = useQueryClient()
  
  // Fetch tech stacks from database
  const { data: stacksData, isLoading: stacksLoading } = useStacks({ is_active: true })
  const techStacks = stacksData?.data || []

  // Auto-select first stack when loaded
  useEffect(() => {
    if (techStacks.length > 0 && !techStack) {
      setTechStack(techStacks[0].code)
    }
  }, [techStacks, techStack])

  const filteredTechStacks = useMemo(() => {
    return techStacks.filter(stack => {
      const matchesSearch = !techStackSearch ||
        stack.name.toLowerCase().includes(techStackSearch.toLowerCase()) ||
        stack.description?.toLowerCase().includes(techStackSearch.toLowerCase())
      const matchesCategory = techStackCategory === "All" || 
        stack.stack_config?.category === techStackCategory
      return matchesSearch && matchesCategory
    })
  }, [techStacks, techStackSearch, techStackCategory])

  const selectedTechStack = techStacks.find(s => s.code === techStack)

  const createProjectMutation = useMutation({
    mutationFn: (data: ProjectCreate) =>
      ProjectsService.createProject({
        requestBody: data,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["list-project"] })
    },
  })

  const validateProjectName = (name: string): { isValid: boolean; error?: string } => {
    if (!name.trim()) {
      return { isValid: false, error: "Project name is required" }
    }
    if (name.length < 1 || name.length > 50) {
      return { isValid: false, error: "Project name must be between 1 and 50 characters" }
    }
    if (name.startsWith("-") || name.endsWith("-")) {
      return { isValid: false, error: "Project name cannot start or end with a hyphen" }
    }
    if (name.includes("--")) {
      return { isValid: false, error: "Project name cannot contain consecutive hyphens" }
    }
    if (!/^[a-zA-Z0-9\-_]+$/.test(name)) {
      return { isValid: false, error: "Project name can only contain letters, numbers, hyphens, and underscores" }
    }
    return { isValid: true }
  }

  const handleAgentPersonaChange = (role: RoleType, personaId: string | null) => {
    setAgentSelections(prev =>
      prev.map(a => a.role === role ? { ...a, personaId } : a)
    )
  }

  const handleCreate = async () => {
    const validation = validateProjectName(projectName)
    if (!validation.isValid) {
      toast.error(validation.error || "Invalid project name")
      return
    }

    if (!techStack) {
      toast.error("Please select a tech stack")
      setActiveTab("tech")
      return
    }

    setIsLoading(true)
    try {
      const dataProjectCreate: ProjectCreate = {
        name: projectName,
        tech_stack: techStack ? [techStack] : null,
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
      resetForm()
      setIsOpen(false)
    }
  }

  const resetForm = () => {
    setProjectName("")
    setDescription("")
    setTechStack("")
    setTechStackSearch("")
    setTechStackCategory("All")
    setActiveTab("info")
    setAgentMode("random")
    setAgentSelections(AGENT_ROLES.map(r => ({ role: r.role, personaId: null })))
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
        className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-3xl max-h-[90vh] overflow-y-auto z-50"
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

          {/* Tabs */}
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <TabsList className="grid w-full grid-cols-2 mb-6">
              <TabsTrigger value="info" className="flex items-center gap-2">
                <Globe className="h-4 w-4" />
                Project Info
              </TabsTrigger>
              <TabsTrigger value="tech" className="flex items-center gap-2">
                <Layers className="h-4 w-4" />
                Tech Stack
              </TabsTrigger>
            </TabsList>

            {/* Project Info Tab */}
            <TabsContent value="info" className="space-y-6">
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

              {/* Agent Mode Toggle */}
              <div className="space-y-3">
                <Label className="text-foreground">Agents</Label>
                <div className="grid grid-cols-2 gap-3">
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => setAgentMode("random")}
                    disabled={isLoading}
                    className={`relative p-4 rounded-lg border-2 transition-all ${agentMode === "random"
                      ? "border-primary bg-primary/10"
                      : "border-border bg-muted hover:border-primary/50"
                      } disabled:opacity-50`}
                  >
                    <Shuffle
                      className={`h-5 w-5 mx-auto mb-2 ${agentMode === "random" ? "text-primary" : "text-muted-foreground"}`}
                    />
                    <p className={`text-sm font-semibold ${agentMode === "random" ? "text-foreground" : "text-muted-foreground"}`}>
                      Random
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Auto assign personas
                    </p>
                  </motion.button>

                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => setAgentMode("custom")}
                    disabled={isLoading}
                    className={`relative p-4 rounded-lg border-2 transition-all ${agentMode === "custom"
                      ? "border-primary bg-primary/10"
                      : "border-border bg-muted hover:border-primary/50"
                      } disabled:opacity-50`}
                  >
                    <Settings
                      className={`h-5 w-5 mx-auto mb-2 ${agentMode === "custom" ? "text-primary" : "text-muted-foreground"}`}
                    />
                    <p className={`text-sm font-semibold ${agentMode === "custom" ? "text-foreground" : "text-muted-foreground"}`}>
                      Custom
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Choose personas manually
                    </p>
                  </motion.button>
                </div>
              </div>

              {/* Custom Agent Persona Selection */}
              {agentMode === "custom" && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="space-y-4"
                >
                  <div className="text-sm text-muted-foreground">
                    Select persona for each agent role.
                  </div>
                  <div className="grid gap-3">
                    {AGENT_ROLES.map((agentRole) => {
                      const selection = agentSelections.find(a => a.role === agentRole.role)
                      return (
                        <div
                          key={agentRole.role}
                          className="p-3 rounded-lg border border-border bg-card"
                        >
                          <div className="flex items-center gap-3">
                            <div className="text-2xl">{agentRole.icon}</div>
                            <div className="flex-1">
                              <h4 className="font-medium text-sm">{agentRole.label}</h4>
                              <p className="text-xs text-muted-foreground">
                                {agentRole.description}
                              </p>
                            </div>
                            <div className="w-48">
                              <PersonaSelector
                                role={agentRole.role}
                                selectedPersonaId={selection?.personaId || null}
                                onSelect={(personaId) => handleAgentPersonaChange(agentRole.role, personaId)}
                                disabled={isLoading}
                              />
                            </div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </motion.div>
              )}
            </TabsContent>

            {/* Tech Stack Tab */}
            <TabsContent value="tech" className="space-y-4">
              {/* Search & Filter */}
              <div className="flex gap-3">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search tech stack..."
                    value={techStackSearch}
                    onChange={(e) => setTechStackSearch(e.target.value)}
                    className="pl-9"
                    disabled={isLoading}
                  />
                </div>
              </div>

              {/* Category Filter */}
              <div className="flex gap-2 flex-wrap">
                {TECH_STACK_CATEGORIES.map((category) => (
                  <Button
                    key={category}
                    variant={techStackCategory === category ? "default" : "outline"}
                    size="sm"
                    onClick={() => setTechStackCategory(category)}
                    disabled={isLoading}
                  >
                    {category}
                  </Button>
                ))}
              </div>

              {/* Tech Stack List */}
              <ScrollArea className="h-[280px] pr-4">
                <div className="space-y-3">
                  {stacksLoading ? (
                    <div className="text-center py-8 text-muted-foreground">
                      Loading tech stacks...
                    </div>
                  ) : filteredTechStacks.length === 0 ? (
                    <div className="text-center py-8 text-muted-foreground">
                      No tech stack found matching your criteria
                    </div>
                  ) : (
                    filteredTechStacks.map((stack) => (
                      <motion.div
                        key={stack.code}
                        whileHover={{ scale: 1.01 }}
                        onClick={() => !isLoading && setTechStack(stack.code)}
                        className={`flex items-center gap-4 p-4 rounded-lg border-2 cursor-pointer transition-all ${techStack === stack.code
                          ? "border-primary bg-primary/5"
                          : "border-border hover:border-primary/50"
                          } ${isLoading ? "opacity-50 cursor-not-allowed" : ""}`}
                      >
                        {stack.image ? (
                          <img
                            src={stack.image}
                            alt={stack.name}
                            className="h-10 w-10 rounded-lg object-cover"
                          />
                        ) : (
                          <div className="h-10 w-10 rounded-lg bg-muted flex items-center justify-center">
                            <Layers className="h-5 w-5 text-muted-foreground" />
                          </div>
                        )}
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-semibold">{stack.name}</span>
                            {stack.stack_config?.category && (
                              <Badge variant="secondary" className="text-xs">
                                {stack.stack_config.category}
                              </Badge>
                            )}
                          </div>
                          <p className="text-sm text-muted-foreground mb-2">{stack.description || "No description"}</p>
                          {stack.stack_config && Object.keys(stack.stack_config).length > 0 && (
                            <div className="flex flex-wrap gap-1">
                              {Object.entries(stack.stack_config)
                                .filter(([key]) => key !== "category")
                                .map(([key, value]) => (
                                  <Badge key={key} variant="outline" className="text-[10px] px-1.5 py-0">
                                    {key}: {value}
                                  </Badge>
                                ))}
                            </div>
                          )}
                        </div>
                        {techStack === stack.code && (
                          <Check className="h-5 w-5 text-primary" />
                        )}
                      </motion.div>
                    ))
                  )}
                </div>
              </ScrollArea>

              {/* Selected Tech Stack Summary */}
              {selectedTechStack && (
                <div className="p-3 bg-muted rounded-lg">
                  <p className="text-sm">
                    <span className="text-muted-foreground">Selected: </span>
                    <span className="font-medium">{selectedTechStack.name}</span>
                  </p>
                </div>
              )}
            </TabsContent>

          </Tabs>

          {/* Action Buttons */}
          <div className="flex gap-3 pt-6 mt-6 border-t border-border">
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
        </div>
      </motion.div>
    </>
  )
}
