import { Button } from "@/components/ui/button";
import { Menu, X, User, LogOut, LayoutDashboard, ChevronDown, CreditCard, Sun, Moon, Monitor } from "lucide-react";
import { useState } from "react";
import { useAppStore } from "@/stores/auth-store";
import { Link } from "@tanstack/react-router";
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
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import useAuth from "@/hooks/useAuth";
import { useTheme } from "@/components/provider/theme-provider";
import { SettingsDialog } from "@/components/settings";
import { useProfile } from "@/queries/profile";

const navItems = [
  { title: "Home", path: "#" },
  { title: "AI Agents", path: "#agents" },
  { title: "Features", path: "#features" },
  { title: "Testimonials", path: "#testimonials" },
];

const scrollToSection = (e: React.MouseEvent<HTMLAnchorElement>, path: string) => {
  e.preventDefault();
  if (path === "#") {
    window.scrollTo({ top: 0, behavior: "smooth" });
  } else {
    const element = document.querySelector(path);
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }
};

export const Header = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [defaultTab, setDefaultTab] = useState<string | undefined>(undefined);
  const user = useAppStore((state) => state.user);
  const isLoggedIn = !!user;
  const { logout } = useAuth();
  const { theme, setTheme } = useTheme();
  const { data: profile } = useProfile();

  const DEFAULT_AVATAR = "https://github.com/shadcn.png";
  const avatarUrl = profile?.avatar_url 
    ? `${import.meta.env.VITE_API_URL}${profile.avatar_url}`
    : DEFAULT_AVATAR;

  const getInitials = (name: string) => {
    return name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);
  };

  const handleLogout = () => {
    logout.mutate();
  };

  const handleViewProfile = () => {
    setSettingsOpen(true);
    setDefaultTab("profile");
  };

  const handleBilling = () => {
    setSettingsOpen(true);
    setDefaultTab("billing");
  };

  return (
    <header className="sticky top-0 z-50 w-full bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 items-center justify-between px-4 md:px-8">
        {/* Logo */}
        <a
          href="/"
          className="flex items-center cursor-pointer"
        >
          <img src="/assets/images/logo.png" alt="VibeSDLC" className="h-36 w-36 object-contain" />
          {/* <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary">
            <span className="text-primary-foreground font-bold text-sm">VS</span>
          </div>
          <span className="ml-2 text-lg font-semibold text-foreground">VibeSDLC</span> */}
        </a>

        {/* Desktop Navigation */}
        <nav className="hidden md:flex items-center space-x-8">
          {navItems.map((item) => (
            <a
              key={item.path}
              href={item.path}
              onClick={(e) => scrollToSection(e, item.path)}
              className="text-sm font-medium text-muted-foreground transition-colors hover:text-foreground cursor-pointer"
            >
              {item.title}
            </a>
          ))}
        </nav>

        {/* Login/User Menu - Desktop */}
        <div className="hidden md:block">
          {isLoggedIn ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="flex items-center gap-2 focus-visible:ring-0 focus-visible:ring-offset-0">
                  <Avatar className="h-8 w-8">
                    <AvatarImage src={avatarUrl} alt={user?.full_name || ""} />
                    <AvatarFallback className="bg-primary text-primary-foreground text-sm font-semibold">
                      {getInitials(user?.full_name || "")}
                    </AvatarFallback>
                  </Avatar>
                  <span className="text-sm font-medium">{user?.full_name}</span>
                  <ChevronDown className="h-4 w-4 text-muted-foreground" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel>
                  <div className="flex flex-col space-y-1">
                    <p className="text-sm font-medium leading-none">{user?.full_name}</p>
                    <p className="text-xs leading-none text-muted-foreground">
                      {user?.email}
                    </p>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild className="cursor-pointer">
                  <Link to="/projects">
                    <LayoutDashboard className="mr-2 h-4 w-4" />
                    <span>Projects</span>
                  </Link>
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
          ) : (
            <Button variant="default" size="sm" className="rounded-full px-6" asChild>
              <a href="/login">Sign in</a>
            </Button>
          )}
        </div>

        <button
          className="md:hidden inline-flex items-center justify-center p-2 text-muted-foreground hover:bg-accent hover:text-foreground"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
        >
          {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>
      {mobileMenuOpen && (
        <div className="md:hidden border-t bg-background">
          <nav className="container flex flex-col space-y-4 px-4 py-6">
            {navItems.map((item) => (
              <a
                key={item.path}
                href={item.path}
                onClick={(e) => {
                  scrollToSection(e, item.path);
                  setMobileMenuOpen(false);
                }}
                className="text-sm font-medium text-muted-foreground transition-colors hover:text-foreground cursor-pointer"
              >
                {item.title}
              </a>
            ))}
            {isLoggedIn ? (
              <>
                <div className="pt-2 pb-2 border-t">
                  <p className="text-sm font-medium">{user?.full_name}</p>
                  <p className="text-xs text-muted-foreground">{user?.email}</p>
                </div>
                <Button variant="default" size="sm" className="w-full" asChild>
                  <Link to="/projects">
                    <LayoutDashboard className="w-4 h-4 mr-2" />
                    Projects
                  </Link>
                </Button>
                <Button 
                  variant="outline" 
                  size="sm" 
                  className="w-full text-destructive hover:text-destructive" 
                  onClick={handleLogout}
                >
                  <LogOut className="w-4 h-4 mr-2" />
                  Logout
                </Button>
              </>
            ) : (
              <Button variant="default" size="sm" className="w-full" asChild>
                <a href="/login">Sign in</a>
              </Button>
            )}
          </nav>
        </div>
      )}

      <SettingsDialog
        open={settingsOpen}
        onOpenChange={setSettingsOpen}
        defaultTab={defaultTab as "profile" | "security" | "billing" | "theme" | undefined}
      />
    </header>
  );
};
