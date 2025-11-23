import { request as __request } from "@client/core/request"
import { OpenAPI } from "@/client"

// ===== Types =====

export interface PoolResponse {
  pool_name: string
  role_class: string
  total_agents: number
  active_agents: number
  busy_agents: number
  idle_agents: number
  total_spawned: number
  total_terminated: number
  total_executions: number
  successful_executions: number
  failed_executions: number
  success_rate: number
  load: number
  created_at: string
}

export interface AgentHealth {
  agent_id: string
  role_name: string
  state: AgentState
  healthy: boolean
  uptime_seconds: number
  idle_seconds: number
  last_heartbeat: string | null
  total_executions: number
  successful_executions: number
  failed_executions: number
  success_rate: number
}

export interface SystemStats {
  uptime_seconds: number
  total_pools: number
  total_agents: number
  total_executions: number
  successful_executions: number
  failed_executions: number
  success_rate: number
  recent_alerts: number
}

export interface DashboardData {
  system: SystemStats
  pools: Record<string, PoolResponse>
  agents: Record<string, AgentHealth[]>
  alerts: Alert[]
  timestamp: string
}

export interface Alert {
  timestamp: string
  severity: "INFO" | "WARNING" | "ERROR"
  pool_name: string
  message: string
  stats: Record<string, unknown>
}

export interface AgentExecutionRecord {
  id: string
  project_id: string
  agent_name: string
  agent_type: string
  status: "pending" | "running" | "completed" | "failed" | "cancelled"
  started_at: string | null
  completed_at: string | null
  duration_ms: number | null
  token_used: number
  llm_calls: number
  error_message: string | null
  created_at: string
}

export interface ExecutionFilters {
  limit?: number
  status?: string
  agent_type?: string
  project_id?: string
}

export type AgentState =
  | "created"
  | "starting"
  | "running"
  | "idle"
  | "busy"
  | "stopping"
  | "stopped"
  | "error"
  | "terminated"

export interface SpawnAgentRequest {
  pool_name: string
  heartbeat_interval?: number
  max_idle_time?: number
}

export interface SpawnAgentResponse {
  agent_id: string
  role_name: string
  pool_name: string
  state: AgentState
  created_at: string
}

export interface CreatePoolRequest {
  role_type: "team_leader" | "business_analyst" | "tester"
  pool_name: string
  config?: {
    min_agents?: number
    max_agents?: number
    scale_up_threshold?: number
    scale_down_threshold?: number
    idle_timeout?: number
    health_check_interval?: number
  }
}

// ===== API Client =====

