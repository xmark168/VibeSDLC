import { useQuery } from '@tanstack/react-query'
import { request as __request } from '@/client/core/request'
import { OpenAPI } from '@/client'
import { projectsApi } from '@/apis/projects'
import type { FetchProjectsParams } from '@/apis/projects'

export function useProjects(params: FetchProjectsParams) {
  return useQuery({
    queryKey: ['projects', params],
    queryFn: () => projectsApi.list(params),
  })
}

export function useProjectTokenBudget(projectId: string | undefined) {
  return useQuery({
    queryKey: ['project-token-budget', projectId],
    queryFn: async () => {
      if (!projectId) return null
      
      return __request(OpenAPI, {
        method: 'GET',
        url: `/api/v1/projects/${projectId}/token-budget`,
      })
    },
    enabled: !!projectId,
    refetchInterval: 30000,
    retry: 2,
  })
}