import { ProjectPublic } from "@/client"
import { ProjectCard } from "./project-card"
import { useQueryClient } from "@tanstack/react-query"

import { useAppStore } from "@/stores/auth-store"
import { useNavigate } from "@tanstack/react-router"
import { ArrowUpRightIcon, FolderOpenDot, Sparkles } from "lucide-react"
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "../ui/empty"
import { Button } from "../ui/button"

interface ProjectListProps {
  projects: ProjectPublic[]
  openLinkGithubModal: React.Dispatch<React.SetStateAction<boolean>>
  openInstallGithubModal: React.Dispatch<React.SetStateAction<boolean>>
}

export const ProjectList = ({ projects }: ProjectListProps) => {
  const queryClient = useQueryClient()
  const user = useAppStore((state) => state.user)
  const naviagate = useNavigate()

  const handleClickProject = (project: ProjectPublic) => {

    naviagate({ to: "/workspace/$workspaceId", params: { workspaceId: project.id } })


  }
  if (projects.length === 0) {
    return (
      <Empty>
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <FolderOpenDot />
          </EmptyMedia>
          <EmptyTitle>No Projects Yet</EmptyTitle>
          <EmptyDescription>
            You haven&apos;t created any projects yet. Get started by creating
            your first project.
          </EmptyDescription>
        </EmptyHeader>
        <EmptyContent>
          <div className="flex gap-2">
            <Button>Create Project</Button>
          </div>
        </EmptyContent>
        <Button
          variant="link"
          asChild
          className="text-muted-foreground"
          size="sm"
        >
          <a href="#">
            Learn More <ArrowUpRightIcon />
          </a>
        </Button>
      </Empty>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {projects.map((project) => (
        <ProjectCard onClick={() => handleClickProject(project)} key={project.code} project={project} />
      ))}
    </div>
  )
}
