import { User, Settings, LogOut } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/core/contexts/AuthContext'
import { Avatar } from '@/components/ui/avatar.jsx'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu.jsx'
import { ROUTES } from '@/core/constants/routes'

export const UserProfileDropdown = () => {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate(ROUTES.LOGIN)
  }

  const handleProfile = () => {
    navigate(ROUTES.PROFILE)
  }

  const handleSettings = () => {
    navigate(ROUTES.SETTINGS)
  }

  if (!user) return null

  // Get user initials for avatar
  const getInitials = (name: string | null, username: string) => {
    if (name) {
      const parts = name.split(' ')
      if (parts.length >= 2) {
        return `${parts[0][0]}${parts[1][0]}`.toUpperCase()
      }
      return name.substring(0, 2).toUpperCase()
    }
    return username.substring(0, 2).toUpperCase()
  }

  const initials = getInitials(user.fullname, user.username)

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button className="flex items-center gap-3 px-4 py-2 rounded-xl bg-white/40 hover:bg-white/60 backdrop-blur-xl border border-white/30 hover:border-white/50 hover:scale-105 transition-all duration-300 shadow-md hover:shadow-xl cursor-pointer">
          <Avatar className="h-9 w-9 ring-2 ring-white/50 shadow-lg">
            <div className="h-full w-full flex items-center justify-center bg-gradient-to-br from-blue-500 to-purple-600 text-white text-sm font-bold">
              {initials}
            </div>
          </Avatar>
          <div className="hidden md:flex flex-col items-start">
            <span className="text-sm font-semibold text-slate-800">
              {user.fullname || user.username}
            </span>
            <span className="text-xs text-slate-600">{user.email}</span>
          </div>
        </button>
      </DropdownMenuTrigger>

      <DropdownMenuContent className="w-64 bg-white/80 dark:bg-slate-900/80 backdrop-blur-2xl border border-white/30 shadow-2xl" align="end">
        <DropdownMenuLabel className="text-foreground px-4 py-3">
          <div className="flex items-center gap-3">
            <Avatar className="h-12 w-12 ring-2 ring-blue-500/50 shadow-lg">
              <div className="h-full w-full flex items-center justify-center bg-gradient-to-br from-blue-500 to-purple-600 text-white text-lg font-bold">
                {initials}
              </div>
            </Avatar>
            <div className="flex flex-col space-y-1">
              <p className="text-sm font-bold leading-none">
                {user.fullname || user.username}
              </p>
              <p className="text-xs leading-none text-slate-600">
                {user.email}
              </p>
            </div>
          </div>
        </DropdownMenuLabel>

        <DropdownMenuSeparator className="bg-white/20" />

        <DropdownMenuGroup className="p-1">
          <DropdownMenuItem
            onClick={handleProfile}
            className="cursor-pointer hover:bg-blue-500/10 rounded-lg px-3 py-2.5 transition-all duration-200"
          >
            <User className="mr-3 h-4 w-4 text-blue-600" />
            <span className="font-medium">Profile</span>
          </DropdownMenuItem>

          <DropdownMenuItem
            onClick={handleSettings}
            className="cursor-pointer hover:bg-purple-500/10 rounded-lg px-3 py-2.5 transition-all duration-200"
          >
            <Settings className="mr-3 h-4 w-4 text-purple-600" />
            <span className="font-medium">Settings</span>
          </DropdownMenuItem>
        </DropdownMenuGroup>

        <DropdownMenuSeparator className="bg-white/20" />

        <div className="p-1">
          <DropdownMenuItem
            onClick={handleLogout}
            className="cursor-pointer text-red-600 hover:text-red-700 hover:bg-red-500/10 rounded-lg px-3 py-2.5 transition-all duration-200 font-medium"
          >
            <LogOut className="mr-3 h-4 w-4" />
            <span>Log out</span>
          </DropdownMenuItem>
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
