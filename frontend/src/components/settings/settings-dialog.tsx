import { useState } from "react"
import { User, CreditCard, LogOut, Pencil, Info, Sun, Moon, Monitor } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { useAppStore } from "@/stores/auth-store"
import useAuth from "@/hooks/useAuth"
import { useTheme } from "@/components/provider/theme-provider"
import { cn } from "@/lib/utils"

interface SettingsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

type SettingsTab = "profile" | "billing" | "theme"

export function SettingsDialog({ open, onOpenChange }: SettingsDialogProps) {
  const [activeTab, setActiveTab] = useState<SettingsTab>("profile")
  const user = useAppStore((state) => state.user)
  const { logout } = useAuth()
  const { theme, setTheme } = useTheme()

  const handleLogout = () => {
    logout.mutate()
    onOpenChange(false)
  }

  const getInitials = (name: string) => {
    return name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase()
      .slice(0, 2)
  }

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
                  <Avatar className="h-20 w-20 ring-2 ring-primary/20">
                    <AvatarFallback className="bg-[var(--gradient-primary)] text-white text-2xl font-semibold">
                      {getInitials(user?.full_name || "")}
                    </AvatarFallback>
                  </Avatar>
                </div>

                {/* Username Section */}
                <div className="flex items-center justify-between px-8 py-6 border-t">
                  <h3 className="text-base font-normal">Username</h3>
                  <div className="flex items-center gap-3">
                    <span className="text-base">{user?.full_name || ""}</span>
                    <Button variant="ghost" size="icon" className="h-8 w-8">
                      <Pencil className="h-4 w-4" />
                    </Button>
                  </div>
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
                    <div className="bg-secondary/30 rounded-lg p-6">
                      <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-2">
                          <h3 className="text-base font-medium">Credits remaining</h3>
                          <Info className="h-4 w-4 text-muted-foreground" />
                        </div>
                        <span className="text-sm font-medium">7.5 / 7.5</span>
                      </div>

                      <div className="space-y-2 mb-4">
                        <div className="flex items-center gap-3">
                          <div className="flex-1 h-2 bg-secondary rounded-full overflow-hidden">
                            <div className="h-full bg-primary w-full" />
                          </div>
                          <span className="text-sm font-medium">7.5 left</span>
                        </div>
                        <p className="text-sm text-muted-foreground">
                          7.5 daily credits reset on Nov 26
                        </p>
                      </div>

                      <div className="pt-4 border-t border-border/50">
                        <p className="text-sm text-muted-foreground">
                          Current plan: <span className="font-semibold text-foreground">Free</span>
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Upgrade Plan Button */}
                  <div className="px-8 py-6">
                    <Button
                      onClick={() => window.open('/upgrade', '_blank')}
                      className="w-full h-12 text-base bg-primary hover:bg-primary/90"
                    >
                      Upgrade Plan
                    </Button>
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
    </Dialog>
  )
}

