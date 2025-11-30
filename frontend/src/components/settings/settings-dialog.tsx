import { useState, useEffect } from "react"
import { User, CreditCard, LogOut, Pencil, Info, Sun, Moon, Monitor, AlertTriangle, RefreshCw, ShieldCheck, Camera, Check, X, Loader2 } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Input } from "@/components/ui/input"
import { Switch } from "@/components/ui/switch"
import { useAppStore } from "@/stores/auth-store"
import useAuth from "@/hooks/useAuth"
import { useTheme } from "@/components/provider/theme-provider"
import { cn } from "@/lib/utils"
import { useCurrentSubscription } from "@/queries/subscription"
import { subscriptionApi } from "@/apis/subscription"
import { TwoFactorSettings } from "./two-factor-settings"
import { LinkedAccountsSettings } from "./linked-accounts-settings"
import { AvatarUploadDialog } from "./avatar-upload-dialog"
import { useProfile, useUpdateProfile } from "@/queries/profile"
import { format } from "date-fns"
import { useQueryClient } from "@tanstack/react-query"
import toast from "react-hot-toast"

const DEFAULT_AVATAR = "https://github.com/shadcn.png"

interface SettingsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  defaultTab?: SettingsTab
}

type SettingsTab = "profile" | "security" | "billing" | "theme"

