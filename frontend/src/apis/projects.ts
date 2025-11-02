
import { request as __request } from '@client/core/request'
import type { ProjectsPage, Project } from '@/types/project'
import { OpenAPI } from '@/client'

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
}
