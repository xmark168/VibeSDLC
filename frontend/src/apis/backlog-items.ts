import { OpenAPI } from '@client'
import { request as __request } from '@client/core/request'

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
  // TraDS ============= Kanban Hierarchy: Parent/children relationships
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

export const backlogItemsApi = {
  /**
   * Get Kanban board for a project
   */
  getKanbanBoard: async (projectId: string): Promise<KanbanBoard> => {
    return __request<KanbanBoard>(OpenAPI, {
      method: 'GET',
      url: `/api/v1/backlog-items/project/${projectId}/kanban`,
    })
  },

  /**
   * List backlog items with filters
   */
  list: async (params: FetchBacklogItemsParams): Promise<{ data: BacklogItem[]; count: number }> => {
    return __request<{ data: BacklogItem[]; count: number }>(OpenAPI, {
      method: 'GET',
      url: '/api/v1/backlog-items/',
      query: {
        project_id: params.project_id,
        status: params.status,
        assignee_id: params.assignee_id,
        type: params.type,
        skip: params.skip ?? 0,
        limit: params.limit ?? 100,
      },
    })
  },

  /**
   * Get single backlog item
   */
  get: async (itemId: string): Promise<BacklogItem> => {
    return __request<BacklogItem>(OpenAPI, {
      method: 'GET',
      url: `/api/v1/backlog-items/${itemId}`,
    })
  },

  /**
   * Get WIP limits for a project
   */
  getWIPLimits: async (projectId: string): Promise<{ data: WIPLimit[]; count: number }> => {
    return __request<{ data: WIPLimit[]; count: number }>(OpenAPI, {
      method: 'GET',
      url: `/api/v1/projects/${projectId}/wip-limits`,
    })
  },

  /**
   * Update WIP limit for a specific column
   */
  updateWIPLimit: async (
    projectId: string,
    columnName: string,
    params: UpdateWIPLimitParams
  ): Promise<WIPLimit> => {
    return __request<WIPLimit>(OpenAPI, {
      method: 'PUT',
      url: `/api/v1/projects/${projectId}/wip-limits/${columnName}`,
      body: params,
    })
  },

  /**
   * Get flow metrics for a project
   */
  getFlowMetrics: async (projectId: string, days: number = 30): Promise<FlowMetrics> => {
    return __request<FlowMetrics>(OpenAPI, {
      method: 'GET',
      url: `/api/v1/projects/${projectId}/flow-metrics`,
      query: { days },
    })
  },

  /**
   * Validate if a story can be moved to target status (WIP + Policy check)
   */
  validateStoryMove: async (
    projectId: string,
    storyId: string,
    targetStatus: string
  ): Promise<{ allowed: boolean; violation: any; warning?: boolean }> => {
    return __request<{ allowed: boolean; violation: any; warning?: boolean }>(OpenAPI, {
      method: 'POST',
      url: `/api/v1/projects/${projectId}/stories/${storyId}/validate-wip`,
      query: { target_status: targetStatus },
    })
  },

  /**
   * Validate if a story move meets workflow policy criteria
   */
  validatePolicyMove: async (
    projectId: string,
    storyId: string,
    fromStatus: string,
    toStatus: string
  ): Promise<{ allowed: boolean; violations: string[] }> => {
    return __request<{ allowed: boolean; violations: string[] }>(OpenAPI, {
      method: 'POST',
      url: `/api/v1/projects/${projectId}/stories/${storyId}/validate-policy`,
      query: {
        from_status: fromStatus,
        to_status: toStatus
      },
    })
  },
}

