import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { AnimatePresence, easeOut, motion } from "framer-motion"
import { Loader2, Plus } from "lucide-react"
import { useState } from "react"
import { projectsApi } from "@/apis/projects"
import { CreateProjectModal } from "@/components/projects/create-project-modal"
import { ProjectList } from "@/components/projects/project-list"
import { Button } from "@/components/ui/button"
import useAuth from "@/hooks/useAuth"
import { useProjects } from "@/queries/projects"
import type { Project } from "@/types/project"
import { CreateProjectContent } from "@/components/projects/create-project-content"
import { HeaderProject } from "@/components/projects/header"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ApiError, ProjectsListProjectsResponse, ProjectsService } from "@/client"
import { handleError } from "@/utils"
import { requireRole } from "@/utils/auth"
import { useAppStore } from "@/stores/auth-store"

export const Route = createFileRoute("/_user/projects")({
  beforeLoad: async () => {
    await requireRole('user')
  },
  component: ProjectsPage,
})

function ProjectsPage() {
  const [showCreateModal, setShowCreateModal] = useState(false)
  const queryClient = useQueryClient()
  const user = useAppStore((state) => state.user)
  const { data: listProjectPublic, isLoading } = useQuery<ProjectsListProjectsResponse>({
    queryKey: ["list-project"],
    queryFn: () => ProjectsService.listProjects(),
  })

  const handleNewProjectClick = () => {
    setShowCreateModal(true)
  }


  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        delayChildren: 0.2,
      },
    },
  }

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.5, ease: easeOut },
    },
  }


  return (
    <>
      <div className="min-h-screen">
        <HeaderProject />
        <div className="container mx-auto px-6 py-8">
          <motion.div
            variants={containerVariants}
            initial="hidden"
            animate="visible"
          >
            {/* Header */}
            <motion.div
              variants={itemVariants}
              className="mb-10"
            >
              {/* Greeting & Stats Row */}
              <div className="flex items-start justify-between gap-6 mb-6">
                <div className="space-y-3">
                  {/* Greeting */}
                  <motion.p 
                    className="text-sm font-medium text-muted-foreground flex items-center gap-2"
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.3 }}
                  >
                    <span className="inline-block w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                    Welcome back, {user?.full_name?.split(' ')[0] || 'Developer'}
                  </motion.p>
                  
                  {/* Title */}
                  <h1 className="text-4xl md:text-5xl font-bold tracking-tight">
                    <span className="text-foreground">Your </span>
                    <span className="relative">
                      <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary via-primary/80 to-primary/60">
                        Projects
                      </span>
                      <motion.span 
                        className="absolute -bottom-1 left-0 h-1 bg-gradient-to-r from-primary to-primary/40 rounded-full"
                        initial={{ width: 0 }}
                        animate={{ width: '100%' }}
                        transition={{ delay: 0.5, duration: 0.6 }}
                      />
                    </span>
                  </h1>
                  
                  {/* Description */}
                  <p className="text-muted-foreground text-lg max-w-md">
                    Build, manage and deploy your AI-powered projects with ease.
                  </p>
                </div>

                {/* Action Button */}
                <motion.div 
                  whileHover={{ scale: 1.02 }} 
                  whileTap={{ scale: 0.98 }}
                  className="flex-shrink-0"
                >
                  <Button
                    onClick={handleNewProjectClick}
                    size="lg"
                    className="font-semibold gap-2 shadow-lg shadow-primary/20 hover:shadow-xl hover:shadow-primary/30 transition-shadow"
                  >
                    <Plus className="h-5 w-5" />
                    New Project
                  </Button>
                </motion.div>
              </div>

              {/* Stats Bar */}
              <motion.div 
                className="flex items-center gap-6 text-sm"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
              >
                <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-muted/50">
                  <span className="font-semibold text-foreground">
                    {listProjectPublic?.data?.length || 0}
                  </span>
                  <span className="text-muted-foreground">
                    {(listProjectPublic?.data?.length || 0) === 1 ? 'Project' : 'Projects'}
                  </span>
                </div>
                <div className="h-4 w-px bg-border" />
                <span className="text-muted-foreground">
                  Last updated: Today
                </span>
              </motion.div>
            </motion.div>

            {/* Projects List */}
            <motion.div variants={itemVariants}>
              {isLoading ? (
                <div className="flex items-center justify-center py-20">
                  <Loader2 className="h-8 w-8 animate-spin text-purple-400" />
                </div>
              ) : (
                <ProjectList
                  projects={listProjectPublic?.data || []}
                  onCreateProject={handleNewProjectClick}
                />
              )}
            </motion.div>
          </motion.div>
        </div>

        {/* Modals */}
        <AnimatePresence>
          {showCreateModal && (
            <CreateProjectModal
              isOpen={showCreateModal}
              onClose={() => setShowCreateModal(false)}
              setIsOpen={setShowCreateModal}
            />
          )}
        </AnimatePresence>
      </div>
    </>
  )
}
