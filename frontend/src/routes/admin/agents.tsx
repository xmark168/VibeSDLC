import { useState } from "react"
import { createFileRoute } from "@tanstack/react-router"
import { requireRole } from "@/utils/auth"
import {
  useAgentDashboard,
  useAgentPools,
  useAllAgentHealth,
  useAgentAlerts,
  useSystemStats,
  useAgentExecutions,
  useCreatePool,
  useDeletePool,
  useSpawnAgent,
  useTerminateAgent,
  useSetAgentIdle,
  useStartMonitoring,
  useStopMonitoring,
  useMetricsTimeseries,
  useMetricsAggregated,
  useProcessMetrics,
  useTokenMetrics,
} from "@/queries/agents"
import {
  type PoolResponse,
  type AgentHealth,
  type Alert,
  type AgentState,
  type AgentExecutionRecord,
  generateAgentDisplayName,
  getStateVariant,
  getStateLabel,
} from "@/apis/agents"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  RefreshCw,
  Plus,
  Trash2,
  MoreVertical,
  Play,
  Square,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  Activity,
  Users,
  Server,
  Zap,
  ChevronDown,
  ChevronRight,
  Loader2,
  Heart,
  Timer,
  History,
  FileText,
  BarChart3,
} from "lucide-react"
import { toast } from "sonner"
import { formatDistanceToNow } from "date-fns"
import {
  AgentUtilizationChart,
  ExecutionTrendsChart,
  TokenUsageChart,
  ProcessMetricsChart,
  SuccessRateChart,
  LLMCallsChart,
} from "@/components/charts"
import { TimeRangeSelector, type TimeRange, MetricCard } from "@/components/admin"

export const Route = createFileRoute("/admin/agents")({
  beforeLoad: async () => {
    await requireRole("admin")
  },
  component: AgentAdminPage,
})

