import axiosInstance from '@/core/lib/axios'
import type {
  Project,
  CreateProjectData,
  UpdateProjectData,
  ProjectFilters,
} from '@/features/projects/types'
import type { BoardView } from '@/features/projects/types/board'

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
}

