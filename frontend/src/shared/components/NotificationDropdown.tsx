import { Bell } from 'lucide-react'
import { useState } from 'react'
import { Badge } from '@/components/ui/badge.jsx'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu.jsx'

interface Notification {
  id: string
  title: string
  message: string
  timestamp: string
  read: boolean
  type: 'info' | 'success' | 'warning' | 'error'
}

export const NotificationDropdown = () => {
  // Mock notifications - in a real app, these would come from API/WebSocket
  const [notifications] = useState<Notification[]>([
    {
      id: '1',
      title: 'Story Completed',
      message: 'Story "Add login feature" has been completed',
      timestamp: '5 minutes ago',
      read: false,
      type: 'success',
    },
    {
      id: '2',
      title: 'New Assignment',
      message: 'You have been assigned to "Fix bug #123"',
      timestamp: '1 hour ago',
      read: false,
      type: 'info',
    },
    {
      id: '3',
      title: 'Story Blocked',
      message: 'Story "Database migration" is blocked',
      timestamp: '2 hours ago',
      read: true,
      type: 'warning',
    },
  ])

  const unreadCount = notifications.filter((n) => !n.read).length

  const getNotificationIcon = (type: Notification['type']) => {
    const colors = {
      info: 'text-blue-500',
      success: 'text-green-500',
      warning: 'text-yellow-500',
      error: 'text-red-500',
    }
    return colors[type]
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button className="relative p-2.5 rounded-xl bg-white/40 hover:bg-white/60 backdrop-blur-xl border border-white/30 hover:border-white/50 hover:scale-110 transition-all duration-300 shadow-md hover:shadow-xl cursor-pointer">
          <Bell className="h-5 w-5 text-slate-700" />
          {unreadCount > 0 && (
            <Badge
              variant="destructive"
              className="absolute -top-1 -right-1 h-5 w-5 flex items-center justify-center p-0 text-xs bg-gradient-to-r from-red-500 to-pink-600 border-2 border-white shadow-lg animate-pulse"
            >
              {unreadCount}
            </Badge>
          )}
        </button>
      </DropdownMenuTrigger>

      <DropdownMenuContent className="w-80 bg-white/80 dark:bg-slate-900/80 backdrop-blur-2xl border border-white/30 shadow-2xl" align="end">
        <DropdownMenuLabel className="flex items-center justify-between px-4 py-3">
          <span className="font-bold text-base bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">Notifications</span>
          {unreadCount > 0 && (
            <Badge variant="secondary" className="ml-auto bg-blue-500/20 text-blue-700 border-blue-500/30">
              {unreadCount} new
            </Badge>
          )}
        </DropdownMenuLabel>

        <DropdownMenuSeparator className="bg-white/20" />

        <div className="max-h-[400px] overflow-y-auto">
          {notifications.length === 0 ? (
            <div className="p-4 text-center text-sm text-muted-foreground">
              No notifications
            </div>
          ) : (
            notifications.map((notification) => (
              <DropdownMenuItem
                key={notification.id}
                className={`flex flex-col items-start p-3 cursor-pointer hover:bg-white/40 transition-all duration-200 ${
                  !notification.read ? 'bg-blue-500/10 border-l-2 border-l-blue-500' : ''
                }`}
              >
                <div className="flex items-start gap-2 w-full">
                  <div className={`mt-0.5 ${getNotificationIcon(notification.type)}`}>
                    <Bell className="h-4 w-4" />
                  </div>
                  <div className="flex-1 space-y-1">
                    <p className="text-sm font-semibold leading-none">
                      {notification.title}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {notification.message}
                    </p>
                    <p className="text-xs text-slate-500 font-medium">
                      {notification.timestamp}
                    </p>
                  </div>
                </div>
              </DropdownMenuItem>
            ))
          )}
        </div>

        <DropdownMenuSeparator className="bg-white/20" />

        <DropdownMenuItem className="justify-center cursor-pointer text-sm font-semibold text-blue-600 hover:bg-blue-500/10 transition-all">
          View all notifications
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
