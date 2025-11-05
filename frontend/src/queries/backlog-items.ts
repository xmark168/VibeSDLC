import { useQuery } from '@tanstack/react-query'
import { backlogItemsApi } from '@/apis/backlog-items'

export function useKanbanBoard(sprintId: string | undefined) {
  return useQuery({
    queryKey: ['kanban-board', sprintId],
    queryFn: () => backlogItemsApi.getKanbanBoard(sprintId!),
    enabled: !!sprintId,
    refetchOnWindowFocus: true,
    staleTime: 30000, // 30 seconds
  })
}

