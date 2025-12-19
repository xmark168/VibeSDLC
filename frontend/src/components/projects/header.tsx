import { useLocation, useNavigate } from "@tanstack/react-router"
import {
  ChevronDown,
  CreditCard,
  Home,
  LogOut,
  Monitor,
  Moon,
  Sun,
  User,
} from "lucide-react"
import { useEffect, useState } from "react"
import toast from "react-hot-toast"
import { useTheme } from "@/components/provider/theme-provider"
import { SettingsDialog } from "@/components/settings"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import useAuth from "@/hooks/useAuth"
import { useProfile } from "@/queries/profile"
import { useCurrentSubscription } from "@/queries/subscription"
import { useAppStore } from "@/stores/auth-store"

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
  const { data: subscriptionData } = useCurrentSubscription()
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [defaultTab, setDefaultTab] = useState<string | undefined>(undefined)
  const location = useLocation()
  const navigate = useNavigate()
  // Get avatar URL with fallback
  const avatarUrl =
    import.meta.env.VITE_API_URL + profile?.avatar_url || DEFAULT_AVATAR
  const displayName = profile?.full_name || user?.full_name || ""
  const planName = subscriptionData?.subscription?.plan?.name || "Free"
  useEffect(() => {
    const params = new URLSearchParams(location.search)
    const success = params.get("success")
    const error = params.get("error")
    const provider = params.get("provider")
    const tab = params.get("tab")

    if (success === "account_linked" && provider) {
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
        transform: "translateZ(0)",
        willChange: "transform",
      }}
      className="sticky top-0 z-50 w-full flex items-center border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60"
    >
      <div className="container flex h-16 items-center justify-between px-4 md:px-8">
        {/* Left side - Logo/Brand */}
        <a href="/" className="flex items-center gap-2 cursor-pointer">
          <div className="flex items-center justify-center rounded-lg">
            <img
              src="/assets/images/logo.png"
              alt="VibeSDLC"
              className="h-5 object-contain"
            />
          </div>
        </a>

        {/* Right side - User menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              className="flex items-center gap-2 hover:bg-accent transition-colors focus-visible:ring-0 focus-visible:ring-offset-0 min-w-0"
            >
              <Avatar className="h-8 w-8">
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
                  {planName}
                </span>
              </div>
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>
              <div className="flex flex-col space-y-1">
                <p className="text-sm font-medium leading-none">
                  {user?.full_name}
                </p>
                <p className="text-xs leading-none text-muted-foreground">
                  {user?.email}
                </p>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild className="cursor-pointer">
              <a href="/">
                <Home className="mr-2 h-4 w-4" />
                <span>Homepage</span>
              </a>
            </DropdownMenuItem>
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
        defaultTab={
          defaultTab as "profile" | "security" | "billing" | "theme" | undefined
        }
      />
    </header>
  )
}
