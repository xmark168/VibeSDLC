import { OpenAPI } from "@client"
import { request as __request } from "@client/core/request"

export type ExecuteAgentRequest = {
  project_id: string
  user_input: string
  agent_type?: "po_agent"
}

export type ExecuteAgentResponse = {
  execution_id: string
  status: string
  message: string
}

export type ExecuteAgentSyncResponse = {
  status: string
  result: any
}

// TraDS: Sprint Planner Test Types
export type TestSprintPlannerRequest = {
  project_id: string
}

export type TestSprintPlannerResponse = {
  status: string
  message: string
}

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

  // TraDS: Test Sprint Planner with mock PO output
  testSprintPlanner: async (
    body: TestSprintPlannerRequest,
  ): Promise<TestSprintPlannerResponse> => {
    return __request<TestSprintPlannerResponse>(OpenAPI, {
      method: "POST",
      url: "/api/v1/scrum-master-test/test-sprint-planner",
      body,
    })
  },
}
