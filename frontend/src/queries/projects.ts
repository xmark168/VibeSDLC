import { useQuery } from '@tanstack/react-query'
import { projectsApi } from '@/apis/projects'
import type { FetchProjectsParams } from '@/apis/projects'

export function useProjects(params: FetchProjectsParams) {
  return useQuery({
    queryKey: ['projects', params],
    queryFn: () => projectsApi.list(params),
  })
}