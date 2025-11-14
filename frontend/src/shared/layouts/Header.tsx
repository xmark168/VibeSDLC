import { Home, LayoutDashboard, FolderKanban, TrendingUp, Settings, Menu } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { UserProfileDropdown } from '@/shared/components/UserProfileDropdown'
import { NotificationDropdown } from '@/shared/components/NotificationDropdown'
import { ROUTES } from '@/core/constants/routes'
import { cn } from '@/lib/utils'

const navigation = [
  { name: 'Dashboard', href: ROUTES.DASHBOARD, icon: LayoutDashboard },
  { name: 'Projects', href: ROUTES.PROJECTS, icon: FolderKanban },
  { name: 'Metrics', href: '/metrics', icon: TrendingUp },
  { name: 'Settings', href: ROUTES.SETTINGS, icon: Settings },
]

interface HeaderProps {
  onMenuClick?: () => void
}

export const Header = ({ onMenuClick }: HeaderProps) => {
  const location = useLocation()
  const [isScrolled, setIsScrolled] = useState(false)

  // Handle scroll effect
  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 0)
    }
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  return (
    <header
      className={cn(
        'sticky top-0 z-50 w-full transition-all duration-500',
        isScrolled
          ? 'bg-white/40 dark:bg-slate-900/60 backdrop-blur-3xl border-b border-white/30 shadow-[0_8px_32px_rgba(31,38,135,0.15)]'
          : 'bg-white/30 dark:bg-slate-900/40 backdrop-blur-3xl border-b border-white/20 shadow-lg'
      )}
    >
      {/* Gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-r from-blue-500/5 via-purple-500/5 to-pink-500/5 pointer-events-none"></div>

      <div className="container mx-auto px-4 relative z-10">
        <div className="flex h-18 items-center justify-between py-3">
          {/* Left: Logo + Navigation */}
          <div className="flex items-center gap-8">
            {/* Mobile Menu Button */}
            <button
              onClick={onMenuClick}
              className="lg:hidden p-2.5 rounded-xl bg-white/40 hover:bg-white/60 backdrop-blur-xl border border-white/30 hover:border-white/50 hover:scale-110 transition-all duration-300 shadow-md hover:shadow-xl"
            >
              <Menu className="h-5 w-5 text-slate-700" />
            </button>

            {/* Logo */}
            <Link to={ROUTES.HOME} className="flex items-center gap-3 group">
              <div className="relative">
                {/* Glow effect */}
                <div className="absolute inset-0 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl blur-md opacity-50 group-hover:opacity-75 transition-opacity duration-300"></div>
                <div className="relative w-11 h-11 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg group-hover:shadow-2xl group-hover:scale-110 transition-all duration-300">
                  <span className="text-white font-bold text-xl">V</span>
                </div>
              </div>
              <div className="hidden md:block">
                <span className="text-2xl font-bold bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 bg-clip-text text-transparent drop-shadow-sm">
                  VibeSDLC
                </span>
              </div>
            </Link>

            {/* Desktop Navigation */}
            <nav className="hidden lg:flex items-center gap-2">
              {navigation.map((item) => {
                const isActive = location.pathname === item.href
                const Icon = item.icon

                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    className={cn(
                      'flex items-center gap-2.5 px-5 py-2.5 rounded-xl transition-all duration-300 relative overflow-hidden group',
                      isActive
                        ? 'bg-white/50 dark:bg-slate-800/50 backdrop-blur-xl border border-white/60 text-foreground shadow-md'
                        : 'text-slate-600 hover:text-foreground hover:bg-white/30 hover:backdrop-blur-xl border border-transparent hover:border-white/30'
                    )}
                  >
                    {isActive && (
                      <>
                        <div className="absolute inset-0 bg-gradient-to-r from-blue-500/10 via-purple-500/10 to-pink-500/10"></div>
                        <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-blue-500 via-purple-500 to-pink-600"></div>
                      </>
                    )}
                    <Icon className={cn(
                      'h-4 w-4 transition-all duration-300',
                      isActive ? 'text-blue-600 scale-110' : 'group-hover:scale-110 group-hover:text-blue-600'
                    )} />
                    <span className={cn(
                      'text-sm font-semibold relative z-10',
                      isActive && 'bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent'
                    )}>
                      {item.name}
                    </span>
                    {!isActive && (
                      <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-blue-500 to-purple-600 scale-x-0 group-hover:scale-x-100 transition-transform duration-300"></div>
                    )}
                  </Link>
                )
              })}
            </nav>
          </div>

          {/* Right: Notifications + Profile */}
          <div className="flex items-center gap-3">
            <NotificationDropdown />
            <UserProfileDropdown />
          </div>
        </div>
      </div>
    </header>
  )
}
