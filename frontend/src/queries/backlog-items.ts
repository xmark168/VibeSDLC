import { useQuery } from '@tanstack/react-query'
import { backlogItemsApi } from '@/apis/backlog-items'

export function useKanbanBoard(projectId: string | undefined) {
  return useQuery({
    queryKey: ['kanban-board', projectId],
    queryFn: () => backlogItemsApi.getKanbanBoard(projectId!),
    enabled: !!projectId,
    refetchOnWindowFocus: true,
    refetchOnMount: true, // Always refetch when component mounts
    staleTime: 0, // Consider data stale immediately to ensure fresh data
  })
}

