import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  plansApi,
  type PlanCreate,
  type PlanUpdate,
  type PlanFilters,
} from "@/apis/plans"
import { toast } from "sonner"

// ===== Query Keys =====
export const planQueryKeys = {
  all: ["plans"] as const,
  lists: () => [...planQueryKeys.all, "list"] as const,
  list: (filters?: PlanFilters, skip?: number, limit?: number) =>
    [...planQueryKeys.lists(), filters, skip, limit] as const,
  featured: () => [...planQueryKeys.all, "featured"] as const,
  detail: (planId: string) => [...planQueryKeys.all, "detail", planId] as const,
}

// ===== Queries =====

/**
 * Fetch all plans with pagination and filters
 */
export function usePlans(
  params?: {
    skip?: number
    limit?: number
    search?: string
    tier?: string
    billing_cycle?: string
    is_active?: boolean
    is_featured?: boolean
    order_by?: 'sort_index' | 'price' | 'created_at' | 'name'
  },
  options?: { enabled?: boolean }
) {
  return useQuery({
    queryKey: planQueryKeys.list(
      {
        search: params?.search,
        tier: params?.tier,
        billing_cycle: params?.billing_cycle,
        is_active: params?.is_active,
        is_featured: params?.is_featured,
        order_by: params?.order_by,
      },
      params?.skip,
      params?.limit
    ),
    queryFn: () => plansApi.listPlans(params),
    enabled: options?.enabled ?? true,
    staleTime: 30000, // Consider stale after 30s
  })
}

/**
 * Fetch featured plans
 */
export function useFeaturedPlans(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: planQueryKeys.featured(),
    queryFn: () => plansApi.getFeaturedPlans(),
    enabled: options?.enabled ?? true,
    staleTime: 60000, // Consider stale after 1min
  })
}

/**
 * Fetch plan by ID
 */
export function usePlan(planId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: planQueryKeys.detail(planId),
    queryFn: () => plansApi.getPlanById(planId),
    enabled: (options?.enabled ?? true) && !!planId,
    staleTime: 30000,
  })
}

// ===== Mutations =====

/**
 * Create new plan
 */
export function useCreatePlan() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: PlanCreate) => plansApi.createPlan(data),
    onSuccess: () => {
      // Invalidate all plan lists to refetch
      queryClient.invalidateQueries({ queryKey: planQueryKeys.lists() })
      queryClient.invalidateQueries({ queryKey: planQueryKeys.featured() })
      toast.success("Plan created successfully")
    },
    onError: (error: any) => {
      const message = error?.body?.detail || error?.message || "Failed to create plan"
      toast.error(message)
    },
  })
}

/**
 * Update existing plan
 */
export function useUpdatePlan() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ planId, data }: { planId: string; data: PlanUpdate }) =>
      plansApi.updatePlan(planId, data),
    onSuccess: (data, variables) => {
      // Invalidate lists
      queryClient.invalidateQueries({ queryKey: planQueryKeys.lists() })
      queryClient.invalidateQueries({ queryKey: planQueryKeys.featured() })
      // Update specific plan cache
      queryClient.setQueryData(planQueryKeys.detail(variables.planId), data)
      toast.success("Plan updated successfully")
    },
    onError: (error: any) => {
      const message = error?.body?.detail || error?.message || "Failed to update plan"
      toast.error(message)
    },
  })
}

/**
 * Delete plan
 */
export function useDeletePlan() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (planId: string) => plansApi.deletePlan(planId),
    onSuccess: () => {
      // Invalidate all plan queries
      queryClient.invalidateQueries({ queryKey: planQueryKeys.all })
      toast.success("Plan deleted successfully")
    },
    onError: (error: any) => {
      const message = error?.body?.detail || error?.message || "Failed to delete plan"
      toast.error(message)
    },
  })
}
