import { Activity, Bot, ChevronRight, Clock } from "lucide-react"
import {
  type AgentHealth,
  type AgentState,
  generateAgentDisplayName,
} from "@/apis/agents"
import { cn } from "@/lib/utils"
import { AgentStatusBadge, AgentStatusDot } from "./agent-status-badge"

interface AgentCardProps {
  agent: AgentHealth
  poolName?: string
  onClick?: () => void
  compact?: boolean
  className?: string
}

export function AgentCard({
  agent,
  poolName,
  onClick,
  compact = false,
  className,
}: AgentCardProps) {
  const displayName = generateAgentDisplayName(agent.agent_id, agent.role_name)

  if (compact) {
    return (
      <div
        onClick={onClick}
        className={cn(
          "flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer",
          "hover:bg-muted/50 transition-colors duration-200",
          "border border-transparent hover:border-border/50",
          className,
        )}
      >
        <div className="flex items-center gap-2 min-w-0">
          <AgentStatusDot state={agent.state} />
          <span className="text-sm font-medium truncate">{displayName}</span>
        </div>
        <ChevronRight className="w-4 h-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
      </div>
    )
  }

  return (
    <div
      onClick={onClick}
      className={cn(
        "group relative overflow-hidden rounded-xl p-4 cursor-pointer",
        "bg-card border border-border/50",
        "shadow-sm transition-all duration-300",
        "hover:shadow-md hover:-translate-y-0.5 hover:border-border",
        className,
      )}
    >
      {/* Status indicator line at top */}
      <div
        className={cn(
          "absolute top-0 left-0 right-0 h-1 transition-opacity duration-300",
          getStatusGradient(agent.state),
          "opacity-60 group-hover:opacity-100",
        )}
      />

      {/* Header */}
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="flex items-center gap-2 min-w-0">
          <div
            className={cn(
              "w-8 h-8 rounded-lg flex items-center justify-center",
              "bg-primary/10 text-primary",
            )}
          >
            <Bot className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <h4 className="text-sm font-semibold truncate">{displayName}</h4>
            <p className="text-xs text-muted-foreground truncate">
              {agent.role_name}
            </p>
          </div>
        </div>
        <AgentStatusBadge state={agent.state} size="sm" />
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="flex items-center gap-1.5 text-muted-foreground">
          <Clock className="w-3 h-3" />
          <span>{formatUptime(agent.uptime_seconds)}</span>
        </div>
        <div className="flex items-center gap-1.5 text-muted-foreground">
          <Activity className="w-3 h-3" />
          <span>{agent.total_executions} runs</span>
        </div>
      </div>

      {/* Success rate indicator */}
      {agent.total_executions > 0 && (
        <div className="mt-3 pt-3 border-t border-border/50">
          <div className="flex items-center justify-between text-xs mb-1">
            <span className="text-muted-foreground">Success rate</span>
            <span className={getSuccessRateColor(agent.success_rate)}>
              {(agent.success_rate * 100).toFixed(0)}%
            </span>
          </div>
          <div className="h-1.5 bg-muted rounded-full overflow-hidden">
            <div
              className={cn(
                "h-full rounded-full transition-all duration-500",
                getSuccessRateBarColor(agent.success_rate),
              )}
              style={{ width: `${agent.success_rate * 100}%` }}
            />
          </div>
        </div>
      )}

      {/* Pool name if provided */}
      {poolName && (
        <div className="mt-2 pt-2 border-t border-border/50">
          <span className="text-xs text-muted-foreground">
            Pool: {poolName}
          </span>
        </div>
      )}
    </div>
  )
}

function getStatusGradient(state: AgentState): string {
  const gradients: Record<AgentState, string> = {
    idle: "bg-gradient-to-r from-green-500 to-emerald-400",
    busy: "bg-gradient-to-r from-yellow-500 to-orange-400",
    running: "bg-gradient-to-r from-yellow-500 to-orange-400",
    error: "bg-gradient-to-r from-red-500 to-rose-400",
    terminated: "bg-gradient-to-r from-red-400 to-rose-300",
    starting: "bg-gradient-to-r from-blue-500 to-cyan-400",
    stopping: "bg-gradient-to-r from-orange-500 to-amber-400",
    stopped: "bg-gradient-to-r from-gray-500 to-slate-400",
    created: "bg-gradient-to-r from-gray-400 to-slate-300",
  }
  return gradients[state] || "bg-gradient-to-r from-gray-500 to-slate-400"
}

function formatUptime(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`
  if (seconds < 86400) return `${Math.round(seconds / 3600)}h`
  return `${Math.round(seconds / 86400)}d`
}

function getSuccessRateColor(rate: number): string {
  if (rate >= 0.9) return "text-green-500"
  if (rate >= 0.7) return "text-yellow-500"
  return "text-red-500"
}

function getSuccessRateBarColor(rate: number): string {
  if (rate >= 0.9) return "bg-green-500"
  if (rate >= 0.7) return "bg-yellow-500"
  return "bg-red-500"
}
