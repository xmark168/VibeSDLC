// Backlog and Kanban-related types

export type StoryAgentState = 'PENDING' | 'PROCESSING' | 'PAUSED' | 'CANCEL_REQUESTED' | 'CANCELED' | 'FINISHED'

// Sub-status for PENDING state to show progress during restart
export type PendingSubStatus = 'queued' | 'cleaning' | 'starting' | null

export interface BacklogItem {
  id: string
  project_id: string
  parent_id?: string | null
  type: string
  title: string
  description?: string | null
  status: string
  reviewer_id?: string | null
  assignee_id?: string | null
  rank?: number | null
  story_point?: number | null
  priority?: number | null
  created_at: string
  updated_at: string
  parent?: BacklogItem | null
  children?: BacklogItem[]
  // Agent tracking
  agent_state?: StoryAgentState | null
  agent_sub_status?: PendingSubStatus  // Sub-status for PENDING state
  assigned_agent_id?: string | null
  branch_name?: string | null
  worktree_path?: string | null
  worktree_path_display?: string | null
  running_port?: number | null
  running_pid?: number | null
  pr_url?: string | null
  merge_status?: string | null
  started_at?: string | null
}

export interface KanbanBoard {
  project: {
    id: string
    name: string
  }
  board: {
    Backlog: BacklogItem[]
    Todo: BacklogItem[]
    InProgress: BacklogItem[]
    Doing: BacklogItem[]  // Legacy alias for InProgress
    Review: BacklogItem[]
    Done: BacklogItem[]
    Archived: BacklogItem[]
  }
  wip_limits?: {
    [key: string]: {
      wip_limit: number
      limit_type: 'hard' | 'soft'
    }
  }
}

export interface FetchBacklogItemsParams {
  project_id?: string
  status?: string
  assignee_id?: string
  type?: string
  skip?: number
  limit?: number
}

export interface WIPLimit {
  id: string
  project_id: string
  column_name: string
  wip_limit: number
  limit_type: 'hard' | 'soft'
}

export interface UpdateWIPLimitParams {
  wip_limit: number
  limit_type: 'hard' | 'soft'
}

export interface FlowMetrics {
  avg_cycle_time_hours: number | null
  avg_lead_time_hours: number | null
  throughput_per_week: number
  total_completed: number
  work_in_progress: number
  aging_items: Array<{
    id: string
    title: string
    status: string
    age_hours: number
  }>
  bottlenecks: Record<string, {
    avg_age_hours: number
    count: number
  }>
}

export interface StoryFormData {
  title: string
  description: string
  type: "UserStory" | "EnablerStory"
  story_point?: number
  priority?: "High" | "Medium" | "Low"
  acceptance_criteria: string[]
  requirements: string[]
  dependencies: string[]
  epic_id?: string
  // New epic fields (when creating new epic)
  new_epic_title?: string
  new_epic_domain?: string
  new_epic_description?: string
}
