import { request as __request } from "@client/core/request"
import { OpenAPI } from "@/client"
import type {
  AgentExecutionRecord,
  AgentHealth,
  AgentPoolDB,
  AgentPoolMetrics,
  AgentState,
  AgentTemplate,
  AgentTemplateCreate,
  AgentTemplateFromAgent,
  AgentTokenStats,
  Alert,
  AutoScalingRule,
  AutoScalingRuleCreate,
  BulkOperationResponse,
  CreatePoolRequest,
  DashboardData,
  EmergencyActionResponse,
  ExecutionFilters,
  PoolResponse,
  PoolSuggestion,
  PoolTokenStats,
  SpawnAgentRequest,
  SpawnAgentResponse,
  SystemStats,
  SystemStatusResponse,
  SystemTokenSummary,
  UpdatePoolConfigRequest,
} from "@/types"

// Re-export types for convenience
export type {
  PoolResponse,
  AgentHealth,
  SystemStats,
  DashboardData,
  Alert,
  AgentExecutionRecord,
  ExecutionFilters,
  AgentState,
  SpawnAgentRequest,
  SpawnAgentResponse,
  CreatePoolRequest,
  AgentPoolDB,
  AgentPoolMetrics,
  UpdatePoolConfigRequest,
  PoolSuggestion,
  AgentTokenStats,
  PoolTokenStats,
  SystemTokenSummary,
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

  deletePool: async (
    poolName: string,
    graceful: boolean = true,
  ): Promise<{ message: string }> => {
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

  terminateAgent: async (
    poolName: string,
    agentId: string,
    graceful: boolean = true,
  ): Promise<{ message: string }> => {
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

  setAgentIdle: async (
    agentId: string,
    poolName: string,
  ): Promise<{
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

  getAgentHealth: async (
    agentId: string,
    poolName: string,
  ): Promise<AgentHealth> => {
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
  startMonitoring: async (
    monitorInterval: number = 30,
  ): Promise<{ message: string }> => {
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
  getExecutions: async (
    filters?: ExecutionFilters,
  ): Promise<AgentExecutionRecord[]> => {
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

  getExecutionDetail: async (
    executionId: string,
  ): Promise<
    AgentExecutionRecord & {
      error_traceback: string | null
      result: Record<string, unknown> | null
      extra_metadata: Record<string, unknown> | null
      updated_at: string
    }
  > => {
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

  // ===== Pool DB Management =====

  getPoolDbInfo: async (poolName: string): Promise<AgentPoolDB> => {
    return __request(OpenAPI, {
      method: "GET",
      url: `/api/v1/agent-management/pools/${poolName}/db`,
    })
  },

  updatePoolConfig: async (
    poolId: string,
    config: Omit<UpdatePoolConfigRequest, "pool_id">,
  ): Promise<AgentPoolDB> => {
    return __request(OpenAPI, {
      method: "PUT",
      url: `/api/v1/agent-management/pools/${poolId}/config`,
      body: config,
    })
  },

  updatePoolPriorities: async (
    poolPriorities: Array<{ pool_id: string; priority: number }>,
  ): Promise<AgentPoolDB[]> => {
    return __request(OpenAPI, {
      method: "PUT",
      url: "/api/v1/agents/pools/priorities",
      body: { pool_priorities: poolPriorities },
    })
  },

  getPoolMetrics: async (
    poolId: string,
    startDate?: string,
    endDate?: string,
    limit: number = 100,
  ): Promise<AgentPoolMetrics[]> => {
    return __request(OpenAPI, {
      method: "GET",
      url: `/api/v1/agent-management/pools/${poolId}/metrics`,
      query: {
        start_date: startDate,
        end_date: endDate,
        limit,
      },
    })
  },

  scalePool: async (
    poolName: string,
    targetAgents: number,
  ): Promise<{
    message: string
    current_count: number
    target_count: number
    spawned?: number
    terminated?: number
  }> => {
    return __request(OpenAPI, {
      method: "POST",
      url: `/api/v1/agent-management/pools/${poolName}/scale`,
      body: { target_agents: targetAgents },
    })
  },

  getPoolSuggestions: async (): Promise<PoolSuggestion[]> => {
    return __request(OpenAPI, {
      method: "GET",
      url: "/api/v1/agent-management/pools/suggestions",
    })
  },

  // ===== Emergency Controls =====

  getSystemStatus: async (): Promise<SystemStatusResponse> => {
    return __request(OpenAPI, {
      method: "GET",
      url: "/api/v1/agents/system/status",
    })
  },

  emergencyPause: async (): Promise<EmergencyActionResponse> => {
    return __request(OpenAPI, {
      method: "POST",
      url: "/api/v1/agents/system/emergency/pause",
    })
  },

  emergencyResume: async (): Promise<EmergencyActionResponse> => {
    return __request(OpenAPI, {
      method: "POST",
      url: "/api/v1/agents/system/emergency/resume",
    })
  },

  emergencyStop: async (
    force: boolean = false,
  ): Promise<EmergencyActionResponse> => {
    return __request(OpenAPI, {
      method: "POST",
      url: "/api/v1/agents/system/emergency/stop",
      query: { force },
    })
  },

  enterMaintenanceMode: async (
    message: string = "System under maintenance",
  ): Promise<EmergencyActionResponse> => {
    return __request(OpenAPI, {
      method: "POST",
      url: "/api/v1/agents/system/emergency/maintenance",
      query: { message },
    })
  },

  restartPool: async (
    poolName: string,
  ): Promise<{
    message: string
    pool_name: string
    agents_terminated: number
    agents_respawned: number
  }> => {
    return __request(OpenAPI, {
      method: "POST",
      url: `/api/v1/agents/system/emergency/restart-pool/${poolName}`,
    })
  },

  // ===== Bulk Operations =====

  bulkTerminate: async (
    agentIds: string[],
    graceful: boolean = true,
  ): Promise<BulkOperationResponse> => {
    return __request(OpenAPI, {
      method: "POST",
      url: "/api/v1/agents/bulk/terminate",
      query: { graceful },
      body: { agent_ids: agentIds },
    })
  },

  bulkSetIdle: async (agentIds: string[]): Promise<BulkOperationResponse> => {
    return __request(OpenAPI, {
      method: "POST",
      url: "/api/v1/agents/bulk/set-idle",
      body: { agent_ids: agentIds },
    })
  },

  bulkRestart: async (agentIds: string[]): Promise<BulkOperationResponse> => {
    return __request(OpenAPI, {
      method: "POST",
      url: "/api/v1/agents/bulk/restart",
      body: { agent_ids: agentIds },
    })
  },

  bulkSpawn: async (params: {
    role_type: string
    count: number
    project_id: string
    pool_name?: string
  }): Promise<BulkOperationResponse> => {
    return __request(OpenAPI, {
      method: "POST",
      url: "/api/v1/agents/bulk/spawn",
      body: {
        role_type: params.role_type,
        count: params.count,
        project_id: params.project_id,
        pool_name: params.pool_name || "universal_pool",
      },
    })
  },

  // ===== Auto-scaling Rules =====

  listScalingRules: async (params?: {
    poolName?: string
    enabledOnly?: boolean
  }): Promise<AutoScalingRule[]> => {
    return __request(OpenAPI, {
      method: "GET",
      url: "/api/v1/agents/scaling/rules",
      query: {
        pool_name: params?.poolName,
        enabled_only: params?.enabledOnly,
      },
    })
  },

  createScalingRule: async (
    rule: AutoScalingRuleCreate,
  ): Promise<AutoScalingRule> => {
    return __request(OpenAPI, {
      method: "POST",
      url: "/api/v1/agents/scaling/rules",
      body: rule,
    })
  },

  getScalingRule: async (ruleId: string): Promise<AutoScalingRule> => {
    return __request(OpenAPI, {
      method: "GET",
      url: `/api/v1/agents/scaling/rules/${ruleId}`,
    })
  },

  updateScalingRule: async (
    ruleId: string,
    rule: AutoScalingRuleCreate,
  ): Promise<AutoScalingRule> => {
    return __request(OpenAPI, {
      method: "PUT",
      url: `/api/v1/agents/scaling/rules/${ruleId}`,
      body: rule,
    })
  },

  deleteScalingRule: async (ruleId: string): Promise<{ message: string }> => {
    return __request(OpenAPI, {
      method: "DELETE",
      url: `/api/v1/agents/scaling/rules/${ruleId}`,
    })
  },

  toggleScalingRule: async (ruleId: string): Promise<AutoScalingRule> => {
    return __request(OpenAPI, {
      method: "POST",
      url: `/api/v1/agents/scaling/rules/${ruleId}/toggle`,
    })
  },

  triggerScalingRule: async (
    ruleId: string,
  ): Promise<{
    message: string
    current_count: number
    target_count: number
    action_taken: string
    agents_to_spawn?: number
    agents_terminated?: number
  }> => {
    return __request(OpenAPI, {
      method: "POST",
      url: `/api/v1/agents/scaling/rules/${ruleId}/trigger`,
    })
  },

  // ===== Agent Templates =====

  listTemplates: async (params?: {
    roleType?: string
    tag?: string
  }): Promise<AgentTemplate[]> => {
    return __request(OpenAPI, {
      method: "GET",
      url: "/api/v1/agents/templates",
      query: {
        role_type: params?.roleType,
        tag: params?.tag,
      },
    })
  },

  createTemplate: async (
    template: AgentTemplateCreate,
  ): Promise<AgentTemplate> => {
    return __request(OpenAPI, {
      method: "POST",
      url: "/api/v1/agents/templates",
      body: template,
    })
  },

  createTemplateFromAgent: async (
    request: AgentTemplateFromAgent,
  ): Promise<AgentTemplate> => {
    return __request(OpenAPI, {
      method: "POST",
      url: "/api/v1/agents/templates/from-agent",
      body: request,
    })
  },

  getTemplate: async (templateId: string): Promise<AgentTemplate> => {
    return __request(OpenAPI, {
      method: "GET",
      url: `/api/v1/agents/templates/${templateId}`,
    })
  },

  updateTemplate: async (
    templateId: string,
    template: AgentTemplateCreate,
  ): Promise<AgentTemplate> => {
    return __request(OpenAPI, {
      method: "PUT",
      url: `/api/v1/agents/templates/${templateId}`,
      body: template,
    })
  },

  deleteTemplate: async (templateId: string): Promise<{ message: string }> => {
    return __request(OpenAPI, {
      method: "DELETE",
      url: `/api/v1/agents/templates/${templateId}`,
    })
  },

  spawnFromTemplate: async (
    templateId: string,
    projectId: string,
    count?: number,
  ): Promise<{
    message: string
    success_count: number
    failed_count: number
    results: Array<{
      index: number
      agent_id?: string
      agent_name?: string
      status: string
      error?: string
    }>
    template: AgentTemplate
  }> => {
    return __request(OpenAPI, {
      method: "POST",
      url: `/api/v1/agents/templates/${templateId}/spawn`,
      query: { project_id: projectId, count: count || 1 },
    })
  },

  duplicateTemplate: async (
    templateId: string,
    newName: string,
  ): Promise<AgentTemplate> => {
    return __request(OpenAPI, {
      method: "POST",
      url: `/api/v1/agents/templates/${templateId}/duplicate`,
      query: { new_name: newName },
    })
  },

  // Agent Activity (for popup)
  getAgentActivity: async (
    agentId: string,
    limit: number = 5,
  ): Promise<AgentActivityResponse> => {
    return __request(OpenAPI, {
      method: "GET",
      url: `/api/v1/agents/${agentId}/activity`,
      query: { limit },
    })
  },

  // ===== Token Usage Statistics =====

  getAgentsTokenStats: async (params?: {
    role_type?: string
    pool_name?: string
    limit?: number
  }): Promise<AgentTokenStats[]> => {
    return __request(OpenAPI, {
      method: "GET",
      url: "/api/v1/agents/stats/token-usage/agents",
      query: {
        role_type: params?.role_type,
        pool_name: params?.pool_name,
        limit: params?.limit || 100,
      },
    })
  },

  getPoolsTokenStats: async (): Promise<PoolTokenStats[]> => {
    return __request(OpenAPI, {
      method: "GET",
      url: "/api/v1/agents/stats/token-usage/pools",
    })
  },

  getSystemTokenSummary: async (): Promise<SystemTokenSummary> => {
    return __request(OpenAPI, {
      method: "GET",
      url: "/api/v1/agents/stats/token-usage/summary",
    })
  },

  resetDailyTokenStats: async (): Promise<{
    message: string
    agents_affected: number
  }> => {
    return __request(OpenAPI, {
      method: "POST",
      url: "/api/v1/agents/stats/token-usage/reset-daily",
    })
  },
}

// Agent Activity Response Type
export interface AgentActivityResponse {
  agent_id: string
  human_name: string
  role_type: string
  status: string
  status_message: string | null
  skills: string[]
  current_task: {
    id: string
    name: string
    status: string
    progress: number | null
    started_at: string
  } | null
  recent_activities: Array<{
    id: string
    activity_type: string
    content: string
    created_at: string
  }>
}

// ===== Utility Functions =====

/**
 * Generate a friendly display name for an agent
 * Format: Agent-{RolePrefix}-{IdSuffix}
 */
export function generateAgentDisplayName(
  agentId: string,
  roleName: string,
): string {
  const rolePrefix = getRolePrefix(roleName)
  const idSuffix = agentId.slice(0, 4).toUpperCase()
  return `Agent-${rolePrefix}-${idSuffix}`
}

function getRolePrefix(roleName: string): string {
  const prefixMap: Record<string, string> = {
    TeamLeader: "TL",
    "Team Leader": "TL",
    team_leader: "TL",
    BusinessAnalyst: "BA",
    "Business Analyst": "BA",
    business_analyst: "BA",
    Developer: "DEV",
    developer: "DEV",
    Tester: "QA",
    tester: "QA",
  }
  return prefixMap[roleName] || roleName.slice(0, 2).toUpperCase()
}

/**
 * Get status color variant for badges
 */
export function getStateVariant(
  state: AgentState,
): "default" | "secondary" | "destructive" | "outline" {
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
