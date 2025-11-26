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
}
