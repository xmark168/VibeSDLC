import { request as __request } from "@client/core/request"
import { OpenAPI } from "@/client"
import type { UserSubscriptionResponse } from "@/types/subscription"

export const subscriptionApi = {
  // Get current user's active subscription and credit wallet
  getCurrentSubscription: async (): Promise<UserSubscriptionResponse> => {
    return __request<UserSubscriptionResponse>(OpenAPI, {
      method: "GET",
      url: "/api/v1/users/me/subscription",
    })
  },

  // Cancel current subscription
  cancelSubscription: async (): Promise<{ message: string }> => {
    return __request<{ message: string }>(OpenAPI, {
      method: "POST",
      url: "/api/v1/users/me/subscription/cancel",
    })
  },

  // Update auto-renew setting
  updateAutoRenew: async (autoRenew: boolean): Promise<{ message: string }> => {
    return __request<{ message: string }>(OpenAPI, {
      method: "PUT",
      url: "/api/v1/users/me/subscription/auto-renew",
      body: { auto_renew: autoRenew },
    })
  },
}
