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

// Generate fallback avatar URL from agent human_name using DiceBear API
const generateFallbackAvatarUrl = (name: string, roleType?: string): string => {
  // Role-based colors for visual distinction
  const roleColors: Record<string, string> = {
    team_leader: "6366f1",
    business_analyst: "3b82f6",
    developer: "22c55e",
    tester: "f59e0b",
  }
  const bgColor = roleColors[roleType || ""] || "6366f1"
  return `https://api.dicebear.com/7.x/initials/svg?seed=${encodeURIComponent(name)}&chars=2&backgroundColor=${bgColor}`
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

  // Get avatar URL - prefer persona_avatar, fallback to generated
  const avatarUrl = agent.persona_avatar || generateFallbackAvatarUrl(agent.human_name, agent.role_type)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-sm p-0 gap-0 overflow-hidden rounded-2xl border shadow-2xl">
        {/* Header with theme-aware gradient */}
        <div className="p-5 bg-gradient-to-br from-primary/10 via-primary/5 to-background border-b">
          <div className="flex items-start gap-4">
            {/* Avatar with status indicator */}
            <div className="relative flex-shrink-0">
              <img
                src={avatarUrl}
                alt={agent.human_name}
                className="w-16 h-16 rounded-2xl shadow-lg ring-2 ring-background object-cover"
                onError={(e) => {
                  // Fallback if persona_avatar fails to load
                  e.currentTarget.src = generateFallbackAvatarUrl(agent.human_name, agent.role_type)
                }}
              />
              {/* Status dot overlay */}
              <span 
                className={cn(
                  "absolute -bottom-0.5 -right-0.5 w-4 h-4 rounded-full border-2 border-background",
                  getStatusColor(activity?.status || agent.status)
                )} 
              />
            </div>
            
            <div className="flex-1 min-w-0 pt-0.5">
              <h3 className="font-semibold text-lg truncate">{agent.human_name}</h3>
              <p className="text-sm text-muted-foreground">{getRoleDesignation(agent.role_type)}</p>
              <Badge 
                variant="outline" 
                className={cn(
                  "mt-2 text-xs capitalize",
                  (activity?.status || agent.status) === "busy" && "border-yellow-500 text-yellow-600",
                  (activity?.status || agent.status) === "idle" && "border-green-500 text-green-600",
                  (activity?.status || agent.status) === "error" && "border-red-500 text-red-600"
                )}
              >
                {activity?.status || agent.status}
              </Badge>
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
        <div className="min-h-[200px]">
          {activeTab === "description" ? (
            <div className="p-5 space-y-4">
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-2">About</p>
              {/* Status Message / Description */}
              {isLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-3/4" />
                </div>
              ) : activity?.status_message ? (
                <p className="text-sm leading-relaxed text-foreground">
                  {activity.status_message}
                </p>
              ) : (
                <p className="text-sm text-muted-foreground italic">No description available</p>
              )}
              </div>

              {/* Skills */}
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-2">Skills</p>
                {isLoading ? (
                  <div className="flex gap-1.5 flex-wrap">
                    <Skeleton className="h-6 w-16 rounded-full" />
                    <Skeleton className="h-6 w-20 rounded-full" />
                    <Skeleton className="h-6 w-14 rounded-full" />
                  </div>
                ) : activity?.skills && activity.skills.length > 0 ? (
                  <div className="flex gap-2 flex-wrap">
                    {activity.skills.map((skill, index) => (
                      <Badge key={index} variant="secondary" className="text-xs px-2.5 py-0.5">
                        {skill}
                      </Badge>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground italic">No skills listed</p>
                )}
              </div>
            </div>
          ) : (
            <div className="p-5">
              {/* Recent Activity */}
              {isLoading ? (
                <div className="space-y-3">
                  <Skeleton className="h-10 w-full rounded-lg" />
                  <Skeleton className="h-10 w-full rounded-lg" />
                  <Skeleton className="h-10 w-5/6 rounded-lg" />
                </div>
              ) : activity?.recent_activities && activity.recent_activities.length > 0 ? (
                <div className="space-y-2 max-h-[180px] overflow-y-auto pr-1">
                  {activity.recent_activities.map((item) => (
                    <div 
                      key={item.id} 
                      className="flex items-start gap-3 p-2.5 rounded-lg bg-muted/50 hover:bg-muted transition-colors"
                    >
                      <span className="mt-0.5 flex-shrink-0">{getActivityIcon(item.activity_type)}</span>
                      <span className="flex-1 min-w-0 text-sm text-foreground line-clamp-2">{item.content}</span>
                      <span className="text-xs text-muted-foreground whitespace-nowrap flex-shrink-0">
                        {formatDistanceToNow(new Date(item.created_at), { addSuffix: false, locale: vi })}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-10 text-muted-foreground">
                  <Activity className="w-8 h-8 mb-2 opacity-50" />
                  <p className="text-sm">No recent activity</p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Action Button */}
        <div className="p-4 border-t bg-muted/30">
          <Button onClick={handleMessage} className="w-full gap-2 h-10">
            <MessageCircle className="w-4 h-4" />
            Send Message
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
