import axiosInstance from '@/core/lib/axios'
import type {
  Project,
  CreateProjectData,
  UpdateProjectData,
  ProjectFilters,
} from '@/features/projects/types'
import type { BoardView, Story } from '@/features/projects/types/board'
import type { Epic, CreateEpicData, UpdateEpicData } from '@/features/projects/types/epic'

// Story creation data
export interface CreateStoryData {
  title: string
  description?: string
  epic_id: number
  type: string
  priority: string
  acceptance_criteria?: string
}

// Story response from backend
export interface StoryResponse extends Story {
  created_by_id: number
  token_used?: number
}

export const projectsAPI = {
  // Get all projects for the current user with optional filters
  async getProjects(filters?: ProjectFilters): Promise<Project[]> {
    const response = await axiosInstance.get<Project[]>('/projects', { params: filters })
    return response.data
  },

  // Get a single project by ID
  async getProject(id: number): Promise<Project> {
    const response = await axiosInstance.get<Project>(`/projects/${id}`)
    return response.data
  },

  // Create a new project
  async createProject(data: CreateProjectData): Promise<Project> {
    const response = await axiosInstance.post<Project>('/projects', data)
    return response.data
  },

  // Update a project
  async updateProject(id: number, data: UpdateProjectData): Promise<Project> {
    const response = await axiosInstance.put<Project>(`/projects/${id}`, data)
    return response.data
  },

  // Update Kanban policy specifically
  async updateKanbanPolicy(id: number, kanbanPolicy: any): Promise<Project> {
    const response = await axiosInstance.put<Project>(`/projects/${id}/kanban-policy`, kanbanPolicy)
    return response.data
  },

  // Delete a project
  async deleteProject(id: number): Promise<void> {
    await axiosInstance.delete(`/projects/${id}`)
  },

  // Get Kanban board view
  async getProjectBoard(id: number): Promise<BoardView> {
    const response = await axiosInstance.get<BoardView>(`/projects/${id}/board`)
    return response.data
  },

  // Create a new story
  async createStory(data: CreateStoryData): Promise<StoryResponse> {
    const response = await axiosInstance.post<StoryResponse>('/stories', data)
    return response.data
  },

  // Update story status (for Kanban workflow)
  async updateStoryStatus(storyId: number, newStatus: string): Promise<Story> {
    const response = await axiosInstance.put<Story>(`/stories/${storyId}/status`, {
      new_status: newStatus
    })
    return response.data
  },

  // Epic Management
  async getEpicsByProject(projectId: number): Promise<Epic[]> {
    const response = await axiosInstance.get<Epic[]>(`/epics?project_id=${projectId}`)
    return response.data
  },

  async getEpic(epicId: number): Promise<Epic> {
    const response = await axiosInstance.get<Epic>(`/epics/${epicId}`)
    return response.data
  },

  async createEpic(data: CreateEpicData): Promise<Epic> {
    const response = await axiosInstance.post<Epic>('/epics', data)
    return response.data
  },

  async updateEpic(epicId: number, data: UpdateEpicData): Promise<Epic> {
    const response = await axiosInstance.put<Epic>(`/epics/${epicId}`, data)
    return response.data
  },

  async deleteEpic(epicId: number): Promise<void> {
    await axiosInstance.delete(`/epics/${epicId}`)
  },
}

