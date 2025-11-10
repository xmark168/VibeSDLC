import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useLocation, useNavigate } from "@tanstack/react-router"
import { AnimatePresence } from "framer-motion"
import { useEffect, useState } from "react"
import { type ApiError, GithubService, UserPublic } from "@/client"
import { GitHubLinkModal } from "@/components/projects/github-link-modal"
import { handleError } from "@/utils"
import { useAppStore } from "@/stores/auth-store"
import toast from "react-hot-toast"

interface GitHubInstallationHandlerProps {
  onSuccess?: () => void
  onError?: (error: string) => void
}

export function GitHubInstallationHandler({
  onSuccess,
  onError,
}: GitHubInstallationHandlerProps) {
  const location = useLocation()
  const navigate = useNavigate()
  const token = localStorage.getItem("access_token")
  const [_error, setError] = useState<string | null>(null)
  const [_success, setSuccess] = useState(false)
  const [showLinkModal, setShowLinkModal] = useState(false)
  const queryClient = useQueryClient()
  const { setUser } = useAppStore()
  // Parse query parameters from URL
  const searchParams = new URLSearchParams(location.search)
  const githubInstallation = searchParams.get("github_installation")
  const installationId = searchParams.get("installation_id")
  const errorParam = searchParams.get("error")
  const messageParam = searchParams.get("message")
  const naviagte = useNavigate()
  // Debug logging
  useEffect(() => {
    console.log("GitHubInstallationHandler - URL params:", {
      githubInstallation,
      installationId,
      errorParam,
      messageParam,
      showLinkModal,
    })
  }, [
    githubInstallation,
    installationId,
    errorParam,
    messageParam,
    showLinkModal,
  ])

  const linkGithubMutation = useMutation({
    mutationFn: GithubService.linkInstallationToUser,
    onSuccess: async () => {
      setSuccess(true)
      setShowLinkModal(false)
      onSuccess?.()
      localStorage.removeItem("installationId")
      const userData = await queryClient.fetchQuery({
        queryKey: ["currentUser"],
      })
      setUser(userData as UserPublic)
      navigate({ to: "/projects", replace: true })
    },
    onError: (err) => {
      handleError(err as ApiError)
      setError("Failed to link GitHub installation")
      setShowLinkModal(false)
      onError?.("Failed to link GitHub installation")
    },
  })

  // Handle error from callback
  useEffect(() => {
    if (errorParam) {
      const errorMsg = messageParam || errorParam
      setError(errorMsg)
      onError?.(errorMsg)
    }
  }, [errorParam, messageParam, onError])

  // Show link modal when installation is pending
  useEffect(() => {
    if (githubInstallation === "pending" && installationId) {
      localStorage.setItem("installationId", installationId)
      setShowLinkModal(true)
    }
  }, [githubInstallation, installationId])

  // Handle link installation - called from modal
  const handleLinkInstallation = async () => {
    if (!installationId || !token) {
      setError("Missing installation ID or authentication token")
      setShowLinkModal(false)
      return
    }

    try {
      await linkGithubMutation.mutateAsync({
        installationId: parseInt(installationId, 10),
      })
      // Success will be handled by mutation's onSuccess callback
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "Unknown error"
      setError(errorMsg)
      setShowLinkModal(false)
      onError?.(errorMsg)
    }
  }

  // Handle close modal
  const handleCloseModal = () => {
    setShowLinkModal(false)
    // Remove query params from URL
    navigate({ to: location.pathname, replace: true })
  }

  return (
    <>
      {/* Show link modal for pending installation */}
      <AnimatePresence>
        {showLinkModal && (
          <GitHubLinkModal
            onClose={handleCloseModal}
            onLinked={handleLinkInstallation}
            installationId={
              installationId ? parseInt(installationId, 10) : null
            }
          />
        )}
      </AnimatePresence>
    </>
  )
}
