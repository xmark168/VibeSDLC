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
  id: string
  pool_name: string
  role_type: string
  priority: number
  total_agents: number
  active_agents: number
  busy_agents: number
  idle_agents: number
  max_agents: number
  is_running: boolean
  total_spawned: number
  total_terminated: number
  total_executions: number
  successful_executions: number
  failed_executions: number
  success_rate: number
  load: number
  created_at: string
  agents: Array<{
    agent_id: string
    name: string
    role: string
    state: string
  }>
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
  project_id: string
  role_type: string
  pool_name?: string
  human_name?: string
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

// ===== Pool DB Types =====

export type PoolType = "free" | "paid"

export interface AgentPoolDB {
  id: string
  pool_name: string
  role_type: string | null
  pool_type: PoolType
  priority: number
  max_agents: number
  health_check_interval: number
  llm_model_config: Record<string, string> | null
  allowed_template_ids: string[] | null
  is_active: boolean
  last_started_at: string | null
  last_stopped_at: string | null
  total_spawned: number
  total_terminated: number
  current_agent_count: number
  created_by: string | null
  updated_by: string | null
  auto_created: boolean
  created_at: string
  updated_at: string
}

export interface AgentPoolMetrics {
  id: string
  pool_id: string
  period_start: string
  period_end: string
  total_tokens_used: number
  tokens_per_model: Record<string, number>
  total_requests: number
  requests_per_model: Record<string, number>
  peak_agent_count: number
  avg_agent_count: number
  total_executions: number
  successful_executions: number
  failed_executions: number
  avg_execution_duration_ms: number | null
  snapshot_metadata: Record<string, any> | null
  created_at: string
}

export interface PoolResponseExtended extends PoolResponse {
  // DB info
  pool_id: string
  pool_type: PoolType
  llm_model_config: Record<string, string> | null
  allowed_template_ids: string[] | null
  is_active: boolean
  auto_created: boolean
  uptime_seconds: number
}

export interface CreatePoolRequestExtended {
  pool_name: string
  role_type?: string | null
  pool_type?: PoolType
  max_agents?: number
  health_check_interval?: number
  llm_model_config?: Record<string, string>
  allowed_template_ids?: string[]
}

export interface UpdatePoolConfigRequest {
  pool_id: string
  max_agents?: number
  health_check_interval?: number
  llm_model_config?: Record<string, string>
  allowed_template_ids?: string[]
  updated_by?: string
}

export interface ScalePoolRequest {
  target_agents: number
}

export interface PoolSuggestion {
  reason: string
  recommended_pool_name: string
  role_type: string | null
  estimated_agents: number
}

// ===== Emergency Controls Types =====

export type SystemStatus = "running" | "paused" | "maintenance" | "stopped"

export interface SystemStatusResponse {
  status: SystemStatus
  paused_at: string | null
  maintenance_message: string | null
  active_pools: number
  total_agents: number
  accepting_tasks: boolean
}

export interface EmergencyActionResponse {
  message: string
  status: SystemStatus
  paused_at?: string
  stopped_at?: string
  started_at?: string
  previous_status?: SystemStatus
  maintenance_message?: string
  agents_affected?: number
  agents_stopped?: number
  agents_failed?: number
  force?: boolean
}

// ===== Bulk Operations Types =====

export interface BulkOperationResponse {
  success_count: number
  failed_count: number
  total_requested: number
  results: Array<{
    agent_id?: string
    index?: number
    status: string
    error?: string
    pool?: string
    previous_state?: string
    agent_name?: string
  }>
  message: string
}

// ===== Auto-scaling Types =====

export type ScalingTriggerType = "schedule" | "load" | "queue_depth"
export type ScalingAction = "scale_up" | "scale_down" | "set_count"

export interface AutoScalingRule {
  id?: string
  name: string
  pool_name: string
  enabled: boolean
  trigger_type: ScalingTriggerType
  cron_expression?: string
  timezone?: string
  metric?: string
  threshold_high?: number
  threshold_low?: number
  cooldown_seconds: number
  action: ScalingAction
  target_count?: number
  scale_amount: number
  min_agents: number
  max_agents: number
  role_type?: string
  created_at?: string
  last_triggered?: string
}

export interface AutoScalingRuleCreate {
  name: string
  pool_name: string
  enabled?: boolean
  trigger_type: ScalingTriggerType
  cron_expression?: string
  timezone?: string
  metric?: string
  threshold_high?: number
  threshold_low?: number
  cooldown_seconds?: number
  action: ScalingAction
  target_count?: number
  scale_amount?: number
  min_agents?: number
  max_agents?: number
  role_type?: string
}

// ===== Agent Template Types =====

export interface AgentTemplate {
  id?: string
  name: string
  description?: string
  role_type: string
  pool_name: string
  llm_config: Record<string, unknown>
  persona_name?: string
  system_prompt_override?: string
  max_idle_time: number
  heartbeat_interval: number
  tags: string[]
  created_by?: string
  created_at?: string
  updated_at?: string
  use_count: number
}

export interface AgentTemplateCreate {
  name: string
  description?: string
  role_type: string
  pool_name?: string
  llm_config?: Record<string, unknown>
  persona_name?: string
  system_prompt_override?: string
  max_idle_time?: number
  heartbeat_interval?: number
  tags?: string[]
}

export interface AgentTemplateFromAgent {
  agent_id: string
  template_name: string
  description?: string
  tags?: string[]
}

// ===== Token Usage Statistics Types =====

export interface AgentTokenStats {
  agent_id: string
  agent_name: string
  role_type: string
  pool_name: string | null
  tokens_used_total: number
  tokens_used_today: number
  llm_calls_total: number
  status: string
  created_at: string | null
}

export interface PoolTokenStats {
  pool_id: string
  pool_name: string
  role_type: string | null
  total_tokens_used: number
  total_llm_calls: number
  total_agents: number
  agents_stats: AgentTokenStats[]
}

export interface SystemTokenSummary {
  total_tokens_all_time: number
  total_tokens_today: number
  total_llm_calls: number
  total_agents: number
  total_pools: number
  by_role_type: Record<string, {
    total_tokens: number
    tokens_today: number
    llm_calls: number
    agent_count: number
  }>
  by_pool: PoolTokenStats[]
  estimated_cost_usd: number
}
