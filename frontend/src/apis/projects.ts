import { request as __request } from "@client/core/request"
import { OpenAPI } from "@/client"
import type {
  Project,
  ProjectsPage,
  FetchProjectsParams,
  CreateProjectBody,
  UpdateProjectBody,
} from "@/types"

// Re-export types for convenience
export type { FetchProjectsParams, CreateProjectBody, UpdateProjectBody }

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

export const projectsApi = {
  list: async (params: FetchProjectsParams): Promise<ProjectsPage> => {
    return __request<ProjectsPage>(OpenAPI, {
      method: "GET",
      url: "/api/v1/projects/",
      query: buildProjectsQuery(params),
    })
  },
  create: async (body: CreateProjectBody): Promise<Project> => {
    return __request<Project>(OpenAPI, {
      method: "POST",
      url: "/api/v1/projects/",
      body,
    })
  },
  update: async (id: string, body: UpdateProjectBody): Promise<Project> => {
    return __request<Project>(OpenAPI, {
      method: "PATCH",
      url: `/api/v1/projects/${id}`,
      body,
    })
  },
}
