import { Home, LayoutDashboard, FolderKanban, TrendingUp, Settings, X } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'
import { ROUTES } from '@/core/constants/routes'
import { cn } from '@/lib/utils'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet.jsx'

const navigation = [
  { name: 'Dashboard', href: ROUTES.DASHBOARD, icon: LayoutDashboard },
  { name: 'Projects', href: ROUTES.PROJECTS, icon: FolderKanban },
  { name: 'Metrics', href: '/metrics', icon: TrendingUp },
  { name: 'Settings', href: ROUTES.SETTINGS, icon: Settings },
]

interface MobileNavProps {
  open: boolean
  onClose: () => void
}

export const MobileNav = ({ open, onClose }: MobileNavProps) => {
  const location = useLocation()

  return (
    <Sheet open={open} onOpenChange={onClose}>
      <SheetContent side="left" className="glass-dark w-[280px]">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-lg">V</span>
            </div>
            <span className="text-xl font-bold bg-gradient-to-r from-blue-500 to-purple-600 bg-clip-text text-transparent">
              VibeSDLC
            </span>
          </SheetTitle>
        </SheetHeader>

        <nav className="flex flex-col gap-2 mt-8">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href
            const Icon = item.icon

            return (
              <Link
                key={item.name}
                to={item.href}
                onClick={onClose}
                className={cn(
                  'flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200',
                  isActive
                    ? 'glass-card bg-white/20 text-foreground'
                    : 'text-muted-foreground hover:text-foreground hover:bg-white/10'
                )}
              >
                <Icon className="h-5 w-5" />
                <span className="font-medium">{item.name}</span>
              </Link>
            )
          })}
        </nav>
      </SheetContent>
    </Sheet>
  )
}
