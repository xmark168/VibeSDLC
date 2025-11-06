import { Github } from "lucide-react"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"

const GITHUB_APP_NAME = import.meta.env.VITE_GITHUB_APP_NAME || "vibesdlc"

interface GitHubInstallButtonProps {
  variant?: "default" | "outline" | "ghost" | "secondary" | "destructive"
  size?: "default" | "sm" | "lg" | "icon"
  showDialog?: boolean
}

export function GitHubInstallButton({
  variant = "outline",
  size = "default",
  showDialog = true,
}: GitHubInstallButtonProps) {
  const [open, setOpen] = useState(false)

  const handleInstall = () => {
    // Redirect to GitHub App installation page
    const installUrl = `https://github.com/apps/${GITHUB_APP_NAME}/installations/new`
    window.location.href = installUrl
  }

  const button = (
    <Button
      variant={variant}
      size={size}
      onClick={handleInstall}
      className="gap-2"
    >
      <Github className="w-4 h-4" />
      <span>Install GitHub App</span>
    </Button>
  )

  if (!showDialog) {
    return button
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{button}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Install GitHub App</DialogTitle>
          <DialogDescription>
            Connect your GitHub repositories to VibeSDLC to enable automated
            product backlog generation and AI-powered project management.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="bg-muted p-4 rounded-md space-y-2">
            <h4 className="font-medium text-sm">What you'll get:</h4>
            <ul className="text-sm text-muted-foreground space-y-1">
              <li>✓ Access to your GitHub repositories</li>
              <li>✓ Automated product backlog generation</li>
              <li>✓ AI-powered sprint planning</li>
              <li>✓ Real-time repository insights</li>
            </ul>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => setOpen(false)}
              className="flex-1"
            >
              Cancel
            </Button>
            <Button
              onClick={() => {
                setOpen(false)
                handleInstall()
              }}
              className="flex-1 gap-2"
            >
              <Github className="w-4 h-4" />
              Continue to GitHub
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
