import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { backlogItemsApi, type UpdateWIPLimitParams } from '@/apis/backlog-items'

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

export function useWIPLimits(projectId: string | undefined) {
  return useQuery({
    queryKey: ['wip-limits', projectId],
    queryFn: async () => {
      const response = await backlogItemsApi.getWIPLimits(projectId!)
      return response
    },
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

export function useFlowMetrics(projectId: string | undefined, days: number = 30) {
  return useQuery({
    queryKey: ['flow-metrics', projectId, days],
    queryFn: () => backlogItemsApi.getFlowMetrics(projectId!, days),
    enabled: !!projectId,
    refetchInterval: 60000, // Refresh every minute
  })
}

