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
}

