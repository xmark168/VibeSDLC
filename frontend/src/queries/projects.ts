import { useQuery } from '@tanstack/react-query'
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
      console.log('[useProjectTokenBudget] Fetching for projectId:', projectId)
      const response = await fetch(`/api/v1/projects/${projectId}/token-budget`, {
        credentials: 'include',
      })
      console.log('[useProjectTokenBudget] Response status:', response.status)
      if (!response.ok) {
        const errorText = await response.text()
        console.error('[useProjectTokenBudget] Error:', response.status, errorText)
        throw new Error(`Failed to fetch token budget: ${response.status}`)
      }
      const data = await response.json()
      console.log('[useProjectTokenBudget] Data:', data)
      return data
    },
    enabled: !!projectId,
    refetchInterval: 30000, // Refetch every 30 seconds
    retry: 2,
  })
}