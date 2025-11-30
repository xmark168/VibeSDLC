import { useState } from "react"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import {
  Alert,
  AlertDescription,
} from "@/components/ui/alert"
import { useLinkedAccounts, useUnlinkAccount, useInitiateLink } from "@/queries/linked-accounts"
import type { OAuthProvider, LinkedAccount } from "@/types/linked-account"
import { Link2, Unlink, Loader2, AlertTriangle, Check } from "lucide-react"
import { FaGoogle, FaGithub, FaFacebook } from "react-icons/fa"
import toast from "react-hot-toast"
import { format } from "date-fns"

const providerConfig: Record<OAuthProvider, { name: string; icon: React.ReactNode; color: string }> = {
  google: {
    name: "Google",
    icon: <FaGoogle className="w-5 h-5" />,
    color: "text-[#EA4335]",
  },
  github: {
    name: "GitHub",
    icon: <FaGithub className="w-5 h-5" />,
    color: "text-foreground",
  },
  facebook: {
    name: "Facebook",
    icon: <FaFacebook className="w-5 h-5" />,
    color: "text-[#1877F2]",
  },
}

export function LinkedAccountsSettings() {
  const { data, isLoading } = useLinkedAccounts()
  const unlinkMutation = useUnlinkAccount()
  const initiateLinkMutation = useInitiateLink()
  const [unlinkDialogOpen, setUnlinkDialogOpen] = useState(false)
  const [selectedProvider, setSelectedProvider] = useState<OAuthProvider | null>(null)
  const [linkingProvider, setLinkingProvider] = useState<OAuthProvider | null>(null)

  const handleLink = (provider: OAuthProvider) => {
    setLinkingProvider(provider)
    initiateLinkMutation.mutate(provider)
  }

  const handleUnlinkClick = (provider: OAuthProvider) => {
    setSelectedProvider(provider)
    setUnlinkDialogOpen(true)
  }

  const handleUnlink = async () => {
    if (!selectedProvider) return

    try {
      await unlinkMutation.mutateAsync({ provider: selectedProvider })
      toast.success(`${providerConfig[selectedProvider].name} account unlinked`)
      setUnlinkDialogOpen(false)
      setSelectedProvider(null)
    } catch (error: any) {
      toast.error(error?.body?.detail || "Failed to unlink account")
    }
  }

  const linkedProviders = data?.linked_accounts || []
  const availableProviders = (data?.available_providers || []) as OAuthProvider[]

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin" />
        </CardContent>
      </Card>
    )
  }

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Link2 className="w-5 h-5" />
            Linked Accounts
          </CardTitle>
          <CardDescription>
            Connect your account with third-party providers for easier sign-in
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Linked accounts */}
          {linkedProviders.map((account: LinkedAccount) => {
            const config = providerConfig[account.provider]
            return (
              <div
                key={account.id}
                className="flex items-center justify-between p-4 bg-muted/50 rounded-lg"
              >
                <div className="flex items-center gap-3">
                  <div className={`${config.color}`}>{config.icon}</div>
                  <div>
                    <p className="font-medium flex items-center gap-2">
                      {config.name}
                      <Check className="w-4 h-4 text-green-500" />
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {account.provider_email}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Linked {format(new Date(account.created_at), "MMM d, yyyy")}
                    </p>
                  </div>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleUnlinkClick(account.provider)}
                  disabled={unlinkMutation.isPending}
                >
                  <Unlink className="w-4 h-4 mr-1" />
                  Unlink
                </Button>
              </div>
            )
          })}

          {/* Available providers to link */}
          {availableProviders.map((provider) => {
            const config = providerConfig[provider]
            if (!config) return null
            return (
              <div
                key={provider}
                className="flex items-center justify-between p-4 border border-dashed rounded-lg"
              >
                <div className="flex items-center gap-3">
                  <div className={`${config.color} opacity-50`}>{config.icon}</div>
                  <div>
                    <p className="font-medium text-muted-foreground">{config.name}</p>
                    <p className="text-sm text-muted-foreground">Not connected</p>
                  </div>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleLink(provider)}
                  disabled={linkingProvider !== null}
                >
                  {linkingProvider === provider ? (
                    <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                  ) : (
                    <Link2 className="w-4 h-4 mr-1" />
                  )}
                  Link
                </Button>
              </div>
            )
          })}

          {linkedProviders.length === 0 && availableProviders.length === 0 && (
            <p className="text-center text-muted-foreground py-4">
              No providers available
            </p>
          )}
        </CardContent>
      </Card>

      {/* Unlink confirmation dialog */}
      <Dialog open={unlinkDialogOpen} onOpenChange={setUnlinkDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Unlink Account</DialogTitle>
            <DialogDescription>
              Are you sure you want to unlink your{" "}
              {selectedProvider && providerConfig[selectedProvider]?.name} account?
            </DialogDescription>
          </DialogHeader>
          <Alert>
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              You will no longer be able to sign in using this provider unless you link it again.
            </AlertDescription>
          </Alert>
          <DialogFooter>
            <Button variant="outline" onClick={() => setUnlinkDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleUnlink}
              disabled={unlinkMutation.isPending}
            >
              {unlinkMutation.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin mr-1" />
              ) : null}
              Unlink
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
