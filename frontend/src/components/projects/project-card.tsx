import { format } from "date-fns"
import { Calendar, Globe, Lock, ExternalLink } from "lucide-react"
import { motion } from "framer-motion"
import { Badge } from "@/components/ui/badge"
import { ProjectPublic } from "@/client"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"


interface ProjectCardProps {
  project: ProjectPublic
  onClick?: () => void
}

export const ProjectCard = ({ project, onClick }: ProjectCardProps) => {

  const createdDate =
    typeof project.created_at === "string"
      ? new Date(project.created_at)
      : project.created_at

  return (
    <div
      onClick={onClick}
      className="group relative overflow-hidden rounded-xl bg-card border border-border p-6 shadow-sm transition-all duration-300 hover:shadow-lg hover:border-primary/30 hover:bg-accent/50 hover:-translate-y-1 cursor-pointer">
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
              {project.name}
            </h3>
          </div>

          <Badge
            variant={project.is_private === false ? "default" : "secondary"}
            className="flex items-center gap-1.5 px-3 py-1 font-medium"
          >
            {project.is_private === false ? (
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

        {/* Actions footer */}
        <div className="flex items-center justify-end pt-2">
          {project.github_repository_url && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <motion.a
                    href={project.github_repository_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.95 }}
                    className="inline-flex items-center justify-center p-2 rounded-lg text-muted-foreground hover:text-primary hover:bg-accent transition-colors"
                  >
                    <ExternalLink className="w-4 h-4" />
                  </motion.a>
                </TooltipTrigger>
                <TooltipContent side="bottom">
                  <p>Open GitHub Repository</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
        </div>

        {/* Bottom gradient line on hover */}
        <div className="absolute bottom-0 left-0 right-0 h-[2px] bg-[var(--gradient-primary)] transform origin-left scale-x-0 transition-transform duration-300 group-hover:scale-x-100" />
      </div>
    </div>
  )
}
