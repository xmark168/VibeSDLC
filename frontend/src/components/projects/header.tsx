import { useState, useEffect } from "react"
import { useLocation, useNavigate } from "@tanstack/react-router"
import { ChevronDown, LogOut, CreditCard, User, Sun, Moon, Monitor } from "lucide-react"
import toast from "react-hot-toast"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
} from "@/components/ui/dropdown-menu"
import { useAppStore } from "@/stores/auth-store"
import useAuth from "@/hooks/useAuth"
import { useTheme } from "@/components/provider/theme-provider"
import { SettingsDialog } from "@/components/settings"
import { useProfile } from "@/queries/profile"

const DEFAULT_AVATAR = "https://github.com/shadcn.png"

interface HeaderProps {
  userName?: string
  userEmail?: string
}

export const HeaderProject = ({
  userName = "John Doe",
  userEmail = "john.doe@example.com",
}: HeaderProps) => {
  const { logout } = useAuth()
  const user = useAppStore((state) => state.user)
  const { theme, setTheme } = useTheme()
  const { data: profile } = useProfile()
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [defaultTab, setDefaultTab] = useState<string | undefined>(undefined)
  const location = useLocation()
  const navigate = useNavigate()

  // Get avatar URL with fallback
  const avatarUrl = import.meta.env.VITE_API_URL + profile?.avatar_url || DEFAULT_AVATAR
  const displayName = profile?.full_name || user?.full_name || ""
  console.log('Profile data:', profile)
  // Handle URL params for opening settings (e.g., after OAuth link callback)
  useEffect(() => {
    const params = new URLSearchParams(location.search)
    const success = params.get("success")
    const error = params.get("error")
    const provider = params.get("provider")
    const tab = params.get("tab")

    if (success === "account_linked" && provider) {
      // toast.success(`${provider.charAt(0).toUpperCase() + provider.slice(1)} account linked successfully!`)
      setDefaultTab(tab || "security")
      setSettingsOpen(true)
      // Clear URL params
      navigate({ to: location.pathname, replace: true })
    } else if (error) {
      toast.error(error.replace(/_/g, " "))
      setDefaultTab(tab || "security")
      setSettingsOpen(true)
      navigate({ to: location.pathname, replace: true })
    }
  }, [location.search, navigate, location.pathname])

  const handleLogout = () => {
    logout.mutate()
  }

  const handleViewProfile = () => {
    setSettingsOpen(true)
  }

  const handleBilling = () => {
    setSettingsOpen(true)
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
    <header
      style={{
        display: "flex",
        justifyContent: "center",
      }}
      className="sticky top-0 z-50 w-full flex items-center border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60"
    >
      <div className="container flex h-16 items-center justify-between px-6">
        {/* Left side - Logo/Brand */}
        <div className="flex items-center gap-2 ml-2">
          <div className="flex items-center justify-center rounded-lg px-3 py-2">
            <span className="text-xl font-bold">VibeSDLC</span>
          </div>
        </div>

        {/* Right side - User menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              className="flex items-center gap-3 hover:bg-accent transition-colors"
            >
              <Avatar
                className="h-8 w-8 ring-2 ring-primary/20"

              >
                <AvatarImage src={avatarUrl} alt={displayName} />
                <AvatarFallback className="bg-[var(--gradient-primary)] text-sm font-semibold">
                  {getInitials(user?.full_name || "")}
                </AvatarFallback>
              </Avatar>
              <div className="hidden md:flex flex-col items-start">
                <span className="text-sm font-medium text-foreground">
                  {user?.full_name || ""}
                </span>

                <span className="text-xs text-muted-foreground">
                  base user
                </span>
              </div>
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>
              <div className="flex flex-col space-y-1">
                <p className="text-sm font-medium leading-none">{userName}</p>
                <p className="text-xs leading-none text-muted-foreground">
                  {userEmail}
                </p>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={handleViewProfile}
              className="cursor-pointer"
            >
              <User className="mr-2 h-4 w-4" />
              <span>Profile</span>
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={handleBilling}
              className="cursor-pointer"
            >
              <CreditCard className="mr-2 h-4 w-4" />
              <span>Plans and Billing</span>
            </DropdownMenuItem>
            <DropdownMenuSub>
              <DropdownMenuSubTrigger className="cursor-pointer">
                <Sun className="mr-2 h-4 w-4" />
                <span>Theme</span>
              </DropdownMenuSubTrigger>
              <DropdownMenuSubContent>
                <DropdownMenuItem
                  onClick={() => setTheme("light")}
                  className="cursor-pointer"
                >
                  <Sun className="mr-2 h-4 w-4" />
                  <span>Light</span>
                  {theme === "light" && (
                    <span className="ml-auto text-xs text-primary">✓</span>
                  )}
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => setTheme("dark")}
                  className="cursor-pointer"
                >
                  <Moon className="mr-2 h-4 w-4" />
                  <span>Dark</span>
                  {theme === "dark" && (
                    <span className="ml-auto text-xs text-primary">✓</span>
                  )}
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => setTheme("system")}
                  className="cursor-pointer"
                >
                  <Monitor className="mr-2 h-4 w-4" />
                  <span>System</span>
                  {theme === "system" && (
                    <span className="ml-auto text-xs text-primary">✓</span>
                  )}
                </DropdownMenuItem>
              </DropdownMenuSubContent>
            </DropdownMenuSub>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={handleLogout}
              className="cursor-pointer text-destructive focus:text-destructive"
            >
              <LogOut className="mr-2 h-4 w-4" />
              <span>Logout</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <SettingsDialog
        open={settingsOpen}
        onOpenChange={setSettingsOpen}
        defaultTab={defaultTab as "profile" | "security" | "billing" | "theme" | undefined}
      />
    </header>
  )
}