export function SettingsDialog({ open, onOpenChange, defaultTab }: SettingsDialogProps) {
  const [activeTab, setActiveTab] = useState<SettingsTab>(defaultTab || "profile")

  // Update active tab when defaultTab changes
  useEffect(() => {
    if (defaultTab && open) {
      setActiveTab(defaultTab)
    }
  }, [defaultTab, open])
  const [isCanceling, setIsCanceling] = useState(false)
  const [isTogglingAutoRenew, setIsTogglingAutoRenew] = useState(false)
  const [showCancelDialog, setShowCancelDialog] = useState(false)
  const [avatarDialogOpen, setAvatarDialogOpen] = useState(false)
  const [isEditingName, setIsEditingName] = useState(false)
  const [editName, setEditName] = useState("")
  const user = useAppStore((state) => state.user)
  const { logout } = useAuth()
  const { theme, setTheme } = useTheme()
  const { data: subscriptionData, isLoading: subscriptionLoading } = useCurrentSubscription()
  const { data: profile, isLoading: profileLoading } = useProfile()
  const updateProfileMutation = useUpdateProfile()
  const queryClient = useQueryClient()

  // Get avatar URL with fallback
  const avatarUrl = import.meta.env.VITE_API_URL + profile?.avatar_url || DEFAULT_AVATAR

  const handleLogout = () => {
    logout.mutate()
    onOpenChange(false)
  }

  const handleStartEditName = () => {
    setEditName(profile?.full_name || "")
    setIsEditingName(true)
  }

  const handleCancelEditName = () => {
    setIsEditingName(false)
    setEditName("")
  }

  const handleSaveName = async () => {
    if (!editName.trim()) {
      toast.error("Name cannot be empty")
      return
    }
    try {
      await updateProfileMutation.mutateAsync({ full_name: editName.trim() })
      toast.success("Name updated successfully")
      setIsEditingName(false)
    } catch (error: any) {
      toast.error(error.message || "Failed to update name")
    }
  }

  const handleCancelSubscription = async () => {
    setShowCancelDialog(false)
    setIsCanceling(true)
    try {
      const result = await subscriptionApi.cancelSubscription()

      // Invalidate subscription query to refetch
      queryClient.invalidateQueries({ queryKey: ['subscription', 'current'] })

      toast.success(result.message, {
        duration: 5000,
        style: {
          background: '#1e293b',
          color: '#fff',
          border: '1px solid #334155',
        },
      })
    } catch (error: any) {
      toast.error(error?.body?.detail || 'Không thể hủy subscription', {
        style: {
          background: '#1e293b',
          color: '#fff',
          border: '1px solid #334155',
        },
      })
    } finally {
      setIsCanceling(false)
    }
  }

  const handleToggleAutoRenew = async (enabled: boolean) => {
    setIsTogglingAutoRenew(true)
    try {
      const result = await subscriptionApi.updateAutoRenew(enabled)

      // Invalidate subscription query to refetch
      queryClient.invalidateQueries({ queryKey: ['subscription', 'current'] })

      toast.success(result.message, {
        duration: 3000,
        style: {
          background: '#1e293b',
          color: '#fff',
          border: '1px solid #334155',
        },
      })
    } catch (error: any) {
      toast.error(error?.body?.detail || 'Không thể cập nhật auto-renew', {
        style: {
          background: '#1e293b',
          color: '#fff',
          border: '1px solid #334155',
        },
      })
    } finally {
      setIsTogglingAutoRenew(false)
    }
  }

  const getInitials = (name: string) => {
    return name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase()
      .slice(0, 2)
  }

  // Get current plan name and credit info
  const currentPlanName = subscriptionData?.subscription?.plan?.name || "Free"
  const totalCredits = subscriptionData?.credit_wallet?.total_credits || 0
  const usedCredits = subscriptionData?.credit_wallet?.used_credits || 0
  const remainingCredits = subscriptionData?.credit_wallet?.remaining_credits || 0
  const creditPercentage = totalCredits > 0 ? (remainingCredits / totalCredits) * 100 : 0

  // Format period end date
  const periodEnd = subscriptionData?.credit_wallet?.period_end
    ? format(new Date(subscriptionData.credit_wallet.period_end), 'MMM dd')
    : null

  // Get auto-renew status (default to false for FREE plan)
  const autoRenew = subscriptionData?.subscription?.auto_renew || false
  const isPaidSubscription = subscriptionData?.subscription && currentPlanName !== "Free"

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="!max-w-6xl sm:!max-w-6xl w-[100vw] h-[80vh] p-0 overflow-hidden">
        <div className="flex h-full overflow-hidden">
          {/* Sidebar */}
          <div className="w-72 border-r bg-secondary/10 p-6">
            <DialogHeader className="mb-6">
              <DialogTitle className="text-xl">Settings</DialogTitle>
            </DialogHeader>

            <div className="space-y-2">
              <button
                onClick={() => setActiveTab("profile")}
                className={cn(
                  "w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors",
                  activeTab === "profile"
                    ? "bg-secondary text-foreground"
                    : "text-muted-foreground hover:bg-secondary/50"
                )}
              >
                <User className="h-4 w-4" />
                Profile
              </button>

              <button
                onClick={() => setActiveTab("security")}
                className={cn(
                  "w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors",
                  activeTab === "security"
                    ? "bg-secondary text-foreground"
                    : "text-muted-foreground hover:bg-secondary/50"
                )}
              >
                <ShieldCheck className="h-4 w-4" />
                Security
              </button>

              <button
                onClick={() => setActiveTab("billing")}
                className={cn(
                  "w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors",
                  activeTab === "billing"
                    ? "bg-secondary text-foreground"
                    : "text-muted-foreground hover:bg-secondary/50"
                )}
              >
                <CreditCard className="h-4 w-4" />
                Plans and Billing
              </button>

              <button
                onClick={() => setActiveTab("theme")}
                className={cn(
                  "w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors",
                  activeTab === "theme"
                    ? "bg-secondary text-foreground"
                    : "text-muted-foreground hover:bg-secondary/50"
                )}
              >
                <Sun className="h-4 w-4" />
                Theme
              </button>
            </div>
          </div>

          {/* Content Area */}
          <div className="flex-1 flex flex-col overflow-hidden min-h-0">
            {activeTab === "profile" && (
              <div className="flex-1 flex flex-col overflow-y-auto min-h-0">
                <div className="p-8 pb-6">
                  <h2 className="text-2xl font-semibold">Profile</h2>
                </div>

                {/* Avatar Section */}
                <div className="flex items-center justify-between px-8 py-6 border-t">
                  <h3 className="text-base font-normal">Avatar</h3>
                  <div className="relative group">
                    <Avatar className="h-20 w-20 ring-2 ring-primary/20">
                      <AvatarImage src={avatarUrl} alt={profile?.full_name || "User"} />
                      <AvatarFallback className="bg-[var(--gradient-primary)] text-white text-2xl font-semibold">
                        {getInitials(profile?.full_name || user?.full_name || "")}
                      </AvatarFallback>
                    </Avatar>
                    <button
                      onClick={() => setAvatarDialogOpen(true)}
                      className="absolute inset-0 flex items-center justify-center bg-black/50 rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <Camera className="h-6 w-6 text-white" />
                    </button>
                  </div>
                </div>

                {/* Username Section */}
                <div className="flex items-center justify-between px-8 py-6 border-t">
                  <h3 className="text-base font-normal">Username</h3>
                  {isEditingName ? (
                    <div className="flex items-center gap-2">
                      <Input
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        className="w-48 h-9"
                        placeholder="Enter your name"
                        autoFocus
                        onKeyDown={(e) => {
                          if (e.key === "Enter") handleSaveName()
                          if (e.key === "Escape") handleCancelEditName()
                        }}
                      />
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={handleSaveName}
                        disabled={updateProfileMutation.isPending}
                      >
                        {updateProfileMutation.isPending ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Check className="h-4 w-4 text-green-500" />
                        )}
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={handleCancelEditName}
                        disabled={updateProfileMutation.isPending}
                      >
                        <X className="h-4 w-4 text-red-500" />
                      </Button>
                    </div>
                  ) : (
                    <div className="flex items-center gap-3">
                      <span className="text-base">{profile?.full_name || user?.full_name || ""}</span>
                      <Button variant="ghost" size="icon" className="h-8 w-8" onClick={handleStartEditName}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                    </div>
                  )}
                </div>

                {/* Email Section */}
                <div className="flex items-center justify-between px-8 py-6 border-t">
                  <h3 className="text-base font-normal">Email</h3>
                  <span className="text-base">{user?.email || ""}</span>
                </div>

                {/* Sign Out Button */}
                <div className="flex justify-end px-8 py-6 border-t mt-auto">
                  <Button
                    variant="destructive"
                    onClick={handleLogout}
                    className="flex items-center gap-2"
                  >
                    <LogOut className="h-4 w-4" />
                    Sign out
                  </Button>
                </div>
              </div>
            )}

            {activeTab === "security" && (
              <div className="flex-1 flex flex-col overflow-y-auto min-h-0">
                <div className="p-8 pb-6">
                  <h2 className="text-2xl font-semibold">Security</h2>
                </div>
                <div className="px-8 pb-8 space-y-6">
                  <TwoFactorSettings />
                  <LinkedAccountsSettings />
                </div>
              </div>
            )}

            {activeTab === "billing" && (
              <div className="flex-1 flex flex-col overflow-hidden">
                {/* Header */}
                <div className="p-8 pb-6 flex-shrink-0">
                  <h2 className="text-2xl font-semibold">Plans and Billing</h2>
                </div>

                {/* Scrollable Content */}
                <div className="flex-1 overflow-y-auto overflow-x-hidden">
                  {/* Credits Remaining Card */}
                  <div className="px-8 pb-6 pt-2">
                    {subscriptionLoading ? (
                      <div className="bg-secondary/30 rounded-lg p-6 flex items-center justify-center">
                        <p className="text-sm text-muted-foreground">Loading...</p>
                      </div>
                    ) : (
                      <div className="bg-secondary/30 rounded-lg p-6">
                        <div className="flex items-center justify-between mb-4">
                          <div className="flex items-center gap-2">
                            <h3 className="text-base font-medium">Credits remaining</h3>
                            <Info className="h-4 w-4 text-muted-foreground" />
                          </div>
                          <span className="text-sm font-medium">
                            {remainingCredits.toLocaleString()} / {totalCredits.toLocaleString()}
                          </span>
                        </div>

                        {totalCredits > 0 && (
                          <div className="space-y-2 mb-4">
                            <div className="flex items-center gap-3">
                              <div className="flex-1 h-2 bg-secondary rounded-full overflow-hidden">
                                <div
                                  className="h-full bg-primary transition-all"
                                  style={{ width: `${creditPercentage}%` }}
                                />
                              </div>
                              <span className="text-sm font-medium">{remainingCredits.toLocaleString()} left</span>
                            </div>
                            {periodEnd && (
                              <p className="text-sm text-muted-foreground">
                                {totalCredits.toLocaleString()} credits reset on {periodEnd}
                              </p>
                            )}
                          </div>
                        )}

                        <div className="pt-4 border-t border-border/50">
                          <p className="text-sm text-muted-foreground">
                            Current plan: <span className="font-semibold text-foreground">{currentPlanName}</span>
                          </p>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Auto-renew Toggle - Only show for paid subscriptions */}
                  {isPaidSubscription && (
                    <div className="px-8">
                      <div className="bg-secondary/20 border border-border/50 rounded-lg p-4">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <RefreshCw className="h-5 w-5 text-primary" />
                            <div>
                              <p className="text-sm font-medium text-foreground">Auto-renew</p>
                              <p className="text-xs text-muted-foreground mt-0.5">
                                {autoRenew
                                  ? "Your subscription will automatically renew"
                                  : "Your subscription will not renew automatically"}
                              </p>
                            </div>
                          </div>
                          <Switch
                            checked={autoRenew}
                            onCheckedChange={handleToggleAutoRenew}
                            disabled={isTogglingAutoRenew}
                          />
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Action Buttons */}
                  <div className="px-8 py-6">
                    {/* FREE plan: Only show Upgrade button */}
                    {(!subscriptionData?.subscription || currentPlanName === "Free") && (
                      <Button
                        onClick={() => window.open('/upgrade', '_blank')}
                        className="w-full h-12 text-base bg-primary hover:bg-primary/90"
                      >
                        Upgrade Plan
                      </Button>
                    )}

                    {/* Paid subscription: Show both Cancel and Upgrade buttons */}
                    {subscriptionData?.subscription && currentPlanName !== "Free" && (
                      <div className="flex gap-3">
                        {/* Cancel button on the left */}
                        <Button
                          variant="outline"
                          onClick={() => setShowCancelDialog(true)}
                          disabled={isCanceling}
                          className="flex-1 h-12 text-base border-destructive/50 text-destructive hover:bg-destructive/10"
                        >
                          <AlertTriangle className="h-4 w-4 mr-2" />
                          {isCanceling ? "Đang hủy..." : "Cancel Subscription"}
                        </Button>

                        {/* Upgrade button on the right */}
                        <Button
                          onClick={() => window.open('/upgrade', '_blank')}
                          className="flex-1 h-12 text-base bg-primary hover:bg-primary/90"
                        >
                          Upgrade Plan
                        </Button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {activeTab === "theme" && (
              <div className="flex-1 flex flex-col overflow-y-auto min-h-0">
                <div className="p-8 pb-6">
                  <h2 className="text-2xl font-semibold">Theme</h2>
                </div>

                {/* Theme Options */}
                <div className="px-8 py-6 border-t">
                  <h3 className="text-base font-normal mb-6">Appearance</h3>

                  <div className="grid grid-cols-3 gap-4">
                    {/* Light Theme */}
                    <button
                      onClick={() => setTheme("light")}
                      className={cn(
                        "flex flex-col items-center gap-3 p-4 rounded-lg border-2 transition-all",
                        theme === "light"
                          ? "border-primary bg-primary/5"
                          : "border-border hover:border-primary/50"
                      )}
                    >
                      <div className="w-full h-24 rounded-md bg-white border flex items-center justify-center">
                        <Sun className="h-8 w-8 text-yellow-500" />
                      </div>
                      <span className="text-sm font-medium">Light</span>
                    </button>

                    {/* Dark Theme */}
                    <button
                      onClick={() => setTheme("dark")}
                      className={cn(
                        "flex flex-col items-center gap-3 p-4 rounded-lg border-2 transition-all",
                        theme === "dark"
                          ? "border-primary bg-primary/5"
                          : "border-border hover:border-primary/50"
                      )}
                    >
                      <div className="w-full h-24 rounded-md bg-slate-900 border flex items-center justify-center">
                        <Moon className="h-8 w-8 text-blue-400" />
                      </div>
                      <span className="text-sm font-medium">Dark</span>
                    </button>

                    {/* System Theme */}
                    <button
                      onClick={() => setTheme("system")}
                      className={cn(
                        "flex flex-col items-center gap-3 p-4 rounded-lg border-2 transition-all",
                        theme === "system"
                          ? "border-primary bg-primary/5"
                          : "border-border hover:border-primary/50"
                      )}
                    >
                      <div className="w-full h-24 rounded-md bg-gradient-to-r from-white to-slate-900 border flex items-center justify-center">
                        <Monitor className="h-8 w-8 text-foreground" />
                      </div>
                      <span className="text-sm font-medium">System</span>
                    </button>
                  </div>

                  <p className="text-xs text-muted-foreground mt-4">
                    {theme === "system"
                      ? "Automatically switch between light and dark mode based on your system preference"
                      : `Currently using ${theme} theme`
                    }
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </DialogContent>

      {/* Cancel Subscription Confirmation Dialog */}
      <Dialog open={showCancelDialog} onOpenChange={setShowCancelDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-destructive">
              <AlertTriangle className="h-5 w-5" />
              Cancel Subscription
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Bạn có chắc muốn hủy subscription? Gói dịch vụ sẽ vẫn hoạt động đến hết thời hạn hiện tại.
            </p>
            <div className="flex gap-3 justify-end">
              <Button
                variant="outline"
                onClick={() => setShowCancelDialog(false)}
                disabled={isCanceling}
              >
                Hủy bỏ
              </Button>
              <Button
                variant="destructive"
                onClick={handleCancelSubscription}
                disabled={isCanceling}
              >
                {isCanceling ? "Đang hủy..." : "Xác nhận"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Avatar Upload Dialog */}
      <AvatarUploadDialog
        open={avatarDialogOpen}
        onOpenChange={setAvatarDialogOpen}
        onSuccess={() => {
          queryClient.invalidateQueries({ queryKey: ["profile"] })
        }}
      />
    </Dialog>
  )
}

