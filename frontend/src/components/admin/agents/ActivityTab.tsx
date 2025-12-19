import { formatDistanceToNow } from "date-fns"
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  Filter,
  Loader2,
  Pause,
  Play,
  RefreshCw,
  Server,
  User,
  XCircle,
  Zap,
} from "lucide-react"
import { useRef, useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useAgentExecutions, useSystemStatus } from "@/queries/agents"
import type { AgentExecutionRecord } from "@/types"

interface ActivityEvent {
  id: string
  type:
    | "execution_started"
    | "execution_completed"
    | "execution_failed"
    | "agent_spawned"
    | "agent_terminated"
    | "system_event"
  timestamp: string
  agentName: string
  agentType: string
  message: string
  details?: {
    tokens?: number
    llmCalls?: number
    duration?: number | null
  }
  status: "success" | "error" | "warning" | "info" | "pending"
}

function executionToActivity(execution: AgentExecutionRecord): ActivityEvent {
  const isCompleted = execution.status === "completed"
  const isFailed = execution.status === "failed"
  const isRunning = execution.status === "running"
  const isPending = execution.status === "pending"

  let type: ActivityEvent["type"] = "execution_started"
  let status: ActivityEvent["status"] = "info"
  let message = ""

  if (isCompleted) {
    type = "execution_completed"
    status = "success"
    message = `Task completed in ${execution.duration_ms ? `${(execution.duration_ms / 1000).toFixed(1)}s` : "N/A"}`
  } else if (isFailed) {
    type = "execution_failed"
    status = "error"
    message = execution.error_message || "Task failed"
  } else if (isRunning) {
    type = "execution_started"
    status = "pending"
    message = "Task in progress..."
  } else if (isPending) {
    type = "execution_started"
    status = "info"
    message = "Task queued"
  }

  return {
    id: execution.id,
    type,
    timestamp: execution.started_at || execution.created_at,
    agentName: execution.agent_name,
    agentType: execution.agent_type,
    message,
    details: {
      tokens: execution.token_used,
      llmCalls: execution.llm_calls,
      duration: execution.duration_ms,
    },
    status,
  }
}

