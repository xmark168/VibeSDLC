import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { AgentsService } from "@/client/sdk.gen"
import {
  agentsApi,
  type CreatePoolRequest,
  type SpawnAgentRequest,
  type ExecutionFilters,
} from "@/apis/agents"

// ===== Query Keys =====
export const agentQueryKeys = {
  all: ["agents"] as const,
  pools: () => [...agentQueryKeys.all, "pools"] as const,
  pool: (poolName: string) => [...agentQueryKeys.pools(), poolName] as const,
  health: () => [...agentQueryKeys.all, "health"] as const,
  agentHealth: (agentId: string, poolName: string) =>
    [...agentQueryKeys.health(), agentId, poolName] as const,
  dashboard: () => [...agentQueryKeys.all, "dashboard"] as const,
  systemStats: () => [...agentQueryKeys.all, "system-stats"] as const,
  alerts: (limit?: number) => [...agentQueryKeys.all, "alerts", limit] as const,
  project: (projectId: string) => [...agentQueryKeys.all, "project", projectId] as const,
  executions: (filters?: ExecutionFilters) => [...agentQueryKeys.all, "executions", filters] as const,
  metrics: () => [...agentQueryKeys.all, "metrics"] as const,
  metricsTimeseries: (params: {
    metric_type: string
    time_range?: string
    pool_name?: string
  }) => [...agentQueryKeys.metrics(), "timeseries", params] as const,
  metricsAggregated: (params: { time_range?: string; group_by?: string }) =>
    [...agentQueryKeys.metrics(), "aggregated", params] as const,
  processMetrics: () => [...agentQueryKeys.metrics(), "processes"] as const,
  tokenMetrics: (params: { time_range?: string; group_by?: string }) =>
    [...agentQueryKeys.metrics(), "tokens", params] as const,
}

// ===== Queries =====

/**
 * Fetch all agents for a specific project (from database)
 */
export function useProjectAgents(projectId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: agentQueryKeys.project(projectId),
    queryFn: async () => {
      const response = await AgentsService.getProjectAgents({ projectId })
      return response || []
    },
    enabled: (options?.enabled ?? true) && !!projectId,
    staleTime: 10000, // Consider stale after 10s
  })
}

/**
 * Fetch all agent pools with polling
 */
export function useAgentPools(options?: { enabled?: boolean; refetchInterval?: number }) {
  return useQuery({
    queryKey: agentQueryKeys.pools(),
    queryFn: () => agentsApi.listPools(),
    enabled: options?.enabled ?? true,
    refetchInterval: options?.refetchInterval ?? 30000, // Poll every 30s
    staleTime: 10000, // Consider stale after 10s
  })
}

/**
 * Fetch specific pool statistics
 */
export function usePoolStats(poolName: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: agentQueryKeys.pool(poolName),
    queryFn: () => agentsApi.getPoolStats(poolName),
    enabled: (options?.enabled ?? true) && !!poolName,
    refetchInterval: 30000,
  })
}

/**
 * Fetch all agent health data
 */
export function useAllAgentHealth(options?: { enabled?: boolean; refetchInterval?: number }) {
  return useQuery({
    queryKey: agentQueryKeys.health(),
    queryFn: () => agentsApi.getAllAgentHealth(),
    enabled: options?.enabled ?? true,
    refetchInterval: options?.refetchInterval ?? 30000,
    staleTime: 10000,
  })
}

/**
 * Fetch specific agent health
 */
export function useAgentHealth(
  agentId: string,
  poolName: string,
  options?: { enabled?: boolean }
) {
  return useQuery({
    queryKey: agentQueryKeys.agentHealth(agentId, poolName),
    queryFn: () => agentsApi.getAgentHealth(agentId, poolName),
    enabled: (options?.enabled ?? true) && !!agentId && !!poolName,
    refetchInterval: 10000, // More frequent for individual agent
  })
}

/**
 * Fetch dashboard data (comprehensive view)
 */
export function useAgentDashboard(options?: { enabled?: boolean; refetchInterval?: number }) {
  return useQuery({
    queryKey: agentQueryKeys.dashboard(),
    queryFn: () => agentsApi.getDashboard(),
    enabled: options?.enabled ?? true,
    refetchInterval: options?.refetchInterval ?? 30000,
    staleTime: 10000,
  })
}

/**
 * Fetch system statistics
 */
export function useSystemStats(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: agentQueryKeys.systemStats(),
    queryFn: () => agentsApi.getSystemStats(),
    enabled: options?.enabled ?? true,
    refetchInterval: 30000,
  })
}

/**
 * Fetch alerts
 */
export function useAgentAlerts(limit: number = 20, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: agentQueryKeys.alerts(limit),
    queryFn: () => agentsApi.getAlerts(limit),
    enabled: options?.enabled ?? true,
    refetchInterval: 60000, // Less frequent for alerts
  })
}

/**
 * Fetch execution history
 */
