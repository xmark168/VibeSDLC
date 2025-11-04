import { format } from "date-fns"
import { Calendar, Globe, Lock } from "lucide-react"
import { Badge } from "@/components/ui/badge"

export interface Project {
  code: string
  repositoryName: string
  createdAt: Date | string
  mode: "public" | "private"
}
interface ProjectCardProps {
  project: Project
}

export const ProjectCard = ({ project }: ProjectCardProps) => {
  const createdDate =
    typeof project.createdAt === "string"
      ? new Date(project.createdAt)
      : project.createdAt

  return (
    <div className="group relative overflow-hidden rounded-xl bg-gradient-to-b from-card to-card/80 p-6 shadow-[var(--shadow-sm)] transition-all duration-300 hover:shadow-[var(--shadow-hover)] hover:-translate-y-1">
      {/* Gradient accent bar */}
      <div className="absolute top-0 left-0 right-0 h-1 bg-[var(--gradient-primary)] opacity-0 transition-opacity duration-300 group-hover:opacity-100" />

      {/* Content */}
      <div className="space-y-4">
        {/* Header with code and status */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <div className="w-2 h-2 rounded-full bg-gradient-to-r from-[hsl(var(--primary))] to-[hsl(var(--accent))] animate-pulse" />
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                {project.code}
              </span>
            </div>
            <h3 className="text-xl font-semibold text-foreground truncate group-hover:text-primary transition-colors">
              {project.repositoryName}
            </h3>
          </div>

          <Badge
            variant={project.mode === "public" ? "default" : "secondary"}
            className="flex items-center gap-1.5 px-3 py-1 font-medium"
          >
            {project.mode === "public" ? (
              <>
                <Globe className="w-3.5 h-3.5" />
                Public
              </>
            ) : (
              <>
                <Lock className="w-3.5 h-3.5" />
                Private
              </>
            )}
          </Badge>
        </div>

        {/* Created date */}
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Calendar className="w-4 h-4" />
          <span>Created {format(createdDate, "MMM dd, yyyy")}</span>
        </div>

        {/* Bottom gradient line on hover */}
        <div className="absolute bottom-0 left-0 right-0 h-[2px] bg-[var(--gradient-primary)] transform origin-left scale-x-0 transition-transform duration-300 group-hover:scale-x-100" />
      </div>
    </div>
  )
}
