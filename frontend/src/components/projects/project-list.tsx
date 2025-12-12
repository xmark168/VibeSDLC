import { ProjectPublic, ProjectsService, AgentsService } from "@/client"
import { ProjectCard } from "./project-card-v2"
import { useMutation, useQueryClient, useQueries } from "@tanstack/react-query"
import { motion } from "framer-motion"
import { formatDistanceToNow } from "date-fns"
import { vi } from "date-fns/locale"
import toast from "react-hot-toast"

import { useAppStore } from "@/stores/auth-store"
import { useNavigate } from "@tanstack/react-router"
import { ArrowRight, FolderPlus, Rocket, Sparkles, Zap } from "lucide-react"
import { Button } from "../ui/button"
import { OpenAPI } from "@/client"

interface ProjectListProps {
  projects: ProjectPublic[]
  openLinkGithubModal?: React.Dispatch<React.SetStateAction<boolean>>
  openInstallGithubModal?: React.Dispatch<React.SetStateAction<boolean>>
  onCreateProject?: () => void
}

export const ProjectList = ({ projects, onCreateProject }: ProjectListProps) => {
  const queryClient = useQueryClient()
  const user = useAppStore((state) => state.user)
  const naviagate = useNavigate()

  // Fetch agents for all projects in parallel
  const agentQueries = useQueries({
    queries: projects.map((project) => ({
      queryKey: ["agents", "project", project.id],
      queryFn: async () => {
        const response = await AgentsService.getProjectAgents({ projectId: project.id })
        return { projectId: project.id, agents: response || [] }
      },
      staleTime: 0, // Always fetch fresh data
      refetchOnMount: 'always' as const, // Force refetch on mount
    })),
  })

  // Create a map of projectId -> agents
  const agentsByProject = agentQueries.reduce((acc, query) => {
    if (query.data) {
      acc[query.data.projectId] = query.data.agents
    }
    return acc
  }, {} as Record<string, any[]>)

  const handleClickProject = (project: ProjectPublic) => {
    naviagate({ to: "/workspace/$workspaceId", params: { workspaceId: project.id } })
  }

  // Delete project mutation
  const deleteProjectMutation = useMutation({
    mutationFn: (projectId: string) => ProjectsService.deleteProject({ projectId }),
    onSuccess: () => {
      toast.success("Project deleted successfully")
      queryClient.invalidateQueries({ queryKey: ["list-project"] })
    },
    onError: (error: Error) => {
      toast.error(`Failed to delete project: ${error.message}`)
    },
  })

  // Cleanup worktrees - direct API call since not in generated client
  const cleanupWorktreesMutation = useMutation({
    mutationFn: async (projectId: string) => {
      const token = localStorage.getItem('access_token') || ''
      const response = await fetch(`${OpenAPI.BASE}/api/v1/projects/${projectId}/cleanup`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      })
      if (!response.ok) throw new Error("Failed to cleanup worktrees")
      return response.json()
    },
    onSuccess: (data) => {
      toast.success(`Cleaned up ${data.deleted_count} worktrees`)
    },
    onError: (error: Error) => {
      toast.error(`Failed to cleanup: ${error.message}`)
    },
  })

  const handleDeleteProject = async (projectId: string) => {
    await deleteProjectMutation.mutateAsync(projectId)
  }

  const handleCleanupWorktrees = (projectId: string) => {
    cleanupWorktreesMutation.mutate(projectId)
  }

  if (projects.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="flex flex-col items-center justify-center py-16 px-4"
      >
        {/* Animated Icon Container */}
        <motion.div 
          className="relative mb-8"
          initial={{ scale: 0.8 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
        >
          {/* Background Glow */}
          <div className="absolute inset-0 bg-primary/20 rounded-full blur-2xl scale-150" />
          
          {/* Icon Circle */}
          <div className="relative w-24 h-24 rounded-full bg-gradient-to-br from-primary/10 to-primary/5 border border-primary/20 flex items-center justify-center">
            <motion.div
              animate={{ 
                rotate: [0, 10, -10, 0],
              }}
              transition={{ 
                duration: 4, 
                repeat: Infinity,
                ease: "easeInOut"
              }}
            >
              <FolderPlus className="w-10 h-10 text-primary" />
            </motion.div>
          </div>

          {/* Floating Particles */}
          <motion.div 
            className="absolute -top-2 -right-2"
            animate={{ y: [-2, 2, -2] }}
            transition={{ duration: 2, repeat: Infinity }}
          >
            <Sparkles className="w-5 h-5 text-yellow-500" />
          </motion.div>
          <motion.div 
            className="absolute -bottom-1 -left-3"
            animate={{ y: [2, -2, 2] }}
            transition={{ duration: 2.5, repeat: Infinity }}
          >
            <Zap className="w-4 h-4 text-primary" />
          </motion.div>
        </motion.div>

        {/* Text Content */}
        <motion.div 
          className="text-center max-w-md mb-8"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
        >
          <h3 className="text-2xl font-bold text-foreground mb-3">
            Start Your First Project
          </h3>
          <p className="text-muted-foreground leading-relaxed">
            Create your first AI-powered project and let our intelligent agents 
            help you build something amazing.
          </p>
        </motion.div>

        {/* CTA Button */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="flex flex-col items-center gap-4"
        >
          <Button 
            size="lg" 
            onClick={onCreateProject}
            className="gap-2 shadow-lg shadow-primary/25 hover:shadow-xl hover:shadow-primary/30 transition-all"
          >
            <Rocket className="w-4 h-4" />
            Create Your First Project
          </Button>
          
          <motion.a 
            href="#"
            className="text-sm text-muted-foreground hover:text-primary flex items-center gap-1 transition-colors"
            whileHover={{ x: 3 }}
          >
            Learn how it works
            <ArrowRight className="w-3 h-3" />
          </motion.a>
        </motion.div>

        {/* Feature Highlights */}
        <motion.div 
          className="grid grid-cols-3 gap-6 mt-12 pt-8 border-t border-border/50 max-w-lg w-full"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
        >
          {[
            { icon: "🤖", label: "AI Agents" },
            { icon: "⚡", label: "Fast Setup" },
            { icon: "🔒", label: "Secure" },
          ].map((feature, i) => (
            <motion.div 
              key={feature.label}
              className="text-center"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 + i * 0.1 }}
            >
              <div className="text-2xl mb-1">{feature.icon}</div>
              <div className="text-xs text-muted-foreground font-medium">{feature.label}</div>
            </motion.div>
          ))}
        </motion.div>
      </motion.div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {projects.map((project) => (
        <div 
          key={project.code} 
          onClick={() => handleClickProject(project)}
          className="cursor-pointer"
        >
          <ProjectCard
            title={project.name}
            code={project.code}
            projectId={project.id}
            status={project.is_init ? "in-progress" : "planning"}
            techStack={project.tech_stack || []}
            agents={(agentsByProject[project.id] || []).map((agent: any) => ({
              id: agent.id,
              human_name: agent.human_name,
              role_type: agent.role_type,
              persona_avatar: agent.persona_avatar,
            }))}
            lastUpdated={formatDistanceToNow(new Date(project.updated_at), { addSuffix: true, locale: vi })}
            githubUrl={project.repository_url || undefined}
            onDelete={handleDeleteProject}
            onCleanup={handleCleanupWorktrees}
          />
        </div>
      ))}
    </div>
  )
}
