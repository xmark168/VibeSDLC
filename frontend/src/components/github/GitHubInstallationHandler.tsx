import { useEffect, useState } from "react"
import { useLocation } from "@tanstack/react-router"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { AlertCircle, CheckCircle2, Loader2 } from "lucide-react"

interface GitHubInstallationHandlerProps {
  onSuccess?: () => void
  onError?: (error: string) => void
}

export function GitHubInstallationHandler({
  onSuccess,
  onError,
}: GitHubInstallationHandlerProps) {
  const location = useLocation()
  const token = localStorage.getItem("access_token")
  const [linking, setLinking] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  // Parse query parameters from URL
  const searchParams = new URLSearchParams(location.search)
  const githubInstallation = searchParams.get("github_installation")
  const installationId = searchParams.get("installation_id")
  const errorParam = searchParams.get("error")
  const messageParam = searchParams.get("message")

  // Handle error from callback
  useEffect(() => {
    if (errorParam) {
      const errorMsg = messageParam || errorParam
      setError(errorMsg)
      onError?.(errorMsg)
    }
  }, [errorParam, messageParam, onError])

  // Handle pending installation - show link prompt
  const handleLinkInstallation = async () => {
    if (!installationId || !token) {
      setError("Missing installation ID or authentication token")
      return
    }

    setLinking(true)
    try {
      const response = await fetch(
        `/api/v1/github/link-installation`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`,
          },
          body: JSON.stringify({
            installation_id: parseInt(installationId),
          }),
        }
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.message || "Failed to link installation")
      }

      setSuccess(true)
      onSuccess?.()
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "Unknown error"
      setError(errorMsg)
      onError?.(errorMsg)
    } finally {
      setLinking(false)
    }
  }

  // Show error alert
  if (error) {
    return (
      <Alert variant="destructive" className="mb-4">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>GitHub Installation Error</AlertTitle>
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    )
  }

  // Show success alert
  if (success) {
    return (
      <Alert className="mb-4 border-green-200 bg-green-50">
        <CheckCircle2 className="h-4 w-4 text-green-600" />
        <AlertTitle className="text-green-900">
          GitHub App Linked Successfully
        </AlertTitle>
        <AlertDescription className="text-green-800">
          Your GitHub App has been linked to your account. You can now use GitHub integration features.
        </AlertDescription>
      </Alert>
    )
  }

  // Show link prompt for pending installation
  if (githubInstallation === "pending" && installationId) {
    return (
      <AlertDialog open={true}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Link GitHub App with Your Account?</AlertDialogTitle>
            <AlertDialogDescription>
              GitHub App has been installed successfully. Would you like to link it with your VibeSDLC account now?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="flex gap-2">
            <AlertDialogCancel
              disabled={linking}
            >
              Later
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleLinkInstallation}
              disabled={linking}
              className="gap-2"
            >
              {linking && <Loader2 className="w-4 h-4 animate-spin" />}
              {linking ? "Linking..." : "Link Now"}
            </AlertDialogAction>
          </div>
        </AlertDialogContent>
      </AlertDialog>
    )
  }

  // Show success alert for existing installation
  if (githubInstallation === "exists" && installationId) {
    return (
      <Alert className="mb-4 border-blue-200 bg-blue-50">
        <CheckCircle2 className="h-4 w-4 text-blue-600" />
        <AlertTitle className="text-blue-900">
          GitHub App Already Installed
        </AlertTitle>
        <AlertDescription className="text-blue-800">
          This GitHub App installation already exists. You can manage it from your GitHub settings.
        </AlertDescription>
      </Alert>
    )
  }

  return null
}

