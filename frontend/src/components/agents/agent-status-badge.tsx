import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import type { AgentState } from "@/apis/agents"
import { Circle, Loader2, AlertCircle, CheckCircle2, Pause, XCircle } from "lucide-react"

interface AgentStatusBadgeProps {
  state: AgentState
  className?: string
  showIcon?: boolean
  size?: "sm" | "md"
}

const stateConfig: Record<
  AgentState,
  {
    label: string
    variant: "default" | "secondary" | "destructive" | "outline"
    icon: React.ComponentType<{ className?: string }>
    colorClass: string
  }
> = {
  created: {
    label: "Created",
    variant: "outline",
    icon: Circle,
    colorClass: "text-gray-500",
  },
  starting: {
    label: "Starting",
    variant: "secondary",
    icon: Loader2,
    colorClass: "text-blue-500 animate-spin",
  },
  running: {
    label: "Running",
    variant: "secondary",
    icon: Loader2,
    colorClass: "text-yellow-500 animate-spin",
  },
  idle: {
    label: "Idle",
    variant: "default",
    icon: CheckCircle2,
    colorClass: "text-green-500",
  },
  busy: {
    label: "Busy",
    variant: "secondary",
    icon: Loader2,
    colorClass: "text-yellow-500 animate-spin",
  },
  stopping: {
    label: "Stopping",
    variant: "outline",
    icon: Pause,
    colorClass: "text-orange-500",
  },
  stopped: {
    label: "Stopped",
    variant: "outline",
    icon: XCircle,
    colorClass: "text-gray-500",
  },
  error: {
    label: "Error",
    variant: "destructive",
    icon: AlertCircle,
    colorClass: "text-red-500",
  },
  terminated: {
    label: "Terminated",
    variant: "destructive",
    icon: XCircle,
    colorClass: "text-red-400",
  },
}

export function AgentStatusBadge({
  state,
  className,
  showIcon = true,
  size = "sm",
}: AgentStatusBadgeProps) {
  const config = stateConfig[state] || stateConfig.idle
  const Icon = config.icon

  return (
    <Badge
      variant={config.variant}
      className={cn(
        size === "sm" ? "text-xs px-2 py-0.5" : "text-sm px-3 py-1",
        className
      )}
    >
      {showIcon && <Icon className={cn("w-3 h-3", config.colorClass)} />}
      <span>{config.label}</span>
    </Badge>
  )
}

/**
 * Simple dot indicator for compact views
 */
export function AgentStatusDot({
  state,
  className,
}: {
  state: AgentState
  className?: string
}) {
  const colorMap: Record<AgentState, string> = {
    created: "bg-gray-400",
    starting: "bg-blue-400 animate-pulse",
    running: "bg-yellow-400 animate-pulse",
    idle: "bg-green-400",
    busy: "bg-yellow-400 animate-pulse",
    stopping: "bg-orange-400",
    stopped: "bg-gray-400",
    error: "bg-red-500",
    terminated: "bg-red-400",
  }

  return (
    <span
      className={cn(
        "inline-block w-2 h-2 rounded-full",
        colorMap[state] || "bg-gray-400",
        className
      )}
      title={stateConfig[state]?.label || state}
    />
  )
}
