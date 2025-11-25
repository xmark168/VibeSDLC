// Backlog and Kanban-related types

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
  estimate_value?: number | null
  story_point?: number | null
  pause: boolean
  deadline?: string | null
  created_at: string
  updated_at: string
  parent?: BacklogItem | null
  children?: BacklogItem[]
}

export interface KanbanBoard {
  project: {
    id: string
    name: string
  }
  board: {
    Backlog: BacklogItem[]
    Todo: BacklogItem[]
    Doing: BacklogItem[]
    Done: BacklogItem[]
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
