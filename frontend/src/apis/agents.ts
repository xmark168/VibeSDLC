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
