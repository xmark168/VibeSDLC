import { useMutation } from "@tanstack/react-query"
import type { ExecuteAgentRequest } from "@/apis/agent"
import { agentApi } from "@/apis/agent"

export function useExecuteAgent() {
  return useMutation({
    mutationFn: (body: ExecuteAgentRequest) => agentApi.execute(body),
  })
}

export function useExecuteAgentSync() {
  return useMutation({
    mutationFn: (body: ExecuteAgentRequest) => agentApi.executeSync(body),
  })
}
