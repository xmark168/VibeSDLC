import { useQuery } from '@tanstack/react-query'
import { backlogItemsApi } from '@/apis/backlog-items'

export function useKanbanBoard(sprintId: string | undefined) {
  return useQuery({
    queryKey: ['kanban-board', sprintId],
    queryFn: () => backlogItemsApi.getKanbanBoard(sprintId!),
    enabled: !!sprintId,
    refetchOnWindowFocus: true,
    refetchOnMount: true, // Always refetch when component mounts
    staleTime: 0, // Consider data stale immediately to ensure fresh data
  })
}

