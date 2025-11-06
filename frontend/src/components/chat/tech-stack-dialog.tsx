import { motion } from "framer-motion"
import { Check, Layers, Plus } from "lucide-react"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { cn } from "@/lib/utils"

interface TechOption {
  id: string
  name: string
  description: string
  icon: string
}

interface TechCategory {
  id: string
  name: string
  description: string
  options: TechOption[]
  allowMultiple?: boolean
}

const TECH_CATEGORIES: TechCategory[] = [
  {
    id: "ui",
    name: "UI",
    description: "User interface frameworks for web and mobile",
    allowMultiple: true,
    options: [
      {
        id: "nextjs",
        name: "Next.js",
        description: "React framework for production",
        icon: "▲",
      },
      {
        id: "react",
        name: "React",
        description: "UI library for building interfaces",
        icon: "⚛️",
      },
      {
        id: "vue",
        name: "Vue.js",
        description: "Progressive JavaScript framework",
        icon: "🟢",
      },
      {
        id: "angular",
        name: "Angular",
        description: "Platform for building web apps",
        icon: "🅰️",
      },
      {
        id: "svelte",
        name: "Svelte",
        description: "Cybernetically enhanced web apps",
        icon: "🔥",
      },
      {
        id: "tailwind",
        name: "Tailwind CSS",
        description: "Utility-first CSS framework",
        icon: "🎨",
      },
      {
        id: "react-native",
        name: "React Native",
        description: "Build native apps with React",
        icon: "📱",
      },
      {
        id: "flutter",
        name: "Flutter",
        description: "Google's UI toolkit for mobile",
        icon: "🦋",
      },
      {
        id: "ionic",
        name: "Ionic",
        description: "Hybrid mobile app framework",
        icon: "⚡",
      },
      {
        id: "expo",
        name: "Expo",
        description: "Platform for React Native apps",
        icon: "🎯",
      },
      {
        id: "swift",
        name: "Swift",
        description: "Native iOS development",
        icon: "🍎",
      },
      {
        id: "kotlin",
        name: "Kotlin",
        description: "Native Android development",
        icon: "🤖",
      },
    ],
  },
  {
    id: "backend",
    name: "Backend",
    description: "Server-side frameworks and runtime",
    allowMultiple: true,
    options: [
      {
        id: "nodejs",
        name: "Node.js",
        description: "JavaScript runtime",
        icon: "🟩",
      },
      {
        id: "express",
        name: "Express",
        description: "Fast Node.js web framework",
        icon: "🚂",
      },
      {
        id: "nestjs",
        name: "NestJS",
        description: "Progressive Node.js framework",
        icon: "🐱",
      },
      {
        id: "python",
        name: "Python",
        description: "High-level programming language",
        icon: "🐍",
      },
      {
        id: "django",
        name: "Django",
        description: "Python web framework",
        icon: "🎸",
      },
      {
        id: "fastapi",
        name: "FastAPI",
        description: "Modern Python web framework",
        icon: "⚡",
      },
      {
        id: "go",
        name: "Go",
        description: "Google's programming language",
        icon: "🔵",
      },
      {
        id: "java",
        name: "Java",
        description: "Enterprise programming language",
        icon: "☕",
      },
      {
        id: "spring",
        name: "Spring Boot",
        description: "Java application framework",
        icon: "🍃",
      },
    ],
  },
  {
    id: "database",
    name: "Database",
    description: "Data storage and management systems",
    allowMultiple: true,
    options: [
      {
        id: "postgresql",
        name: "PostgreSQL",
        description: "Advanced relational database",
        icon: "🐘",
      },
      {
        id: "mysql",
        name: "MySQL",
        description: "Popular relational database",
        icon: "🐬",
      },
      {
        id: "mongodb",
        name: "MongoDB",
        description: "NoSQL document database",
        icon: "🍃",
      },
      {
        id: "redis",
        name: "Redis",
        description: "In-memory data store",
        icon: "🔴",
      },
      {
        id: "supabase",
        name: "Supabase",
        description: "Open source Firebase alternative",
        icon: "⚡",
      },
      {
        id: "firebase",
        name: "Firebase",
        description: "Google's app platform",
        icon: "🔥",
      },
      {
        id: "prisma",
        name: "Prisma",
        description: "Next-generation ORM",
        icon: "💎",
      },
    ],
  },
]

const DEFAULT_SELECTED = {
  ui: ["nextjs", "react", "tailwind"],
  backend: ["nodejs"],
  database: ["postgresql"],
}

