import {
  ChevronDown,
  ChevronRight,
  PanelLeftClose,
  PanelRightClose,
  Plus,
  Sparkles,
} from "lucide-react"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

interface SidebarProps {
  collapsed: boolean
  onToggle: () => void
  hovered: boolean
  onHoverChange: (hovered: boolean) => void
}

export function Sidebar({
  collapsed,
  onToggle,
  hovered,
  onHoverChange,
}: SidebarProps) {
  const [myChatsExpanded, setMyChatsExpanded] = useState(true)


  const _isVisible = !collapsed || hovered

  return (
    <div
      className={cn(
        "flex flex-col bg-sidebar transition-all duration-300 ease-in-out w-[280px] h-full",
        !collapsed
          ? "relative translate-x-0 z-50"
          : hovered
            ? "fixed translate-x-0 z-50"
            : "absolute -translate-x-full z-50",
        hovered && collapsed && "shadow-2xl",
      )}
      onMouseLeave={() => {
        if (collapsed && onHoverChange) {
          onHoverChange(false)
        }
      }}
    >
      <div className="flex items-center justify-between p-4">
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={onToggle}
            className="w-6 h-6 text-sidebar-foreground hover:bg-sidebar-accent"
          >
            {collapsed ? (
              <PanelRightClose className="w-4 h-4" />
            ) : (
              <PanelLeftClose className="w-4 h-4" />
            )}
          </Button>
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-sidebar-foreground" />
            <span className="font-semibold text-sidebar-foreground">
              VibeSDLC
            </span>
          </div>
        </div>
      </div>

      <div className="p-3">
        <Button className="w-full justify-start gap-2 bg-[#6366f1] hover:bg-[#5558e3] text-white rounded-lg">
          <Plus className="w-4 h-4" />
          New Chat
        </Button>
      </div>

      <div className="px-3 pb-2">
        <button className="w-full flex items-center gap-2 px-3 py-2 text-sm text-sidebar-foreground hover:bg-sidebar-accent rounded-lg transition-colors">
          <Sparkles className="w-4 h-4" />
          Go to App World
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-3">
        <button
          onClick={() => setMyChatsExpanded(!myChatsExpanded)}
          className="w-full flex items-center justify-between px-3 py-2 text-sm font-medium text-sidebar-foreground hover:bg-sidebar-accent rounded-lg transition-colors mb-1"
        >
          <span>My Chats</span>
          {myChatsExpanded ? (
            <ChevronDown className="w-4 h-4" />
          ) : (
            <ChevronRight className="w-4 h-4" />
          )}
        </button>

        
      </div>

      <div className="p-3">
        <div className="flex items-center gap-3 px-2 py-2 rounded-lg hover:bg-sidebar-accent cursor-pointer transition-colors">
          <div className="w-8 h-8 rounded-full bg-[#8b5cf6] flex items-center justify-center text-white text-sm font-semibold">
            T
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-sidebar-foreground truncate">
              Tra Do Son
            </p>
            <p className="text-xs text-muted-foreground">Free</p>
          </div>
          <ChevronDown className="w-4 h-4 text-muted-foreground" />
        </div>

        <div className="mt-3 px-2">
          <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
            <span>Credits remaining</span>
            <span>0.32 left</span>
          </div>
          <div className="h-1 bg-sidebar-accent rounded-full overflow-hidden">
            <div
              className="h-full bg-[#8b5cf6] rounded-full"
              style={{ width: "32%" }}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