export function useAgentExecutions(
  filters?: ExecutionFilters,
  options?: { enabled?: boolean; refetchInterval?: number }
) {
  return useQuery({
    queryKey: agentQueryKeys.executions(filters),
    queryFn: () => agentsApi.getExecutions(filters),
    enabled: options?.enabled ?? true,
    refetchInterval: options?.refetchInterval ?? 30000,
    staleTime: 10000,
  })
}

// ===== Metrics Queries =====

/**
 * Fetch time-series metrics for charts
 */
export function useMetricsTimeseries(
  params: {
    metric_type: "utilization" | "executions" | "tokens" | "success_rate"
    time_range?: "1h" | "6h" | "24h" | "7d" | "30d"
    interval?: string
    pool_name?: string
  },
  options?: { enabled?: boolean; refetchInterval?: number }
) {
  return useQuery({
    queryKey: agentQueryKeys.metricsTimeseries(params),
    queryFn: () => agentsApi.getMetricsTimeseries(params),
    enabled: options?.enabled ?? true,
    refetchInterval: options?.refetchInterval ?? 60000, // 1 minute default
    staleTime: 30000,
  })
}

/**
 * Fetch aggregated metrics statistics
 */
export function useMetricsAggregated(
  params: {
    time_range?: "1h" | "6h" | "24h" | "7d" | "30d"
    group_by?: "pool" | "hour" | "day"
  },
  options?: { enabled?: boolean }
) {
  return useQuery({
    queryKey: agentQueryKeys.metricsAggregated(params),
    queryFn: () => agentsApi.getMetricsAggregated(params),
    enabled: options?.enabled ?? true,
    refetchInterval: 60000,
    staleTime: 30000,
  })
}

/**
 * Fetch process metrics (current state)
 */
export function useProcessMetrics(options?: { enabled?: boolean; refetchInterval?: number }) {
  return useQuery({
    queryKey: agentQueryKeys.processMetrics(),
    queryFn: () => agentsApi.getProcessMetrics(),
    enabled: options?.enabled ?? true,
    refetchInterval: options?.refetchInterval ?? 30000, // More frequent for real-time data
    staleTime: 10000,
  })
}

/**
 * Fetch token usage metrics
 */
export function useTokenMetrics(
  params: {
    time_range?: "1h" | "6h" | "24h" | "7d" | "30d"
    group_by?: "pool" | "agent_type"
  },
  options?: { enabled?: boolean }
) {
  return useQuery({
    queryKey: agentQueryKeys.tokenMetrics(params),
    queryFn: () => agentsApi.getTokenMetrics(params),
    enabled: options?.enabled ?? true,
    refetchInterval: 60000,
    staleTime: 30000,
  })
}

// ===== Mutations =====

/**
 * Create a new agent pool
 */
export function useCreatePool() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (body: CreatePoolRequest) => agentsApi.createPool(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentQueryKeys.pools() })
      queryClient.invalidateQueries({ queryKey: agentQueryKeys.dashboard() })
    },
  })
}

/**
 * Delete an agent pool
 */
export function useDeletePool() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ poolName, graceful = true }: { poolName: string; graceful?: boolean }) =>
      agentsApi.deletePool(poolName, graceful),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentQueryKeys.pools() })
      queryClient.invalidateQueries({ queryKey: agentQueryKeys.dashboard() })
    },
  })
}

/**
 * Spawn a new agent in a pool
 */
export function useSpawnAgent() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (body: SpawnAgentRequest) => agentsApi.spawnAgent(body),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: agentQueryKeys.pool(variables.pool_name) })
      queryClient.invalidateQueries({ queryKey: agentQueryKeys.health() })
      queryClient.invalidateQueries({ queryKey: agentQueryKeys.dashboard() })
    },
  })
}

/**
 * Terminate an agent
 */
export function useTerminateAgent() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      poolName,
      agentId,
      graceful = true,
    }: {
      poolName: string
      agentId: string
      graceful?: boolean
    }) => agentsApi.terminateAgent(poolName, agentId, graceful),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: agentQueryKeys.pool(variables.poolName) })
      queryClient.invalidateQueries({ queryKey: agentQueryKeys.health() })
      queryClient.invalidateQueries({ queryKey: agentQueryKeys.dashboard() })
    },
  })
}

/**
 * Force set agent to idle state
 */
export function useSetAgentIdle() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ agentId, poolName }: { agentId: string; poolName: string }) =>
      agentsApi.setAgentIdle(agentId, poolName),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: agentQueryKeys.agentHealth(variables.agentId, variables.poolName),
      })
      queryClient.invalidateQueries({ queryKey: agentQueryKeys.health() })
      queryClient.invalidateQueries({ queryKey: agentQueryKeys.dashboard() })
    },
  })
}

/**
 * Start monitoring system
 */
export function useStartMonitoring() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (monitorInterval: number = 30) => agentsApi.startMonitoring(monitorInterval),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentQueryKeys.systemStats() })
    },
  })
}

/**
 * Stop monitoring system
 */
export function useStopMonitoring() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => agentsApi.stopMonitoring(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentQueryKeys.systemStats() })
    },
  })
}
