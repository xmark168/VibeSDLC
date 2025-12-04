import { OpenAPI } from '@client'
import { request as __request } from '@client/core/request'
import type { 
  Story, 
  StoryFormData,
  CreateStoryResponse,
  UpdateStoryParams,
  StoryStatus,
  StoryType
} from '@/types'

// Re-export types for convenience
export type { 
  Story, 
  StoryFormData,
  CreateStoryResponse,
  UpdateStoryParams,
  StoryStatus,
  StoryType
}

export const storiesApi = {
  /**
   * Create a new story
   */
  create: async (data: {
    project_id: string
    title: string
    description?: string
    story_type: StoryType
    story_point?: number
    priority?: number
    acceptance_criteria?: string[]
    requirements?: string[]
    dependencies?: string[]
    epic_id?: string
    tags?: string[]
    labels?: string[]
    // New epic fields
    new_epic_title?: string
    new_epic_domain?: string
    new_epic_description?: string
  }): Promise<Story> => {
    return __request<Story>(OpenAPI, {
      method: 'POST',
      url: '/api/v1/stories/',
      body: {
        project_id: data.project_id,
        title: data.title,
        description: data.description,
        story_type: data.story_type,
        story_point: data.story_point,
        priority: data.priority || 3, // Default to medium priority (3)
        acceptance_criteria: data.acceptance_criteria || [],
        requirements: data.requirements || [],
        dependencies: data.dependencies || [],
        epic_id: data.epic_id,
        tags: data.tags || [],
        labels: data.labels || [],
        // New epic fields
        new_epic_title: data.new_epic_title,
        new_epic_domain: data.new_epic_domain,
        new_epic_description: data.new_epic_description,
      },
    })
  },

  /**
   * Get all stories for a project
   */
  list: async (
    projectId: string,
    params?: {
      status?: StoryStatus
      assignee_id?: string
      story_type?: StoryType
      skip?: number
      limit?: number
    }
  ): Promise<{ data: Story[]; count: number }> => {
    return __request<{ data: Story[]; count: number }>(OpenAPI, {
      method: 'GET',
      url: `/api/v1/stories/project/${projectId}`,
      query: {
        status: params?.status,
        assignee_id: params?.assignee_id,
        type: params?.story_type,
        skip: params?.skip ?? 0,
        limit: params?.limit ?? 100,
      },
    })
  },

  /**
   * Get single story
   */
  get: async (storyId: string): Promise<Story> => {
    return __request<Story>(OpenAPI, {
      method: 'GET',
      url: `/api/v1/stories/${storyId}`,
    })
  },

  /**
   * Update story
   */
  update: async (storyId: string, data: UpdateStoryParams): Promise<Story> => {
    return __request<Story>(OpenAPI, {
      method: 'PATCH',
      url: `/api/v1/stories/${storyId}`,
      body: data,
    })
  },

  /**
   * Update story status
   */
  updateStatus: async (storyId: string, status: StoryStatus): Promise<Story> => {
    return __request<Story>(OpenAPI, {
      method: 'PUT',
      url: `/api/v1/stories/${storyId}/status`,
      query: { new_status: status },
    })
  },

  /**
   * Assign story to a user
   */
  assign: async (
    storyId: string, 
    assigneeId: string, 
    reviewerId?: string
  ): Promise<Story> => {
    return __request<Story>(OpenAPI, {
      method: 'PUT',
      url: `/api/v1/stories/${storyId}/assign`,
      body: {
        assignee_id: assigneeId,
        reviewer_id: reviewerId,
      },
    })
  },

  /**
   * Delete story
   */
  delete: async (storyId: string): Promise<void> => {
    return __request<void>(OpenAPI, {
      method: 'DELETE',
      url: `/api/v1/stories/${storyId}`,
    })
  },

  /**
   * Handle review action (apply/keep/remove)
   */
  reviewAction: async (
    storyId: string,
    action: 'apply' | 'keep' | 'remove',
    suggestions?: {
      suggested_title?: string
      suggested_acceptance_criteria?: string[]
      suggested_requirements?: string[]
    }
  ): Promise<{ message: string; story_id: string }> => {
    return __request<{ message: string; story_id: string }>(OpenAPI, {
      method: 'POST',
      url: `/api/v1/stories/${storyId}/review-action`,
      body: {
        action,
        ...suggestions
      },
    })
  },

  /**
   * List all epics for a project
   */
  listEpics: async (
    projectId: string
  ): Promise<{ data: { id: string; epic_code?: string; title: string; description?: string; domain?: string; status?: string }[]; count: number }> => {
    return __request<{ data: { id: string; epic_code?: string; title: string; description?: string; domain?: string; status?: string }[]; count: number }>(OpenAPI, {
      method: 'GET',
      url: `/api/v1/stories/epics/${projectId}`,
    })
  }
}