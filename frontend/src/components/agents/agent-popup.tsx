import { useEffect, useState } from "react"
import {
  Dialog,
  DialogContent,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import type { AgentPublic } from "@/client/types.gen"
import { useAgentActivity } from "@/queries/agents"
import { formatDistanceToNow } from "date-fns"
import { vi } from "date-fns/locale"
import {
  MessageCircle,
  FileText,
  HelpCircle,
  FileCode,
  Info,
  Activity,
} from "lucide-react"
import { cn } from "@/lib/utils"

interface AgentPopupProps {
  agent: AgentPublic | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onMessage?: (agentName: string) => void
}

// Generate avatar URL from agent human_name using DiceBear API
const generateAvatarUrl = (name: string): string => {
  return `https://api.dicebear.com/7.x/initials/svg?seed=${encodeURIComponent(name)}&chars=2&backgroundColor=6366f1`
}

// Map role_type to user-friendly designation
const getRoleDesignation = (roleType: string): string => {
  const roleMap: Record<string, string> = {
    team_leader: "Team Leader",
    business_analyst: "Business Analyst",
    developer: "Developer",
    tester: "Tester",
  }
  return roleMap[roleType] || roleType
}

// Get status color
const getStatusColor = (status: string): string => {
  switch (status) {
    case "idle":
      return "bg-green-500"
    case "busy":
      return "bg-yellow-500 animate-pulse"
    case "error":
      return "bg-red-500"
    default:
      return "bg-gray-400"
  }
}

// Get activity icon
const getActivityIcon = (type: string) => {
  switch (type) {
    case "question":
      return <HelpCircle className="w-3.5 h-3.5 text-blue-500" />
    case "prd":
    case "artifact":
      return <FileText className="w-3.5 h-3.5 text-purple-500" />
    case "stories":
      return <FileCode className="w-3.5 h-3.5 text-green-500" />
    default:
      return <MessageCircle className="w-3.5 h-3.5 text-gray-500" />
  }
}

export function AgentPopup({
  agent,
  open,
  onOpenChange,
  onMessage,
}: AgentPopupProps) {
  const [activeTab, setActiveTab] = useState<"description" | "activity">("description")
  
  // Fetch activity data when dialog opens
  const { data: activity, isLoading, refetch } = useAgentActivity(agent?.id || "", {
    enabled: open && !!agent?.id,
  })

  // Refetch when dialog opens and reset tab
  useEffect(() => {
    if (open && agent?.id) {
      refetch()
      setActiveTab("description")
    }
  }, [open, agent?.id, refetch])

  if (!agent) return null

  const handleMessage = () => {
    onOpenChange(false)
    onMessage?.(agent.human_name)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-sm p-0 gap-0 overflow-hidden">
        {/* Header */}
        <div className="p-4 bg-gradient-to-br from-primary/5 to-primary/10">
          <div className="flex items-start gap-3">
            <img
              src={generateAvatarUrl(agent.human_name)}
              alt={agent.human_name}
              className="w-14 h-14 rounded-xl shadow-md"
            />
            <div className="flex-1 min-w-0">
              <h3 className="font-semibold text-lg truncate">{agent.human_name}</h3>
              <p className="text-sm text-muted-foreground">{getRoleDesignation(agent.role_type)}</p>
              <div className="flex items-center gap-2 mt-1.5">
                <span className={cn("w-2 h-2 rounded-full", getStatusColor(activity?.status || agent.status))} />
                <span className="text-xs text-muted-foreground capitalize">
                  {activity?.status || agent.status}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b">
          <button
            onClick={() => setActiveTab("description")}
            className={cn(
              "flex-1 flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors",
              activeTab === "description"
                ? "text-primary border-b-2 border-primary"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            <Info className="w-4 h-4" />
            Detail
          </button>
          <button
            onClick={() => setActiveTab("activity")}
            className={cn(
              "flex-1 flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors",
              activeTab === "activity"
                ? "text-primary border-b-2 border-primary"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            <Activity className="w-4 h-4" />
            Activity
          </button>
        </div>

        {/* Tab Content */}
        <div className="min-h-[180px]">
          {activeTab === "description" ? (
            <div className="p-4 space-y-4">
              <p className="text-base font-medium mb-2">Description</p>
              {/* Status Message / Description */}
              {isLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-3/4" />
                </div>
              ) : activity?.status_message ? (
                <p className="text-sm leading-relaxed">
                  {activity.status_message}
                </p>
              ) : (
                <p className="text-sm italic">Chưa có mô tả</p>
              )}

              {/* Skills */}
              <div>
                <p className="text-base font-medium mb-2">Skills</p>
                {isLoading ? (
                  <div className="flex gap-1.5 flex-wrap">
                    <Skeleton className="h-6 w-16 rounded-full" />
                    <Skeleton className="h-6 w-20 rounded-full" />
                    <Skeleton className="h-6 w-14 rounded-full" />
                  </div>
                ) : activity?.skills && activity.skills.length > 0 ? (
                  <div className="flex gap-1.5 flex-wrap">
                    {activity.skills.map((skill, index) => (
                      <Badge key={index} variant="secondary" className="text-xs">
                        {skill}
                      </Badge>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground italic">Chưa có thông tin</p>
                )}
              </div>
            </div>
          ) : (
            <div className="p-4">
              {/* Recent Activity */}
              {isLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-8 w-full" />
                  <Skeleton className="h-8 w-full" />
                  <Skeleton className="h-8 w-5/6" />
                </div>
              ) : activity?.recent_activities && activity.recent_activities.length > 0 ? (
                <div className="space-y-2 max-h-[160px] overflow-y-auto">
                  {activity.recent_activities.map((item) => (
                    <div key={item.id} className="flex items-start gap-2 text-sm">
                      <span className="mt-0.5 flex-shrink-0">{getActivityIcon(item.activity_type)}</span>
                      <span className="flex-1 min-w-0 text-muted-foreground line-clamp-1">{item.content}</span>
                      <span className="text-xs text-muted-foreground whitespace-nowrap flex-shrink-0">
                        {formatDistanceToNow(new Date(item.created_at), { addSuffix: false, locale: vi })}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground italic text-center py-8">
                  Chưa có hoạt động nào
                </p>
              )}
            </div>
          )}
        </div>

        {/* Action Button */}
        <div className="p-4 border-t">
          <Button onClick={handleMessage} className="w-full gap-2">
            <MessageCircle className="w-4 h-4" />
            Nhắn tin
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
