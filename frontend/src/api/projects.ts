import { OpenAPI } from '@client'
import { request as __request } from '@client/core/request'
import type { ProjectsPage } from '@/types/project'

export async function fetchProjects(params: { search?: string; page?: number; pageSize?: number }): Promise<ProjectsPage> {
  const skip = Math.max(0, ((params.page ?? 1) - 1) * (params.pageSize ?? 10))
  const data = await __request<ProjectsPage>(OpenAPI, {
    method: 'GET',
    url: '/api/v1/projects/',
    query: {
      name: params.search || undefined,
      skip,
      limit: params.pageSize ?? 10,
    },
  })
  return data
}