export function ActivityTab() {
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [filter, setFilter] = useState<string>("all")
  const [searchTerm, setSearchTerm] = useState("")
  const scrollRef = useRef<HTMLDivElement>(null)

  const {
    data: executions,
    isLoading,
    refetch,
  } = useAgentExecutions(
    { limit: 100 },
    { enabled: true, refetchInterval: autoRefresh ? 5000 : undefined },
  )

  const { data: systemStatus } = useSystemStatus({
    refetchInterval: autoRefresh ? 5000 : undefined,
  })

  const activities: ActivityEvent[] = (executions || [])
    .map(executionToActivity)
    .sort(
      (a, b) =>
        new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
    )

  const filteredActivities = activities.filter((activity) => {
    if (filter !== "all" && activity.status !== filter) return false
    if (searchTerm) {
      const search = searchTerm.toLowerCase()
      return (
        activity.agentName.toLowerCase().includes(search) ||
        activity.agentType.toLowerCase().includes(search) ||
        activity.message.toLowerCase().includes(search)
      )
    }
    return true
  })

  const getStatusIcon = (status: ActivityEvent["status"]) => {
    switch (status) {
      case "success":
        return <CheckCircle className="w-4 h-4 text-green-500" />
      case "error":
        return <XCircle className="w-4 h-4 text-red-500" />
      case "warning":
        return <AlertTriangle className="w-4 h-4 text-yellow-500" />
      case "pending":
        return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
      default:
        return <Activity className="w-4 h-4 text-gray-500" />
    }
  }

  const getActivityIcon = (type: ActivityEvent["type"]) => {
    switch (type) {
      case "execution_started":
        return <Play className="w-3 h-3" />
      case "execution_completed":
        return <CheckCircle className="w-3 h-3" />
      case "execution_failed":
        return <XCircle className="w-3 h-3" />
      case "agent_spawned":
        return <User className="w-3 h-3" />
      case "agent_terminated":
        return <Pause className="w-3 h-3" />
      case "system_event":
        return <Server className="w-3 h-3" />
      default:
        return <Activity className="w-3 h-3" />
    }
  }

  const stats = {
    total: activities.length,
    success: activities.filter((a) => a.status === "success").length,
    failed: activities.filter((a) => a.status === "error").length,
    running: activities.filter((a) => a.status === "pending").length,
  }

  return (
    <div className="space-y-4">
      {/* System Status Banner */}
      {systemStatus && systemStatus.status !== "running" && (
        <Card
          className={`border-2 ${
            systemStatus.status === "paused"
              ? "border-yellow-500 bg-yellow-50"
              : systemStatus.status === "maintenance"
                ? "border-orange-500 bg-orange-50"
                : "border-red-500 bg-red-50"
          }`}
        >
          <CardContent className="py-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertTriangle
                className={`w-5 h-5 ${
                  systemStatus.status === "paused"
                    ? "text-yellow-600"
                    : systemStatus.status === "maintenance"
                      ? "text-orange-600"
                      : "text-red-600"
                }`}
              />
              <span className="font-medium">
                System {systemStatus.status.toUpperCase()}
                {systemStatus.maintenance_message &&
                  `: ${systemStatus.maintenance_message}`}
              </span>
            </div>
            <Badge variant="outline">
              {systemStatus.total_agents} agents | {systemStatus.active_pools}{" "}
              pools
            </Badge>
          </CardContent>
        </Card>
      )}

      {/* Header with Controls */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Activity Stream</h2>
          <p className="text-muted-foreground">
            Real-time agent activity and execution logs
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant={autoRefresh ? "default" : "outline"}
            size="sm"
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            {autoRefresh ? (
              <>
                <Pause className="w-4 h-4 mr-2" />
                Auto-refresh ON
              </>
            ) : (
              <>
                <Play className="w-4 h-4 mr-2" />
                Auto-refresh OFF
              </>
            )}
          </Button>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">
                  Total Activities
                </p>
                <p className="text-2xl font-bold">{stats.total}</p>
              </div>
              <Activity className="w-8 h-8 text-muted-foreground/50" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Successful</p>
                <p className="text-2xl font-bold text-green-600">
                  {stats.success}
                </p>
              </div>
              <CheckCircle className="w-8 h-8 text-green-500/50" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Failed</p>
                <p className="text-2xl font-bold text-red-600">
                  {stats.failed}
                </p>
              </div>
              <XCircle className="w-8 h-8 text-red-500/50" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">In Progress</p>
                <p className="text-2xl font-bold text-blue-600">
                  {stats.running}
                </p>
              </div>
              <Loader2 className="w-8 h-8 text-blue-500/50 animate-spin" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-muted-foreground" />
              <span className="text-sm font-medium">Filters:</span>
            </div>
            <Select value={filter} onValueChange={setFilter}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="success">Success</SelectItem>
                <SelectItem value="error">Failed</SelectItem>
                <SelectItem value="pending">In Progress</SelectItem>
                <SelectItem value="info">Queued</SelectItem>
              </SelectContent>
            </Select>
            <Input
              placeholder="Search agent or message..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="max-w-xs"
            />
            <span className="text-sm text-muted-foreground">
              {filteredActivities.length} activities
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Activity Stream */}
      <Card>
        <CardHeader>
          <CardTitle>Live Activity Feed</CardTitle>
          <CardDescription>
            {autoRefresh ? "Updating every 5 seconds" : "Auto-refresh paused"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin" />
            </div>
          ) : filteredActivities.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Activity className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>No activities to display</p>
            </div>
          ) : (
            <ScrollArea className="h-[500px] pr-4" ref={scrollRef}>
              <div className="space-y-3">
                {filteredActivities.map((activity) => (
                  <div
                    key={activity.id}
                    className={`flex items-start gap-3 p-3 rounded-lg border transition-colors ${
                      activity.status === "pending"
                        ? "bg-blue-50/50 border-blue-200"
                        : activity.status === "error"
                          ? "bg-red-50/50 border-red-200"
                          : activity.status === "success"
                            ? "bg-green-50/50 border-green-200"
                            : "bg-muted/30"
                    }`}
                  >
                    <div className="mt-0.5">
                      {getStatusIcon(activity.status)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-medium">
                          {activity.agentName}
                        </span>
                        <Badge variant="outline" className="text-xs">
                          {activity.agentType}
                        </Badge>
                        <span className="text-xs text-muted-foreground flex items-center gap-1">
                          {getActivityIcon(activity.type)}
                          {activity.type.replace(/_/g, " ")}
                        </span>
                      </div>
                      <p className="text-sm text-muted-foreground mt-1">
                        {activity.message}
                      </p>
                      {activity.details &&
                        (activity.details.tokens ||
                          activity.details.llmCalls) && (
                          <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
                            {activity.details.tokens && (
                              <span className="flex items-center gap-1">
                                <Zap className="w-3 h-3" />
                                {activity.details.tokens.toLocaleString()}{" "}
                                tokens
                              </span>
                            )}
                            {activity.details.llmCalls && (
                              <span>{activity.details.llmCalls} LLM calls</span>
                            )}
                          </div>
                        )}
                    </div>
                    <span className="text-xs text-muted-foreground whitespace-nowrap">
                      {formatDistanceToNow(new Date(activity.timestamp), {
                        addSuffix: true,
                      })}
                    </span>
                  </div>
                ))}
              </div>
            </ScrollArea>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
