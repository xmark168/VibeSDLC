import { OpenAPI } from '@client'
import { request as __request } from '@client/core/request'
import type {
  BacklogItem,
  KanbanBoard,
  FetchBacklogItemsParams,
  WIPLimit,
  UpdateWIPLimitParams,
  FlowMetrics,
} from '@/types'

// Re-export types for convenience
export type {
  BacklogItem,
  KanbanBoard,
  FetchBacklogItemsParams,
  WIPLimit,
  UpdateWIPLimitParams,
  FlowMetrics,
}

export const backlogItemsApi = {
  /**
   * Get Kanban board for a project
   */
  getKanbanBoard: async (projectId: string): Promise<KanbanBoard> => {
    return __request<KanbanBoard>(OpenAPI, {
      method: 'GET',
      url: `/api/v1/stories/kanban/${projectId}`,
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
  getWIPLimits: async (projectId: string): Promise<WIPLimit[]> => {
    return __request<WIPLimit[]>(OpenAPI, {
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

}

