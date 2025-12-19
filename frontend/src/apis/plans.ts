import { request as __request } from "@client/core/request"
import { OpenAPI } from "@/client"
import type {
  Plan,
  PlanCreate,
  PlanUpdate,
  PlansResponse,
  PlanFilters,
} from "@/types/plan"

// Re-export types for convenience
export type {
  Plan,
  PlanCreate,
  PlanUpdate,
  PlansResponse,
  PlanFilters,
}

// ===== API Client =====

export const plansApi = {
  // List plans with pagination and filters
  listPlans: async (params?: {
    skip?: number
    limit?: number
    search?: string
    tier?: string
    is_active?: boolean
    is_featured?: boolean
    order_by?: 'sort_index' | 'price' | 'created_at' | 'name'
  }): Promise<PlansResponse> => {
    return __request<PlansResponse>(OpenAPI, {
      method: "GET",
      url: "/api/v1/plans",
      query: {
        skip: params?.skip ?? 0,
        limit: params?.limit ?? 100,
        search: params?.search,
        tier: params?.tier,
        is_active: params?.is_active,
        is_featured: params?.is_featured,
        order_by: params?.order_by ?? 'sort_index',
      },
    })
  },

  // Get featured plans
  getFeaturedPlans: async (): Promise<Plan[]> => {
    return __request<Plan[]>(OpenAPI, {
      method: "GET",
      url: "/api/v1/plans/featured",
    })
  },

  // Get plan by ID
  getPlanById: async (planId: string): Promise<Plan> => {
    return __request<Plan>(OpenAPI, {
      method: "GET",
      url: `/api/v1/plans/${planId}`,
    })
  },

  // Create new plan (admin only)
  createPlan: async (body: PlanCreate): Promise<Plan> => {
    return __request<Plan>(OpenAPI, {
      method: "POST",
      url: "/api/v1/plans",
      body,
    })
  },

  // Update plan (admin only)
  updatePlan: async (planId: string, body: PlanUpdate): Promise<Plan> => {
    return __request<Plan>(OpenAPI, {
      method: "PATCH",
      url: `/api/v1/plans/${planId}`,
      body,
    })
  },

  // Delete plan (admin only)
  deletePlan: async (planId: string): Promise<{ message: string }> => {
    return __request<{ message: string }>(OpenAPI, {
      method: "DELETE",
      url: `/api/v1/plans/${planId}`,
    })
  },
}

// ===== Utility Functions =====

/**
 * Format price with currency
 */
export function formatPrice(price: number, currency: string = 'VND'): string {
  if (currency === 'VND') {
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND',
    }).format(price)
  }
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency,
  }).format(price)
}

/**
 * Get tier display name
 */
export function getTierLabel(tier: string): string {
  const labels: Record<string, string> = {
    free: 'Free',
    pay: 'Pay',
  }
  return labels[tier] || tier
}

/**
 * Get tier badge variant
 */
export function getTierVariant(tier: string): "default" | "secondary" | "destructive" | "outline" {
  switch (tier) {
    case 'free':
      return 'outline'
    case 'pay':
      return 'default'
    default:
      return 'outline'
  }
}

/**
 * Format discount percentage for display
 */
export function formatDiscount(discount: number | null): string {
  if (!discount || discount <= 0) return ''
  return `Save ${Math.round(discount)}%`
}

/**
 * Get effective price based on billing cycle
 */
export function getEffectivePrice(
  plan: Plan,
  billingCycle: 'monthly' | 'yearly'
): number | null {
  return billingCycle === 'monthly' ? plan.monthly_price : plan.yearly_price
}

/**
 * Check if plan supports a billing cycle
 */
export function supportsBillingCycle(
  plan: Plan,
  billingCycle: 'monthly' | 'yearly'
): boolean {
  return billingCycle === 'monthly'
    ? plan.monthly_price !== null
    : plan.yearly_price !== null
}
