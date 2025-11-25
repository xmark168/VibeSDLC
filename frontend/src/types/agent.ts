// Agent-related types

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

export type AgentStatus = "idle" | "busy" | "stopped" | "error"

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

export interface ExecuteAgentRequest {
  project_id: string
  user_input: string
  agent_name?: string
}

export interface ExecuteAgentResponse {
  execution_id: string
  status: string
  message: string
}

export interface ExecuteAgentSyncResponse {
  status: string
  result: any
  execution_time: number
}
