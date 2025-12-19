import { CheckCircle, Clock, Crown } from "lucide-react"
import { Badge } from "@/components/ui/badge"

interface ConversationOwnerBadgeProps {
  agentName: string
  isOwner: boolean
  status: "active" | "thinking" | "waiting" | "completed"
}

export function ConversationOwnerBadge({
  agentName,
  isOwner,
  status,
}: ConversationOwnerBadgeProps) {
  if (!isOwner) return null

  const statusConfig = {
    active: {
      icon: Crown,
      color:
        "bg-yellow-500/10 text-yellow-600 dark:text-yellow-400 border-yellow-500/20",
      pulse: true,
      label: "Leading Conversation",
    },
    thinking: {
      icon: Clock,
      color:
        "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20",
      pulse: true,
      label: "Processing",
    },
    waiting: {
      icon: Clock,
      color:
        "bg-gray-500/10 text-gray-600 dark:text-gray-400 border-gray-500/20",
      pulse: false,
      label: "Waiting for input",
    },
    completed: {
      icon: CheckCircle,
      color:
        "bg-green-500/10 text-green-600 dark:text-green-400 border-green-500/20",
      pulse: false,
      label: "Completed",
    },
  }

  const config = statusConfig[status]
  const Icon = config.icon

  return (
    <div className="flex items-center gap-2">
      <Badge
        variant="outline"
        className={`${config.color} flex items-center gap-1.5 px-2 py-1 ${config.pulse ? "animate-pulse" : ""}`}
      >
        <Icon className="w-3.5 h-3.5" />
        <span className="text-xs font-semibold">{config.label}</span>
      </Badge>
    </div>
  )
}
