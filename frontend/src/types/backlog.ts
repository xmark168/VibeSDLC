// Backlog and Kanban-related types

export type StoryAgentState = 'pending' | 'processing' | 'canceled' | 'finished'

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
  deadline?: string | null
  created_at: string
  updated_at: string
  parent?: BacklogItem | null
  children?: BacklogItem[]
  // Agent tracking
  agent_state?: StoryAgentState | null
  assigned_agent_id?: string | null
  branch_name?: string | null
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
}