function AgentAdminPage() {
  const [activeTab, setActiveTab] = useState("pools")

  // Queries
  const { data: dashboard, isLoading: dashboardLoading, refetch: refetchDashboard } = useAgentDashboard()
  const { data: pools, isLoading: poolsLoading } = useAgentPools()
  const { data: healthData, isLoading: healthLoading } = useAllAgentHealth()
  const { data: alerts, isLoading: alertsLoading } = useAgentAlerts(50)
  const { data: executions, isLoading: executionsLoading } = useAgentExecutions({ limit: 100 })
  const { data: systemStats } = useSystemStats()

  const isLoading = dashboardLoading || poolsLoading || healthLoading

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Agent Management</h1>
          <p className="text-muted-foreground">
            Monitor and manage all agent processes in the system
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => refetchDashboard()}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
          <SystemControls />
        </div>
      </div>

      {/* System Stats Cards */}
      <SystemStatsCards stats={systemStats} isLoading={isLoading} />

      {/* Main Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-6">
          <TabsTrigger value="pools">
            <Server className="w-4 h-4 mr-2" />
            Pools
          </TabsTrigger>
          <TabsTrigger value="agents">
            <Users className="w-4 h-4 mr-2" />
            Agents
          </TabsTrigger>
          <TabsTrigger value="health">
            <Heart className="w-4 h-4 mr-2" />
            Health
          </TabsTrigger>
          <TabsTrigger value="executions">
            <History className="w-4 h-4 mr-2" />
            Executions
          </TabsTrigger>
          <TabsTrigger value="analytics">
            <BarChart3 className="w-4 h-4 mr-2" />
            Analytics
          </TabsTrigger>
          <TabsTrigger value="alerts">
            <AlertTriangle className="w-4 h-4 mr-2" />
            Alerts
            {alerts && alerts.length > 0 && (
              <Badge variant="destructive" className="ml-2 h-5 px-1.5">
                {alerts.length}
              </Badge>
            )}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="pools" className="mt-6">
          <PoolsTab pools={pools || []} healthData={healthData} isLoading={poolsLoading} />
        </TabsContent>

        <TabsContent value="agents" className="mt-6">
          <AgentsTab healthData={healthData} pools={pools || []} isLoading={healthLoading} />
        </TabsContent>

        <TabsContent value="health" className="mt-6">
          <HealthTab healthData={healthData} pools={pools || []} isLoading={healthLoading} />
        </TabsContent>

        <TabsContent value="executions" className="mt-6">
          <ExecutionsTab executions={executions || []} isLoading={executionsLoading} />
        </TabsContent>

        <TabsContent value="analytics" className="mt-6">
          <AnalyticsTab />
        </TabsContent>

        <TabsContent value="alerts" className="mt-6">
          <AlertsTab alerts={alerts || []} isLoading={alertsLoading} />
        </TabsContent>
      </Tabs>
    </div>
  )
}

// ===== System Stats Cards =====
function SystemStatsCards({
  stats,
  isLoading,
}: {
  stats?: {
    total_pools: number
    total_agents: number
    success_rate: number
    recent_alerts: number
    total_executions: number
    uptime_seconds: number
  }
  isLoading: boolean
}) {
  // Fetch 24h metrics for sparklines
  const { data: utilizationData } = useMetricsTimeseries(
    { metric_type: "utilization", time_range: "24h" },
    { refetchInterval: 60000 }
  )

  const { data: executionData } = useMetricsTimeseries(
    { metric_type: "executions", time_range: "24h" },
    { refetchInterval: 60000 }
  )

  const { data: tokenData } = useTokenMetrics({ time_range: "24h" })
  const { data: processData } = useProcessMetrics({ refetchInterval: 30000 })

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {[...Array(4)].map((_, i) => (
          <Card key={i}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <div className="h-4 w-24 bg-muted animate-pulse rounded" />
            </CardHeader>
            <CardContent>
              <div className="h-8 w-16 bg-muted animate-pulse rounded" />
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  // Calculate trends (compare first half vs second half of 24h data)
  const calculateTrend = (data: any[], key: string): number => {
    if (!data || data.length < 2) return 0
    const midpoint = Math.floor(data.length / 2)
    const firstHalf = data.slice(0, midpoint)
    const secondHalf = data.slice(midpoint)

    const firstAvg = firstHalf.reduce((sum, d) => sum + (d[key] || 0), 0) / firstHalf.length
    const secondAvg = secondHalf.reduce((sum, d) => sum + (d[key] || 0), 0) / secondHalf.length

    if (firstAvg === 0) return 0
    return ((secondAvg - firstAvg) / firstAvg) * 100
  }

  // Prepare sparkline data
  const agentTrend = utilizationData?.data.map((d: any) => ({ value: d.total || 0 })) || []
  const agentChange = calculateTrend(utilizationData?.data || [], "total")

  const successTrend = executionData?.data.map((d: any) => ({ value: d.success_rate || 0 })) || []
  const successChange = calculateTrend(executionData?.data || [], "success_rate")

  const tokenTrend = tokenData?.data.map((d) => ({ value: d.total_tokens })) || []
  const tokenChange = tokenData?.data.length > 1
    ? ((tokenData.data[tokenData.data.length - 1].total_tokens - tokenData.data[0].total_tokens) / (tokenData.data[0].total_tokens || 1)) * 100
    : 0

  const processUtilization = processData?.summary.avg_utilization || 0

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <MetricCard
        title="Total Agents"
        value={stats?.total_agents || 0}
        change={agentChange}
        trend={agentTrend}
        icon={<Users className="h-4 w-4 text-muted-foreground" />}
        subtitle="Running instances"
      />

      <MetricCard
        title="Success Rate"
        value={stats?.success_rate ? `${(stats.success_rate * 100).toFixed(1)}%` : "N/A"}
        change={successChange}
        trend={successTrend}
        icon={<Activity className="h-4 w-4 text-muted-foreground" />}
        subtitle={`${stats?.total_executions || 0} executions`}
      />

      <MetricCard
        title="Token Usage (24h)"
        value={tokenData?.summary.total_tokens.toLocaleString() || "0"}
        change={tokenChange}
        trend={tokenTrend}
        icon={<Zap className="h-4 w-4 text-muted-foreground" />}
        subtitle={`$${tokenData?.summary.estimated_total_cost_usd.toFixed(4) || "0.00"} cost`}
      />

      <MetricCard
        title="Process Utilization"
        value={`${processUtilization.toFixed(1)}%`}
        change={undefined}
        icon={<Server className="h-4 w-4 text-muted-foreground" />}
        subtitle={`${processData?.summary.used_capacity || 0}/${processData?.summary.total_capacity || 0} capacity`}
      />
    </div>
  )
}

// ===== System Controls =====
function SystemControls() {
  const startMonitoring = useStartMonitoring()
  const stopMonitoring = useStopMonitoring()

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm">
          <Zap className="w-4 h-4 mr-2" />
          System
          <ChevronDown className="w-4 h-4 ml-2" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent>
        <DropdownMenuItem
          onClick={() => {
            startMonitoring.mutate(30, {
              onSuccess: () => toast.success("Monitoring started"),
              onError: (e) => toast.error(`Failed to start: ${e.message}`),
            })
          }}
        >
          <Play className="w-4 h-4 mr-2" />
          Start Monitoring
        </DropdownMenuItem>
        <DropdownMenuItem
          onClick={() => {
            stopMonitoring.mutate(undefined, {
              onSuccess: () => toast.success("Monitoring stopped"),
              onError: (e) => toast.error(`Failed to stop: ${e.message}`),
            })
          }}
        >
          <Square className="w-4 h-4 mr-2" />
          Stop Monitoring
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

// ===== Pools Tab =====
function PoolsTab({
  pools,
  healthData,
  isLoading,
}: {
  pools: PoolResponse[]
  healthData?: Record<string, AgentHealth[]>
  isLoading: boolean
}) {
  const [expandedPools, setExpandedPools] = useState<Set<string>>(new Set())

  const togglePool = (poolName: string) => {
    setExpandedPools((prev) => {
      const newSet = new Set(prev)
      if (newSet.has(poolName)) {
        newSet.delete(poolName)
      } else {
        newSet.add(poolName)
      }
      return newSet
    })
  }

  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-center">
            <Loader2 className="w-6 h-6 animate-spin" />
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Agent Pools</h2>
        <CreatePoolDialog />
      </div>

      {pools.length === 0 ? (
        <Card>
          <CardContent className="p-6 text-center text-muted-foreground">
            No pools available. Create a pool to get started.
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {pools.map((pool) => (
            <Card key={pool.pool_name}>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="p-0 h-auto"
                      onClick={() => togglePool(pool.pool_name)}
                    >
                      {expandedPools.has(pool.pool_name) ? (
                        <ChevronDown className="w-4 h-4" />
                      ) : (
                        <ChevronRight className="w-4 h-4" />
                      )}
                    </Button>
                    <div>
                      <CardTitle className="text-base">{pool.pool_name}</CardTitle>
                      <CardDescription>{pool.role_class}</CardDescription>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-sm text-right">
                      <div className="font-medium">
                        {pool.idle_agents} idle / {pool.busy_agents} busy
                      </div>
                      <div className="text-muted-foreground">
                        Load: {(pool.load * 100).toFixed(0)}%
                      </div>
                    </div>
                    <PoolActions pool={pool} />
                  </div>
                </div>
              </CardHeader>

              {expandedPools.has(pool.pool_name) && (
                <CardContent className="pt-0">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4 text-sm">
                    <div>
                      <span className="text-muted-foreground">Total Agents:</span>
                      <span className="ml-2 font-medium">{pool.total_agents}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Executions:</span>
                      <span className="ml-2 font-medium">{pool.total_executions}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Success Rate:</span>
                      <span className="ml-2 font-medium">
                        {(pool.success_rate * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Created:</span>
                      <span className="ml-2 font-medium">
                        {formatDistanceToNow(new Date(pool.created_at), { addSuffix: true })}
                      </span>
                    </div>
                  </div>

                  {/* Agents in pool */}
                  {healthData?.[pool.pool_name] && healthData[pool.pool_name].length > 0 && (
                    <div className="border rounded-lg">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Agent</TableHead>
                            <TableHead>State</TableHead>
                            <TableHead>Uptime</TableHead>
                            <TableHead>Executions</TableHead>
                            <TableHead className="w-[100px]">Actions</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {healthData[pool.pool_name].map((agent) => (
                            <TableRow key={agent.agent_id}>
                              <TableCell className="font-medium">
                                {generateAgentDisplayName(agent.agent_id, agent.role_name)}
                              </TableCell>
                              <TableCell>
                                <Badge variant={getStateVariant(agent.state)}>
                                  {getStateLabel(agent.state)}
                                </Badge>
                              </TableCell>
                              <TableCell>{formatUptime(agent.uptime_seconds)}</TableCell>
                              <TableCell>
                                <span className="text-green-600">{agent.successful_executions}</span>
                                {" / "}
                                <span className="text-red-600">{agent.failed_executions}</span>
                              </TableCell>
                              <TableCell>
                                <AgentActions
                                  agent={agent}
                                  poolName={pool.pool_name}
                                />
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  )}
                </CardContent>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

// ===== Create Pool Dialog =====
function CreatePoolDialog() {
  const [open, setOpen] = useState(false)
  const [roleType, setRoleType] = useState<string>("")
  const [poolName, setPoolName] = useState("")
  const createPool = useCreatePool()

  const handleCreate = () => {
    if (!roleType || !poolName) {
      toast.error("Please fill all fields")
      return
    }

    createPool.mutate(
      {
        role_type: roleType as "team_leader" | "business_analyst" | "tester",
        pool_name: poolName,
      },
      {
        onSuccess: () => {
          toast.success(`Pool "${poolName}" created`)
          setOpen(false)
          setRoleType("")
          setPoolName("")
        },
        onError: (e) => toast.error(`Failed to create pool: ${e.message}`),
      }
    )
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">
          <Plus className="w-4 h-4 mr-2" />
          Create Pool
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create Agent Pool</DialogTitle>
          <DialogDescription>
            Create a new pool to manage agents of a specific role type.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label>Role Type</Label>
            <Select value={roleType} onValueChange={setRoleType}>
              <SelectTrigger>
                <SelectValue placeholder="Select role type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="team_leader">Team Leader</SelectItem>
                <SelectItem value="business_analyst">Business Analyst</SelectItem>
                <SelectItem value="tester">Tester</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Pool Name</Label>
            <Input
              value={poolName}
              onChange={(e) => setPoolName(e.target.value)}
              placeholder="e.g., team_leader_pool"
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handleCreate} disabled={createPool.isPending}>
            {createPool.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
            Create
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ===== Pool Actions =====
function PoolActions({ pool }: { pool: PoolResponse }) {
  const deletePool = useDeletePool()
  const spawnAgent = useSpawnAgent()

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm">
          <MoreVertical className="w-4 h-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent>
        <DropdownMenuItem
          onClick={() => {
            spawnAgent.mutate(
              { pool_name: pool.pool_name },
              {
                onSuccess: (res) =>
                  toast.success(`Agent ${res.agent_id.slice(0, 8)} spawned`),
                onError: (e) => toast.error(`Failed to spawn: ${e.message}`),
              }
            )
          }}
        >
          <Plus className="w-4 h-4 mr-2" />
          Spawn Agent
        </DropdownMenuItem>
        <DropdownMenuItem
          className="text-destructive"
          onClick={() => {
            if (confirm(`Delete pool "${pool.pool_name}"?`)) {
              deletePool.mutate(
                { poolName: pool.pool_name, graceful: true },
                {
                  onSuccess: () => toast.success(`Pool "${pool.pool_name}" deleted`),
                  onError: (e) => toast.error(`Failed to delete: ${e.message}`),
                }
              )
            }
          }}
        >
          <Trash2 className="w-4 h-4 mr-2" />
          Delete Pool
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

// ===== Agent Actions =====
function AgentActions({
  agent,
  poolName,
}: {
  agent: AgentHealth
  poolName: string
}) {
  const terminateAgent = useTerminateAgent()
  const setAgentIdle = useSetAgentIdle()

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm">
          <MoreVertical className="w-4 h-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent>
        <DropdownMenuItem
          onClick={() => {
            setAgentIdle.mutate(
              { agentId: agent.agent_id, poolName },
              {
                onSuccess: () => toast.success("Agent set to idle"),
                onError: (e) => toast.error(`Failed: ${e.message}`),
              }
            )
          }}
          disabled={agent.state === "idle"}
        >
          <Clock className="w-4 h-4 mr-2" />
          Set Idle
        </DropdownMenuItem>
        <DropdownMenuItem
          className="text-destructive"
          onClick={() => {
            if (confirm("Terminate this agent?")) {
              terminateAgent.mutate(
                { poolName, agentId: agent.agent_id, graceful: true },
                {
                  onSuccess: () => toast.success("Agent terminated"),
                  onError: (e) => toast.error(`Failed: ${e.message}`),
                }
              )
            }
          }}
        >
          <XCircle className="w-4 h-4 mr-2" />
          Terminate
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

// ===== Agents Tab =====
function AgentsTab({
  healthData,
  pools,
  isLoading,
}: {
  healthData?: Record<string, AgentHealth[]>
  pools: PoolResponse[]
  isLoading: boolean
}) {
  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-center">
            <Loader2 className="w-6 h-6 animate-spin" />
          </div>
        </CardContent>
      </Card>
    )
  }

  // Flatten all agents with their pool names
  const allAgents: Array<{ agent: AgentHealth; poolName: string }> = []
  if (healthData) {
    Object.entries(healthData).forEach(([poolName, agents]) => {
      agents.forEach((agent) => {
        allAgents.push({ agent, poolName })
      })
    })
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>All Agents</CardTitle>
        <CardDescription>
          {allAgents.length} agents across {pools.length} pools
        </CardDescription>
      </CardHeader>
      <CardContent>
        {allAgents.length === 0 ? (
          <div className="text-center text-muted-foreground py-6">
            No agents available. Spawn agents in a pool to get started.
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Agent</TableHead>
                <TableHead>Pool</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>State</TableHead>
                <TableHead>Health</TableHead>
                <TableHead>Uptime</TableHead>
                <TableHead>Success Rate</TableHead>
                <TableHead className="w-[100px]">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {allAgents.map(({ agent, poolName }) => (
                <TableRow key={agent.agent_id}>
                  <TableCell className="font-medium">
                    {generateAgentDisplayName(agent.agent_id, agent.role_name)}
                  </TableCell>
                  <TableCell>{poolName}</TableCell>
                  <TableCell>{agent.role_name}</TableCell>
                  <TableCell>
                    <Badge variant={getStateVariant(agent.state)}>
                      {getStateLabel(agent.state)}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {agent.healthy ? (
                      <CheckCircle className="w-4 h-4 text-green-500" />
                    ) : (
                      <XCircle className="w-4 h-4 text-red-500" />
                    )}
                  </TableCell>
                  <TableCell>{formatUptime(agent.uptime_seconds)}</TableCell>
                  <TableCell>
                    {agent.total_executions > 0
                      ? `${(agent.success_rate * 100).toFixed(0)}%`
                      : "N/A"}
                  </TableCell>
                  <TableCell>
                    <AgentActions agent={agent} poolName={poolName} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  )
}

// ===== Health Tab =====
function HealthTab({
  healthData,
  pools,
  isLoading,
}: {
  healthData?: Record<string, AgentHealth[]>
  pools: PoolResponse[]
  isLoading: boolean
}) {
  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-center">
            <Loader2 className="w-6 h-6 animate-spin" />
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {pools.map((pool) => {
        const agents = healthData?.[pool.pool_name] || []
        const healthyCount = agents.filter((a) => a.healthy).length
        const unhealthyCount = agents.length - healthyCount

        return (
          <Card key={pool.pool_name}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>{pool.pool_name}</CardTitle>
                  <CardDescription>{pool.role_class}</CardDescription>
                </div>
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-1">
                    <CheckCircle className="w-4 h-4 text-green-500" />
                    <span className="text-sm">{healthyCount} healthy</span>
                  </div>
                  {unhealthyCount > 0 && (
                    <div className="flex items-center gap-1">
                      <XCircle className="w-4 h-4 text-red-500" />
                      <span className="text-sm">{unhealthyCount} unhealthy</span>
                    </div>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {agents.length === 0 ? (
                <div className="text-center text-muted-foreground py-4">
                  No agents in this pool
                </div>
              ) : (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {agents.map((agent) => (
                    <Card
                      key={agent.agent_id}
                      className={agent.healthy ? "" : "border-red-200"}
                    >
                      <CardContent className="p-4">
                        <div className="flex items-center justify-between mb-3">
                          <span className="font-medium text-sm">
                            {generateAgentDisplayName(agent.agent_id, agent.role_name)}
                          </span>
                          <Badge variant={getStateVariant(agent.state)}>
                            {getStateLabel(agent.state)}
                          </Badge>
                        </div>
                        <div className="space-y-2 text-sm">
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Health</span>
                            <span className={agent.healthy ? "text-green-600" : "text-red-600"}>
                              {agent.healthy ? "Healthy" : "Unhealthy"}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Uptime</span>
                            <span>{formatUptime(agent.uptime_seconds)}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Idle Time</span>
                            <span>{formatUptime(agent.idle_seconds)}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Success Rate</span>
                            <span>
                              {agent.total_executions > 0
                                ? `${(agent.success_rate * 100).toFixed(0)}%`
                                : "N/A"}
                            </span>
                          </div>
                          {agent.last_heartbeat && (
                            <div className="flex justify-between">
                              <span className="text-muted-foreground">Last Heartbeat</span>
                              <span>
                                {formatDistanceToNow(new Date(agent.last_heartbeat), {
                                  addSuffix: true,
                                })}
                              </span>
                            </div>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}

// ===== Alerts Tab =====
function AlertsTab({
  alerts,
  isLoading,
}: {
  alerts: Alert[]
  isLoading: boolean
}) {
  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-center">
            <Loader2 className="w-6 h-6 animate-spin" />
          </div>
        </CardContent>
      </Card>
    )
  }

  const getSeverityIcon = (severity: Alert["severity"]) => {
    switch (severity) {
      case "ERROR":
        return <XCircle className="w-4 h-4 text-red-500" />
      case "WARNING":
        return <AlertTriangle className="w-4 h-4 text-yellow-500" />
      case "INFO":
        return <CheckCircle className="w-4 h-4 text-blue-500" />
    }
  }

  const getSeverityBadge = (severity: Alert["severity"]) => {
    switch (severity) {
      case "ERROR":
        return <Badge variant="destructive">{severity}</Badge>
      case "WARNING":
        return <Badge variant="secondary">{severity}</Badge>
      case "INFO":
        return <Badge variant="outline">{severity}</Badge>
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>System Alerts</CardTitle>
        <CardDescription>{alerts.length} alerts recorded</CardDescription>
      </CardHeader>
      <CardContent>
        {alerts.length === 0 ? (
          <div className="text-center text-muted-foreground py-6">
            No alerts to display
          </div>
        ) : (
          <div className="space-y-4">
            {alerts.map((alert, index) => (
              <div
                key={index}
                className="flex items-start gap-4 p-4 border rounded-lg"
              >
                {getSeverityIcon(alert.severity)}
                <div className="flex-1 space-y-1">
                  <div className="flex items-center gap-2">
                    {getSeverityBadge(alert.severity)}
                    <span className="text-sm text-muted-foreground">
                      {alert.pool_name}
                    </span>
                    <span className="text-sm text-muted-foreground">
                      {formatDistanceToNow(new Date(alert.timestamp), {
                        addSuffix: true,
                      })}
                    </span>
                  </div>
                  <p className="text-sm">{alert.message}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ===== Executions Tab =====
function ExecutionsTab({
  executions,
  isLoading,
}: {
  executions: AgentExecutionRecord[]
  isLoading: boolean
}) {
  const [statusFilter, setStatusFilter] = useState<string>("all")
  const [expandedExecution, setExpandedExecution] = useState<string | null>(null)

  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-center">
            <Loader2 className="w-6 h-6 animate-spin" />
          </div>
        </CardContent>
      </Card>
    )
  }

  const filteredExecutions = statusFilter === "all"
    ? executions
    : executions.filter(ex => ex.status === statusFilter)

  const getStatusBadge = (status: AgentExecutionRecord["status"]) => {
    switch (status) {
      case "completed":
        return <Badge variant="default" className="bg-green-500">Completed</Badge>
      case "failed":
        return <Badge variant="destructive">Failed</Badge>
      case "running":
        return <Badge variant="secondary">Running</Badge>
      case "pending":
        return <Badge variant="outline">Pending</Badge>
      case "cancelled":
        return <Badge variant="outline">Cancelled</Badge>
    }
  }

  const formatDuration = (ms: number | null) => {
    if (!ms) return "N/A"
    if (ms < 1000) return `${ms}ms`
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
    return `${(ms / 60000).toFixed(1)}m`
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Execution History</CardTitle>
            <CardDescription>
              {filteredExecutions.length} executions
            </CardDescription>
          </div>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[150px]">
              <SelectValue placeholder="Filter status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
              <SelectItem value="running">Running</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
              <SelectItem value="cancelled">Cancelled</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </CardHeader>
      <CardContent>
        {filteredExecutions.length === 0 ? (
          <div className="text-center text-muted-foreground py-6">
            No executions to display
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[50px]"></TableHead>
                <TableHead>Agent</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Duration</TableHead>
                <TableHead>Tokens</TableHead>
                <TableHead>LLM Calls</TableHead>
                <TableHead>Started</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredExecutions.map((execution) => (
                <>
                  <TableRow
                    key={execution.id}
                    className="cursor-pointer hover:bg-muted/50"
                    onClick={() => setExpandedExecution(
                      expandedExecution === execution.id ? null : execution.id
                    )}
                  >
                    <TableCell>
                      {expandedExecution === execution.id ? (
                        <ChevronDown className="w-4 h-4" />
                      ) : (
                        <ChevronRight className="w-4 h-4" />
                      )}
                    </TableCell>
                    <TableCell className="font-medium">
                      {execution.agent_name}
                    </TableCell>
                    <TableCell>{execution.agent_type}</TableCell>
                    <TableCell>{getStatusBadge(execution.status)}</TableCell>
                    <TableCell>{formatDuration(execution.duration_ms)}</TableCell>
                    <TableCell>{execution.token_used.toLocaleString()}</TableCell>
                    <TableCell>{execution.llm_calls}</TableCell>
                    <TableCell>
                      {execution.started_at
                        ? formatDistanceToNow(new Date(execution.started_at), {
                            addSuffix: true,
                          })
                        : "Not started"}
                    </TableCell>
                  </TableRow>
                  {expandedExecution === execution.id && (
                    <TableRow>
                      <TableCell colSpan={8} className="bg-muted/30">
                        <div className="p-4 space-y-3">
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                            <div>
                              <span className="text-muted-foreground">Execution ID:</span>
                              <p className="font-mono text-xs">{execution.id}</p>
                            </div>
                            <div>
                              <span className="text-muted-foreground">Project ID:</span>
                              <p className="font-mono text-xs">{execution.project_id}</p>
                            </div>
                            <div>
                              <span className="text-muted-foreground">Started:</span>
                              <p>{execution.started_at
                                ? new Date(execution.started_at).toLocaleString()
                                : "N/A"}</p>
                            </div>
                            <div>
                              <span className="text-muted-foreground">Completed:</span>
                              <p>{execution.completed_at
                                ? new Date(execution.completed_at).toLocaleString()
                                : "N/A"}</p>
                            </div>
                          </div>
                          {execution.error_message && (
                            <div className="mt-3">
                              <span className="text-sm text-muted-foreground">Error:</span>
                              <div className="mt-1 p-3 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded text-sm text-red-700 dark:text-red-300">
                                {execution.error_message}
                              </div>
                            </div>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                </>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  )
}

// ===== Analytics Tab =====
function AnalyticsTab() {
  const [timeRange, setTimeRange] = useState<TimeRange>("24h")
  const [selectedPool, setSelectedPool] = useState<string | undefined>()

  // Fetch metrics data
  const { data: utilizationData } = useMetricsTimeseries(
    { metric_type: "utilization", time_range: timeRange, pool_name: selectedPool },
    { refetchInterval: 60000 }
  )

  const { data: executionData } = useMetricsTimeseries(
    { metric_type: "executions", time_range: timeRange, pool_name: selectedPool },
    { refetchInterval: 60000 }
  )

  const { data: tokenData } = useTokenMetrics({ time_range: timeRange })
  const { data: processData } = useProcessMetrics({ refetchInterval: 30000 })

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Analytics & Metrics</h2>
        <div className="flex items-center gap-4">
          <TimeRangeSelector value={timeRange} onChange={setTimeRange} />
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Agent Utilization Chart */}
        {utilizationData && (
          <AgentUtilizationChart
            data={utilizationData.data.map((d) => ({
              timestamp: d.timestamp,
              idle: (d as any).idle || 0,
              busy: (d as any).busy || 0,
              error: (d as any).error || 0,
              total: (d as any).total || 0,
            }))}
          />
        )}

        {/* Execution Trends Chart */}
        {executionData && (
          <ExecutionTrendsChart
            data={executionData.data.map((d) => ({
              timestamp: d.timestamp,
              total: (d as any).total || 0,
              successful: (d as any).successful || 0,
              failed: (d as any).failed || 0,
              success_rate: (d as any).success_rate || 0,
            }))}
          />
        )}

        {/* Process Metrics Chart */}
        {processData && (
          <ProcessMetricsChart summary={processData.summary} processes={processData.processes} />
        )}

        {/* Token Usage Chart */}
        {tokenData && <TokenUsageChart data={tokenData.data} />}

        {/* Success Rate Chart */}
        {executionData && (
          <SuccessRateChart
            data={executionData.data.map((d) => ({
              timestamp: d.timestamp,
              success_rate: (d as any).success_rate || 0,
              successful: (d as any).successful || 0,
              failed: (d as any).failed || 0,
            }))}
            showArea={true}
          />
        )}

        {/* LLM Calls Chart */}
        {tokenData && (
          <LLMCallsChart
            data={tokenData.data.map((d) => ({
              pool_name: d.pool_name,
              llm_calls: d.total_llm_calls,
              tokens: d.total_tokens,
              avg_tokens_per_call: d.avg_tokens_per_call,
            }))}
          />
        )}
      </div>

      {/* Summary Stats */}
      {tokenData && (
        <Card>
          <CardHeader>
            <CardTitle>Summary Statistics</CardTitle>
            <CardDescription>
              Aggregated metrics for the selected time range ({timeRange})
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <div className="text-sm text-muted-foreground">Total Tokens</div>
                <div className="text-2xl font-bold">
                  {tokenData.summary.total_tokens.toLocaleString()}
                </div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Total LLM Calls</div>
                <div className="text-2xl font-bold">
                  {tokenData.summary.total_llm_calls.toLocaleString()}
                </div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Avg Tokens/Call</div>
                <div className="text-2xl font-bold">
                  {tokenData.summary.avg_tokens_per_call.toFixed(0)}
                </div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Estimated Cost</div>
                <div className="text-2xl font-bold">
                  ${tokenData.summary.estimated_total_cost_usd.toFixed(4)}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

// ===== Utility Functions =====
function formatUptime(seconds: number): string {
  if (seconds < 60) return `${seconds}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`
  return `${Math.floor(seconds / 86400)}d`
}
