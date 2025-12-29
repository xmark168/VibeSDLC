import { request as __request } from "@client/core/request"
import { OpenAPI } from "@/client"
import type { CreditActivityResponse } from "@/types/subscription"

export const creditsApi = {
  /**
   * Get user's credit activities with pagination
   */
  getActivities: async (params: {
    limit?: number
    offset?: number
    project_id?: string
  }): Promise<CreditActivityResponse> => {
    return __request<CreditActivityResponse>(OpenAPI, {
      method: "GET",
      url: "/api/v1/credits/activities",
      query: {
        limit: params.limit || 20,
        offset: params.offset || 0,
        project_id: params.project_id,
      },
    })
  },
}
