import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { backlogItemsApi, type UpdateWIPLimitParams } from '@/apis/backlog-items'

export function useKanbanBoard(projectId: string | undefined) {
  return useQuery({
    queryKey: ['kanban-board', projectId],
    queryFn: async () => {
      console.log('[useKanbanBoard] Fetching data for projectId:', projectId)
      const result = await backlogItemsApi.getKanbanBoard(projectId!)
      console.log('[useKanbanBoard] Received data:', result)
      return result
    },
    enabled: !!projectId,
    refetchOnWindowFocus: false,
    refetchOnMount: true, // Always refetch when component mounts
    staleTime: 0, // Consider data stale immediately to ensure fresh data
    structuralSharing: false, // Disable structural sharing to always get new reference on refetch
  })
}

export function useWIPLimits(projectId: string | undefined) {
  return useQuery({
    queryKey: ['wip-limits', projectId],
    queryFn: () => backlogItemsApi.getWIPLimits(projectId!),
    enabled: !!projectId,
  })
}

export function useUpdateWIPLimit(projectId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ columnName, params }: { columnName: string; params: UpdateWIPLimitParams }) =>
      backlogItemsApi.updateWIPLimit(projectId, columnName, params),
    onSuccess: () => {
      // Invalidate both WIP limits and kanban board queries to refresh the UI
      queryClient.invalidateQueries({ queryKey: ['wip-limits', projectId] })
      queryClient.invalidateQueries({ queryKey: ['kanban-board', projectId] })
    },
  })
}



