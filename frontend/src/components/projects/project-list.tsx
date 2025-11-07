import { ApiError, GithubService, ProjectPublic } from "@/client"
import { ProjectCard } from "./project-card"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import toast from "react-hot-toast"
import { handleError } from "@/utils"
import { useAppStore } from "@/stores/auth-store"

interface ProjectListProps {
  projects: ProjectPublic[]
  openLinkGithubModal: React.Dispatch<React.SetStateAction<boolean>>
  openInstallGithubModal: React.Dispatch<React.SetStateAction<boolean>>
}

export const ProjectList = ({ projects, openLinkGithubModal, openInstallGithubModal }: ProjectListProps) => {
  const queryClient = useQueryClient()
  const user = useAppStore((state) => state.user)

  const handleClickProject = () => {
    if (user?.github_installations === null) {
      openLinkGithubModal(true)
      return
    }

  }
  if (projects.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="w-16 h-16 mb-4 rounded-2xl bg-gradient-to-br from-primary/10 to-accent/10 flex items-center justify-center">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-primary to-accent opacity-50" />
        </div>
        <h3 className="text-xl font-semibold text-foreground mb-2">
          No projects yet
        </h3>
        <p className="text-muted-foreground max-w-sm">
          Create your first project to get started
        </p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {projects.map((project) => (
        <ProjectCard onClick={handleClickProject} key={project.code} project={project} />
      ))}
    </div>
  )
}
