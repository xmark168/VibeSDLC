import { OpenAPI } from "@client"
import { request as __request } from "@client/core/request"
import type {
  ExecuteAgentRequest,
  ExecuteAgentResponse,
  ExecuteAgentSyncResponse,
} from "@/types"

// Re-export types for convenience
export type { ExecuteAgentRequest, ExecuteAgentResponse, ExecuteAgentSyncResponse }

export const agentApi = {
  /**
   * Execute agent asynchronously (recommended for production)
   * Agent will send responses via WebSocket
   */
  execute: async (body: ExecuteAgentRequest): Promise<ExecuteAgentResponse> => {
    return __request<ExecuteAgentResponse>(OpenAPI, {
      method: "POST",
      url: "/api/v1/agent/execute",
      body,
    })
  },

  /**
   * Execute agent synchronously (blocking)
   * Use for testing or when you need immediate response
   */
  executeSync: async (
    body: ExecuteAgentRequest,
  ): Promise<ExecuteAgentSyncResponse> => {
    return __request<ExecuteAgentSyncResponse>(OpenAPI, {
      method: "POST",
      url: "/api/v1/agent/execute-sync",
      body,
    })
  },
}
