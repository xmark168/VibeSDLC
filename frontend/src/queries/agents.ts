import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { AgentsService } from "@/client/sdk.gen"
import {
  agentsApi,
  type CreatePoolRequest,
  type SpawnAgentRequest,
  type ExecutionFilters,
  type UpdatePoolConfigRequest,
} from "@/apis/agents"

// ===== Query Keys =====
export const agentQueryKeys = {
  all: ["agents"] as const,
  pools: () => [...agentQueryKeys.all, "pools"] as const,
  pool: (poolName: string) => [...agentQueryKeys.pools(), poolName] as const,
  poolDb: (poolName: string) => [...agentQueryKeys.pool(poolName), "db"] as const,
  poolMetrics: (poolId: string, startDate?: string, endDate?: string) =>
    [...agentQueryKeys.all, "pool-metrics", poolId, startDate, endDate] as const,
  poolSuggestions: () => [...agentQueryKeys.pools(), "suggestions"] as const,
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

// ===== Pool DB Management Queries & Mutations =====

/**
 * Fetch pool database information
 * Returns persistent pool record including configuration, counters, and metadata
 */
export function usePoolDbInfo(poolName: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: agentQueryKeys.poolDb(poolName),
    queryFn: () => agentsApi.getPoolDbInfo(poolName),
    enabled: (options?.enabled ?? true) && !!poolName,
    staleTime: 30000, // 30s - DB data doesn't change frequently
    refetchInterval: 60000, // Refetch every minute
  })
}

/**
 * Fetch pool metrics history from database
 * Returns time-series metrics including tokens, requests, agent counts, executions
 */
export function usePoolMetrics(
  poolId: string,
  options?: {
    enabled?: boolean
    startDate?: string
    endDate?: string
    limit?: number
  }
) {
  return useQuery({
    queryKey: agentQueryKeys.poolMetrics(poolId, options?.startDate, options?.endDate),
    queryFn: () =>
      agentsApi.getPoolMetrics(poolId, options?.startDate, options?.endDate, options?.limit),
    enabled: (options?.enabled ?? true) && !!poolId,
    staleTime: 60000, // 1 minute - historical data
    refetchInterval: 120000, // Refetch every 2 minutes
  })
}

/**
 * Fetch pool creation suggestions based on current load
 * Analyzes pools and suggests creating new ones when needed
 */
export function usePoolSuggestions(options?: { enabled?: boolean; refetchInterval?: number }) {
  return useQuery({
    queryKey: agentQueryKeys.poolSuggestions(),
    queryFn: () => agentsApi.getPoolSuggestions(),
    enabled: options?.enabled ?? true,
    staleTime: 30000, // 30s
    refetchInterval: options?.refetchInterval ?? 60000, // Default 1 minute
  })
}

/**
 * Update pool configuration in database
 * Also updates runtime manager if pool is active
 */
export function useUpdatePoolConfig() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      poolId,
      config,
    }: {
      poolId: string
      config: Omit<UpdatePoolConfigRequest, "pool_id">
    }) => agentsApi.updatePoolConfig(poolId, config),
    onSuccess: (data) => {
      // Invalidate pool DB info
      queryClient.invalidateQueries({ queryKey: agentQueryKeys.poolDb(data.pool_name) })
      // Invalidate pool stats (runtime data)
      queryClient.invalidateQueries({ queryKey: agentQueryKeys.pool(data.pool_name) })
      // Invalidate pools list
      queryClient.invalidateQueries({ queryKey: agentQueryKeys.pools() })
      // Invalidate dashboard
      queryClient.invalidateQueries({ queryKey: agentQueryKeys.dashboard() })
    },
  })
}

/**
 * Scale pool to target agent count
 * Automatically spawns or terminates agents
 */
export function useScalePool() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ poolName, targetAgents }: { poolName: string; targetAgents: number }) =>
      agentsApi.scalePool(poolName, targetAgents),
    onSuccess: (_, variables) => {
      // Invalidate pool DB info
      queryClient.invalidateQueries({ queryKey: agentQueryKeys.poolDb(variables.poolName) })
      // Invalidate pool stats
      queryClient.invalidateQueries({ queryKey: agentQueryKeys.pool(variables.poolName) })
      // Invalidate health data
      queryClient.invalidateQueries({ queryKey: agentQueryKeys.health() })
      // Invalidate pools list
      queryClient.invalidateQueries({ queryKey: agentQueryKeys.pools() })
      // Invalidate dashboard
      queryClient.invalidateQueries({ queryKey: agentQueryKeys.dashboard() })
    },
  })
}
