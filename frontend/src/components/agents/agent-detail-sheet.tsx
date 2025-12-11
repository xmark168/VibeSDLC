import { useState } from "react"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetFooter,
} from "@/components/ui/sheet"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { AgentStatusBadge } from "./agent-status-badge"
import { generateAgentDisplayName, type AgentHealth } from "@/apis/agents"
import { useSetAgentIdle, useTerminateAgent } from "@/queries/agents"
import { useProjects } from "@/queries/projects"
import {
  Bot,
  Clock,
  Activity,
  CheckCircle,
  XCircle,
  Percent,
  RefreshCw,
  Power,
  Calendar,
  Heart,
} from "lucide-react"
import { toast } from "@/lib/toast"

interface AgentDetailSheetProps {
  agent: AgentHealth | null
  poolName: string
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function AgentDetailSheet({
  agent,
  poolName,
  open,
  onOpenChange,
}: AgentDetailSheetProps) {
  const [selectedProjectId, setSelectedProjectId] = useState<string>("")

  const setIdleMutation = useSetAgentIdle()
  const terminateMutation = useTerminateAgent()
  const { data: projectsData } = useProjects({ pageSize: 100 })

  if (!agent) return null

  const displayName = generateAgentDisplayName(agent.agent_id, agent.role_name)

  const handleSetIdle = async () => {
    try {
      await setIdleMutation.mutateAsync({
        agentId: agent.agent_id,
        poolName,
      })
      toast.success("Agent set to IDLE state")
    } catch (error) {
      toast.error("Failed to set agent to IDLE")
    }
  }

  const handleTerminate = async () => {
    if (!confirm(`Are you sure you want to terminate ${displayName}?`)) return

    try {
      await terminateMutation.mutateAsync({
        poolName,
        agentId: agent.agent_id,
        graceful: true,
      })
      toast.success("Agent terminated successfully")
      onOpenChange(false)
    } catch (error) {
      toast.error("Failed to terminate agent")
    }
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-[400px] sm:w-[540px] overflow-y-auto">
        <SheetHeader>
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
              <Bot className="w-6 h-6 text-primary" />
            </div>
            <div>
              <SheetTitle className="text-lg">{displayName}</SheetTitle>
              <SheetDescription>{agent.role_name}</SheetDescription>
            </div>
          </div>
        </SheetHeader>

        <div className="mt-6 space-y-6">
          {/* Status Section */}
          <div className="space-y-3">
            <h4 className="text-sm font-medium text-muted-foreground">Status</h4>
            <div className="flex items-center justify-between p-3 bg-muted/30 rounded-lg">
              <span className="text-sm">Current State</span>
              <AgentStatusBadge state={agent.state} size="md" />
            </div>
            <div className="flex items-center justify-between p-3 bg-muted/30 rounded-lg">
              <div className="flex items-center gap-2">
                <Heart className="w-4 h-4 text-muted-foreground" />
                <span className="text-sm">Health</span>
              </div>
              <span className={agent.healthy ? "text-green-500" : "text-red-500"}>
                {agent.healthy ? "Healthy" : "Unhealthy"}
              </span>
            </div>
          </div>

          <Separator />

          {/* Metrics Section */}
          <div className="space-y-3">
            <h4 className="text-sm font-medium text-muted-foreground">Metrics</h4>
            <div className="grid grid-cols-2 gap-3">
              <MetricCard
                icon={Clock}
                label="Uptime"
                value={formatDuration(agent.uptime_seconds)}
              />
              <MetricCard
                icon={Clock}
                label="Idle Time"
                value={formatDuration(agent.idle_seconds)}
              />
              <MetricCard
                icon={Activity}
                label="Total Runs"
                value={agent.total_executions.toString()}
              />
              <MetricCard
                icon={Percent}
                label="Success Rate"
                value={`${(agent.success_rate * 100).toFixed(1)}%`}
                valueColor={getSuccessRateColor(agent.success_rate)}
              />
              <MetricCard
                icon={CheckCircle}
                label="Successful"
                value={agent.successful_executions.toString()}
                valueColor="text-green-500"
              />
              <MetricCard
                icon={XCircle}
                label="Failed"
                value={agent.failed_executions.toString()}
                valueColor={agent.failed_executions > 0 ? "text-red-500" : undefined}
              />
            </div>
          </div>

          <Separator />

          {/* Last Heartbeat */}
          <div className="space-y-3">
            <h4 className="text-sm font-medium text-muted-foreground">Activity</h4>
            <div className="flex items-center justify-between p-3 bg-muted/30 rounded-lg">
              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4 text-muted-foreground" />
                <span className="text-sm">Last Heartbeat</span>
              </div>
              <span className="text-sm text-muted-foreground">
                {agent.last_heartbeat
                  ? new Date(agent.last_heartbeat).toLocaleTimeString()
                  : "Never"}
              </span>
            </div>
          </div>

          <Separator />

          {/* Project Assignment */}
          <div className="space-y-3">
            <h4 className="text-sm font-medium text-muted-foreground">Project Assignment</h4>
            <Select value={selectedProjectId} onValueChange={setSelectedProjectId}>
              <SelectTrigger>
                <SelectValue placeholder="Select a project..." />
              </SelectTrigger>
              <SelectContent>
                {projectsData?.data?.map((project) => (
                  <SelectItem key={project.id} value={project.id}>
                    {project.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              Assign this agent to work on a specific project.
            </p>
          </div>

          <Separator />

          {/* Agent Info */}
          <div className="space-y-3">
            <h4 className="text-sm font-medium text-muted-foreground">Details</h4>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Agent ID</span>
                <span className="font-mono text-xs">{agent.agent_id.slice(0, 8)}...</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Pool</span>
                <span>{poolName}</span>
              </div>
            </div>
          </div>
        </div>

        <SheetFooter className="mt-6">
          <div className="flex gap-2 w-full">
            <Button
              variant="outline"
              className="flex-1"
              onClick={handleSetIdle}
              disabled={agent.state === "idle" || setIdleMutation.isPending}
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Reset to Idle
            </Button>
            <Button
              variant="destructive"
              className="flex-1"
              onClick={handleTerminate}
              disabled={terminateMutation.isPending}
            >
              <Power className="w-4 h-4 mr-2" />
              Terminate
            </Button>
          </div>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  )
}

function MetricCard({
  icon: Icon,
  label,
  value,
  valueColor,
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  value: string
  valueColor?: string
}) {
  return (
    <div className="p-3 bg-muted/30 rounded-lg">
      <div className="flex items-center gap-2 mb-1">
        <Icon className="w-3.5 h-3.5 text-muted-foreground" />
        <span className="text-xs text-muted-foreground">{label}</span>
      </div>
      <p className={`text-lg font-semibold ${valueColor || ""}`}>{value}</p>
    </div>
  )
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`
  if (seconds < 3600) {
    const mins = Math.floor(seconds / 60)
    const secs = Math.round(seconds % 60)
    return `${mins}m ${secs}s`
  }
  if (seconds < 86400) {
    const hours = Math.floor(seconds / 3600)
    const mins = Math.floor((seconds % 3600) / 60)
    return `${hours}h ${mins}m`
  }
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  return `${days}d ${hours}h`
}

function getSuccessRateColor(rate: number): string {
  if (rate >= 0.9) return "text-green-500"
  if (rate >= 0.7) return "text-yellow-500"
  return "text-red-500"
}
