import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { AnimatePresence, easeOut, motion } from "framer-motion"
import { Loader2, Plus } from "lucide-react"
import { useState } from "react"
import { projectsApi } from "@/apis/projects"
import { CreateProjectModal } from "@/components/projects/create-project-modal"
import { GitHubInstallModal } from "@/components/projects/github-install-modal"
import { GitHubLinkModal } from "@/components/projects/github-link-modal"
import { ProjectList } from "@/components/projects/project-list"
import { Button } from "@/components/ui/button"
import useAuth from "@/hooks/useAuth"
import { useProjects } from "@/queries/projects"
import type { Project } from "@/types/project"
import { CreateProjectContent } from "@/components/projects/create-project-content"
import { HeaderProject } from "@/components/projects/header"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ApiError, GithubCheckGithubInstallationStatusResponse, GithubService, ProjectsListProjectsResponse, ProjectsService } from "@/client"
import { GitHubInstallationHandler } from "@/components/github/GitHubInstallationHandler"
import toast from "react-hot-toast"
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
  const [showGitHubInstallModal, setShowGitHubInstallModal] = useState(false)
  const [showGitHubLinkModal, setShowGitHubLinkModal] = useState(false)
  const [_githubLinked, setGithubLinked] = useState(false)
  const [linkSuccess, setLinkSuccess] = useState(false)
  const installationId = (localStorage.getItem("installationId"))
  const queryClient = useQueryClient()
  const user = useAppStore((state) => state.user)
  const { data: _githubStatus } = useQuery<GithubCheckGithubInstallationStatusResponse>({
    queryKey: ["github-installation-status"],
    queryFn: GithubService.checkGithubInstallationStatus,
  })
  const { data: listProjectPublic, isLoading } = useQuery<ProjectsListProjectsResponse>({
    queryKey: ["list-project"],
    queryFn: () => ProjectsService.listProjects(),
  })
  const linkInstallationMutation = useMutation({
    mutationFn: GithubService.linkInstallationToUser,
    onSuccess: () => {
      toast.success("GitHub installation linked successfully")
      setLinkSuccess(true)
      localStorage.removeItem("installationId")
      queryClient.invalidateQueries({
        queryKey: ["currentUser"],
      })
    },
    onError: (err) => {
      handleError(err as ApiError)
    },
  })
  console.log('_githubStatus', _githubStatus)


  const _handleInstallGitHub = () => {
    setShowGitHubInstallModal(true)
  }

  const handleGitHubInstallComplete = () => {
    setShowGitHubInstallModal(false)
    setShowGitHubLinkModal(true)
  }

  const handleGitHubLinked = async () => {
    try {
      await linkInstallationMutation.mutateAsync({
        installationId: parseInt(installationId || "0", 10),
      })
    } catch (err) {
      console.error("Failed to link installation:", err)
    }
  }

  const handleNewProjectClick = () => {
    if (user?.github_installations === null) {
      setShowGitHubLinkModal(true)
    }
    else {
      setShowCreateModal(true)
    }
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
     
      

       (
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
                    className="flex items-center justify-between mb-8"
                  >
                    <div>
                      <h1 className="text-4xl font-bold text-white mb-2">
                        Your{" "}
                        <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-purple-600">
                          Projects
                        </span>
                      </h1>
                      <p className="text-slate-400">
                        Manage your AI-powered development projects
                      </p>
                    </div>

                    <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                      <Button
                        onClick={handleNewProjectClick}
                        className="bg-gradient-to-r from-purple-500 to-purple-600 hover:from-purple-600 hover:to-purple-700 text-white font-semibold gap-2"
                      >
                        <Plus className="h-5 w-5" />
                        New Project
                      </Button>
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
                        openLinkGithubModal={setShowGitHubLinkModal}
                        openInstallGithubModal={setShowGitHubInstallModal}
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



              <AnimatePresence>
                {showGitHubLinkModal && (
                  <GitHubLinkModal
                    onClose={() => {
                      setShowGitHubLinkModal(false)
                      setLinkSuccess(false)
                    }}
                    onLinked={handleGitHubLinked}
                    installationId={installationId ? parseInt(installationId, 10) : null}
                    isSuccess={linkSuccess}
                  />
                )}
              </AnimatePresence>
            </div>
          ) 
      

    </>
  )
}