export const agentsApi = {
  // Pool Management
  listPools: async (): Promise<PoolResponse[]> => {
    return __request<PoolResponse[]>(OpenAPI, {
      method: "GET",
      url: "/api/v1/agents/pools",
    })
  },

  getPoolStats: async (poolName: string): Promise<PoolResponse> => {
    return __request<PoolResponse>(OpenAPI, {
      method: "GET",
      url: `/api/v1/agents/pools/${poolName}`,
    })
  },

  createPool: async (body: CreatePoolRequest): Promise<PoolResponse> => {
    return __request<PoolResponse>(OpenAPI, {
      method: "POST",
      url: "/api/v1/agents/pools",
      body,
    })
  },

  deletePool: async (poolName: string, graceful: boolean = true): Promise<{ message: string }> => {
    return __request<{ message: string }>(OpenAPI, {
      method: "DELETE",
      url: `/api/v1/agents/pools/${poolName}`,
      query: { graceful },
    })
  },

  // Agent Management
  spawnAgent: async (body: SpawnAgentRequest): Promise<SpawnAgentResponse> => {
    return __request<SpawnAgentResponse>(OpenAPI, {
      method: "POST",
      url: "/api/v1/agents/spawn",
      body,
    })
  },

  terminateAgent: async (poolName: string, agentId: string, graceful: boolean = true): Promise<{ message: string }> => {
    return __request<{ message: string }>(OpenAPI, {
      method: "POST",
      url: "/api/v1/agents/terminate",
      body: {
        pool_name: poolName,
        agent_id: agentId,
        graceful,
      },
    })
  },

  setAgentIdle: async (agentId: string, poolName: string): Promise<{
    message: string
    agent_id: string
    previous_state: string
    current_state: string
  }> => {
    return __request(OpenAPI, {
      method: "POST",
      url: `/api/v1/agents/${agentId}/set-idle`,
      query: { pool_name: poolName },
    })
  },

  // Health & Monitoring
  getAllAgentHealth: async (): Promise<Record<string, AgentHealth[]>> => {
    return __request<Record<string, AgentHealth[]>>(OpenAPI, {
      method: "GET",
      url: "/api/v1/agents/health",
    })
  },

  getAgentHealth: async (agentId: string, poolName: string): Promise<AgentHealth> => {
    return __request<AgentHealth>(OpenAPI, {
      method: "GET",
      url: `/api/v1/agents/${agentId}/health`,
      query: { pool_name: poolName },
    })
  },

  getSystemStats: async (): Promise<SystemStats> => {
    return __request<SystemStats>(OpenAPI, {
      method: "GET",
      url: "/api/v1/agents/monitor/system",
    })
  },

  getDashboard: async (): Promise<DashboardData> => {
    return __request<DashboardData>(OpenAPI, {
      method: "GET",
      url: "/api/v1/agents/monitor/dashboard",
    })
  },

  getAlerts: async (limit: number = 20): Promise<Alert[]> => {
    return __request<Alert[]>(OpenAPI, {
      method: "GET",
      url: "/api/v1/agents/monitor/alerts",
      query: { limit },
    })
  },

  // System Control
  startMonitoring: async (monitorInterval: number = 30): Promise<{ message: string }> => {
    return __request<{ message: string }>(OpenAPI, {
      method: "POST",
      url: "/api/v1/agents/system/start",
      query: { monitor_interval: monitorInterval },
    })
  },

  stopMonitoring: async (): Promise<{ message: string }> => {
    return __request<{ message: string }>(OpenAPI, {
      method: "POST",
      url: "/api/v1/agents/system/stop",
    })
  },

  // Execution History
  getExecutions: async (filters?: ExecutionFilters): Promise<AgentExecutionRecord[]> => {
    return __request<AgentExecutionRecord[]>(OpenAPI, {
      method: "GET",
      url: "/api/v1/agents/executions",
      query: {
        limit: filters?.limit || 50,
        status: filters?.status,
        agent_type: filters?.agent_type,
        project_id: filters?.project_id,
      },
    })
  },

  getExecutionDetail: async (executionId: string): Promise<AgentExecutionRecord & {
    error_traceback: string | null
    result: Record<string, unknown> | null
    extra_metadata: Record<string, unknown> | null
    updated_at: string
  }> => {
    return __request(OpenAPI, {
      method: "GET",
      url: `/api/v1/agents/executions/${executionId}`,
    })
  },

  // Metrics & Analytics
  getMetricsTimeseries: async (params: {
    metric_type: "utilization" | "executions" | "tokens" | "success_rate"
    time_range?: "1h" | "6h" | "24h" | "7d" | "30d"
    interval?: string
    pool_name?: string
  }): Promise<{
    metric_type: string
    time_range: string
    interval: string
    pool_name: string | null
    data: Array<{
      timestamp: string
      pool_name: string
      [key: string]: unknown
    }>
    count: number
  }> => {
    return __request(OpenAPI, {
      method: "GET",
      url: "/api/v1/agents/metrics/timeseries",
      query: {
        metric_type: params.metric_type,
        time_range: params.time_range || "24h",
        interval: params.interval || "auto",
        pool_name: params.pool_name,
      },
    })
  },

  getMetricsAggregated: async (params: {
    time_range?: "1h" | "6h" | "24h" | "7d" | "30d"
    group_by?: "pool" | "hour" | "day"
  }): Promise<{
    group_by: string
    time_range: string
    data: Array<{
      pool_name?: string
      timestamp?: string
      [key: string]: unknown
    }>
    count: number
  }> => {
    return __request(OpenAPI, {
      method: "GET",
      url: "/api/v1/agents/metrics/aggregated",
      query: {
        time_range: params.time_range || "24h",
        group_by: params.group_by || "pool",
      },
    })
  },

  getTokenMetrics: async (params: {
    time_range?: "1h" | "6h" | "24h" | "7d" | "30d"
    group_by?: "pool" | "agent_type"
  }): Promise<{
    time_range: string
    group_by: string
    summary: {
      total_tokens: number
      total_llm_calls: number
      avg_tokens_per_call: number
      estimated_total_cost_usd: number
    }
    data: Array<{
      pool_name: string
      total_tokens: number
      total_llm_calls: number
      avg_tokens_per_call: number
      avg_duration_ms: number
      estimated_cost_usd: number
    }>
    count: number
  }> => {
    return __request(OpenAPI, {
      method: "GET",
      url: "/api/v1/agents/metrics/tokens",
      query: {
        time_range: params.time_range || "24h",
        group_by: params.group_by || "pool",
      },
    })
  },
}

// ===== Utility Functions =====

/**
 * Generate a friendly display name for an agent
 * Format: Agent-{RolePrefix}-{IdSuffix}
 */
export function generateAgentDisplayName(agentId: string, roleName: string): string {
  const rolePrefix = getRolePrefix(roleName)
  const idSuffix = agentId.slice(0, 4).toUpperCase()
  return `Agent-${rolePrefix}-${idSuffix}`
}

function getRolePrefix(roleName: string): string {
  const prefixMap: Record<string, string> = {
    "TeamLeader": "TL",
    "Team Leader": "TL",
    "team_leader": "TL",
    "BusinessAnalyst": "BA",
    "Business Analyst": "BA",
    "business_analyst": "BA",
    "Developer": "DEV",
    "developer": "DEV",
    "Tester": "QA",
    "tester": "QA",
  }
  return prefixMap[roleName] || roleName.slice(0, 2).toUpperCase()
}

/**
 * Get status color variant for badges
 */
export function getStateVariant(state: AgentState): "default" | "secondary" | "destructive" | "outline" {
  switch (state) {
    case "idle":
      return "default" // Green - ready
    case "busy":
    case "running":
      return "secondary" // Yellow - working
    case "error":
    case "terminated":
      return "destructive" // Red - error
    default:
      return "outline" // Gray - other
  }
}

/**
 * Get human-readable state label
 */
export function getStateLabel(state: AgentState): string {
  const labels: Record<AgentState, string> = {
    created: "Created",
    starting: "Starting",
    running: "Running",
    idle: "Idle",
    busy: "Busy",
    stopping: "Stopping",
    stopped: "Stopped",
    error: "Error",
    terminated: "Terminated",
  }
  return labels[state] || state
}
