import { OpenAPI } from '@client'
import { request as __request } from '@client/core/request'
import type { ProjectsPage, Project } from '@/types/project'

export type FetchProjectsParams = {
  search?: string
  page?: number
  pageSize?: number
}

export function buildProjectsQuery(params: FetchProjectsParams) {
  const page = params.page ?? 1
  const pageSize = params.pageSize ?? 10
  const skip = Math.max(0, (page - 1) * pageSize)
  return {
    name: params.search || undefined,
    skip,
    limit: pageSize,
  }
}

export type CreateProjectBody = {
  code: string
  name: string
  owner_id: string
  is_init?: boolean
}

export type UpdateProjectBody = {
  code?: string
  name?: string
  is_init?: boolean
}

export interface Sprint {
  id: string
  project_id: string
  name: string
  number: number
  goal: string
  status: string
  start_date: string
  end_date: string
  velocity_plan: string
  velocity_actual: string
  created_at: string
  updated_at: string
}

export const projectsApi = {
  list: async (params: FetchProjectsParams): Promise<ProjectsPage> => {
    return __request<ProjectsPage>(OpenAPI, {
      method: 'GET',
      url: '/api/v1/projects/',
      query: buildProjectsQuery(params),
    })
  },
  create: async (body: CreateProjectBody): Promise<Project> => {
    return __request<Project>(OpenAPI, {
      method: 'POST',
      url: '/api/v1/projects/',
      body,
    })
  },
  update: async (id: string, body: UpdateProjectBody): Promise<Project> => {
    return __request<Project>(OpenAPI, {
      method: 'PATCH',
      url: `/api/v1/projects/${id}`,
      body,
    })
  },
  getActiveSprint: async (projectId: string): Promise<Sprint> => {
    return __request<Sprint>(OpenAPI, {
      method: 'GET',
      url: `/api/v1/sprints/project/${projectId}/active`,
    })
  },
  getSprints: async (projectId: string): Promise<{ data: Sprint[]; count: number }> => {
    return __request<{ data: Sprint[]; count: number }>(OpenAPI, {
      method: 'GET',
      url: '/api/v1/sprints/',
      query: {
        project_id: projectId,
        limit: 100,
      },
    })
  },
}
