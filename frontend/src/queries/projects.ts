import { useQuery } from '@tanstack/react-query'
import { projectsApi } from '@/apis/projects'
import type { FetchProjectsParams } from '@/apis/projects'

export function useProjects(params: FetchProjectsParams) {
  return useQuery({
    queryKey: ['projects', params],
    queryFn: () => projectsApi.list(params),
  })
}

export function useActiveSprint(projectId: string | undefined) {
  return useQuery({
    queryKey: ['active-sprint', projectId],
    queryFn: () => projectsApi.getActiveSprint(projectId!),
    enabled: !!projectId,
    retry: false, // Don't retry if no active sprint
    refetchOnMount: true, // Always refetch when component mounts
    staleTime: 0, // Consider data stale immediately
  })
}

export function useSprints(projectId: string | undefined) {
  return useQuery({
    queryKey: ['sprints', projectId],
    queryFn: () => projectsApi.getSprints(projectId!),
    enabled: !!projectId,
    refetchOnMount: true,
    staleTime: 0,
  })
}