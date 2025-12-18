import {
  ArrowLeft,
  ChevronDown,
  ChevronRight,
  PanelLeftClose,
  PanelRightClose,
  Plus,
  Sparkles,
} from "lucide-react"
import { useState } from "react"
import { useNavigate } from "@tanstack/react-router"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { useQuery } from "@tanstack/react-query"
import { getUserSubscription } from "@/queries/subscription"

interface SidebarProps {
  collapsed: boolean
  onToggle: () => void
}

export function Sidebar({
  collapsed,
  onToggle,
}: SidebarProps) {
  const [myChatsExpanded, setMyChatsExpanded] = useState(true)
  const navigate = useNavigate()

  const { data: subscriptionData } = useQuery({
    queryKey: ["subscription"],
    queryFn: getUserSubscription,
  })

  // Calculate total credits from both wallets
  const subRemainingCredits = subscriptionData?.credit_wallet?.remaining_credits || 0
  const purchasedRemainingCredits = subscriptionData?.purchased_wallet?.remaining_credits || 0
  const totalRemainingCredits = subRemainingCredits + purchasedRemainingCredits

  const subTotalCredits = subscriptionData?.credit_wallet?.total_credits || 0
  const purchasedTotalCredits = subscriptionData?.purchased_wallet?.total_credits || 0
  const totalCredits = subTotalCredits + purchasedTotalCredits

  const creditPercentage = totalCredits > 0 ? (totalRemainingCredits / totalCredits) * 100 : 0

  const handleBackToProjects = () => {
    navigate({ to: "/projects" })
  }

  return (
    <div
      className={cn(
        "flex flex-col bg-sidebar transition-all duration-300 ease-in-out h-full",
        !collapsed ? "w-[280px] relative" : "w-0 overflow-hidden"
      )}
    >
      <div className="flex items-center justify-between p-4">
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={handleBackToProjects}
            className="w-6 h-6 text-sidebar-foreground hover:bg-sidebar-accent"
            title="Back to Projects"
          >
            <ArrowLeft className="w-4 h-4" />
          </Button>
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-sidebar-foreground" />
            <span className="font-semibold text-sidebar-foreground">
              VibeSDLC
            </span>
          </div>
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={onToggle}
          className="w-6 h-6 text-sidebar-foreground hover:bg-sidebar-accent"
        >
          <PanelLeftClose className="w-4 h-4" />
        </Button>
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
            <span>{totalRemainingCredits.toLocaleString()} left</span>
          </div>
          <div className="h-1 bg-sidebar-accent rounded-full overflow-hidden">
            <div
              className="h-full bg-[#8b5cf6] rounded-full"
              style={{ width: `${creditPercentage}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