export function TechStackDialog() {
  const [isEditing, setIsEditing] = useState(false)
  const [selected, setSelected] =
    useState<Record<string, string[]>>(DEFAULT_SELECTED)
  const [tempSelected, setTempSelected] =
    useState<Record<string, string[]>>(DEFAULT_SELECTED)

  const handleToggleTech = (categoryId: string, techId: string) => {
    setTempSelected((prev) => {
      const current = prev[categoryId] || []
      const isSelected = current.includes(techId)

      if (isSelected) {
        return { ...prev, [categoryId]: current.filter((id) => id !== techId) }
      }
      return { ...prev, [categoryId]: [...current, techId] }
    })
  }

  const handleSave = () => {
    setSelected(tempSelected)
    setIsEditing(false)
  }

  const handleCancel = () => {
    setTempSelected(selected)
    setIsEditing(false)
  }

  const handleEdit = () => {
    setTempSelected(selected)
    setIsEditing(true)
  }

  const currentSelected = isEditing ? tempSelected : selected

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon" className="h-8 w-8 hover:bg-accent">
          <Layers className="w-4 h-4" />
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-4xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <DialogTitle className="flex items-center gap-2">
              <Layers className="w-5 h-5" />
              Project Tech Stack
            </DialogTitle>
            {!isEditing && (
              <Button variant="outline" size="sm" onClick={handleEdit}>
                Edit Stack
              </Button>
            )}
          </div>
        </DialogHeader>

        <div className="space-y-6 mt-4">
          {TECH_CATEGORIES.map((category, categoryIndex) => {
            const selectedTechs = currentSelected[category.id] || []
            const selectedOptions = category.options.filter((opt) =>
              selectedTechs.includes(opt.id),
            )
            const availableOptions = category.options.filter(
              (opt) => !selectedTechs.includes(opt.id),
            )

            return (
              <motion.div
                key={category.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: categoryIndex * 0.1 }}
                className="space-y-3"
              >
                <div>
                  <h3 className="text-sm font-semibold text-foreground">
                    {category.name}
                  </h3>
                  <p className="text-xs text-muted-foreground">
                    {category.description}
                  </p>
                </div>

                {/* Selected Technologies */}
                {selectedOptions.length > 0 && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {selectedOptions.map((tech) => (
                      <motion.div
                        key={tech.id}
                        layout
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.9 }}
                        className={cn(
                          "flex items-start gap-3 p-3 rounded-lg border transition-all",
                          isEditing
                            ? "bg-primary/5 border-primary/20 cursor-pointer hover:bg-primary/10"
                            : "bg-muted/50 border-border",
                        )}
                        onClick={() =>
                          isEditing && handleToggleTech(category.id, tech.id)
                        }
                      >
                        <div className="w-10 h-10 rounded-lg bg-background flex items-center justify-center text-lg flex-shrink-0 border border-border">
                          {tech.icon}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-foreground text-sm">
                              {tech.name}
                            </span>
                            <Check className="w-4 h-4 text-green-500 ml-auto" />
                          </div>
                          <p className="text-xs text-muted-foreground mt-0.5">
                            {tech.description}
                          </p>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                )}

                {/* Available Technologies (only in edit mode) */}
                {isEditing && availableOptions.length > 0 && (
                  <div className="space-y-2">
                    <p className="text-xs text-muted-foreground">
                      Available options:
                    </p>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                      {availableOptions.map((tech) => (
                        <motion.button
                          key={tech.id}
                          layout
                          initial={{ opacity: 0, scale: 0.9 }}
                          animate={{ opacity: 1, scale: 1 }}
                          className="flex items-center gap-2 p-2 rounded-lg border border-dashed border-border hover:border-primary/50 hover:bg-accent transition-all text-left"
                          onClick={() => handleToggleTech(category.id, tech.id)}
                        >
                          <div className="w-8 h-8 rounded bg-muted flex items-center justify-center text-sm flex-shrink-0">
                            {tech.icon}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-xs font-medium text-foreground truncate">
                              {tech.name}
                            </p>
                          </div>
                          <Plus className="w-3 h-3 text-muted-foreground flex-shrink-0" />
                        </motion.button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Empty state */}
                {selectedOptions.length === 0 && !isEditing && (
                  <div className="text-sm text-muted-foreground italic">
                    No technologies selected
                  </div>
                )}
              </motion.div>
            )
          })}
        </div>

        {isEditing && (
          <DialogFooter className="mt-6">
            <Button variant="outline" onClick={handleCancel}>
              Cancel
            </Button>
            <Button onClick={handleSave}>Save Changes</Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  )
}
