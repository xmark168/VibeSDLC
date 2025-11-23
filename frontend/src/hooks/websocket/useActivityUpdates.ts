/**
 * useActivityUpdates - Activity and progress tracking hook
 * 
 * Responsibilities:
 * - Track agent execution progress
 * - Monitor tool calls
 * - Handle approval requests
 * - Track agent progress events
 * 
 * Depends on: WebSocket message events
 */

import { useState, useCallback } from 'react'

export interface AgentProgress {
  isExecuting: boolean
  currentStep?: string
  currentAgent?: string
  currentTool?: string
  stepNumber?: number
  totalSteps?: number
}

export interface ToolCall {
  agent_name?: string
  tool_name?: string
  display_name?: string
  status?: string
  timestamp?: string
  parameters?: any
  result?: any
  error_message?: string
}

export interface ApprovalRequest {
  id?: string
  request_type?: string
  agent_name?: string
  proposed_data?: any
  preview_data?: any
  explanation?: string
  timestamp?: string
}

export interface UseActivityUpdatesOptions {
  /** Callback when message received */
  onMessage?: (event: MessageEvent) => void
}

export interface UseActivityUpdatesReturn {
  /** Current agent progress */
  agentProgress: AgentProgress
  /** List of tool calls */
  toolCalls: ToolCall[]
  /** List of approval requests */
  approvalRequests: ApprovalRequest[]
  /** Clear all activity data */
  clearActivities: () => void
}

export function useActivityUpdates(options: UseActivityUpdatesOptions = {}): UseActivityUpdatesReturn {
  const { onMessage } = options

  const [agentProgress, setAgentProgress] = useState<AgentProgress>({
    isExecuting: false,
  })

  const [toolCalls, setToolCalls] = useState<ToolCall[]>([])
  const [approvalRequests, setApprovalRequests] = useState<ApprovalRequest[]>([])

  // Handle incoming WebSocket message
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data)

      switch (data.type) {
        case 'agent_progress': {
          setAgentProgress({
            isExecuting: data.status === 'in_progress',
            currentStep: data.description || data.step_description,
            currentAgent: data.agent_name,
            stepNumber: data.step_number,
            totalSteps: data.total_steps,
          })
          break
        }

        case 'tool_call': {
          const toolCall: ToolCall = {
            agent_name: data.agent_name,
            tool_name: data.tool_name,
            display_name: data.display_name,
            status: data.status,
            timestamp: data.timestamp,
            parameters: data.parameters,
            result: data.result,
            error_message: data.error_message,
          }

          setToolCalls(prev => [...prev, toolCall])

          // Update progress to show tool being used
          if (data.status === 'started') {
            setAgentProgress(prev => ({
              ...prev,
              currentTool: data.display_name || data.tool_name,
            }))
          }
          break
        }

        case 'approval_request': {
          const request: ApprovalRequest = {
            id: data.approval_request_id,
            request_type: data.request_type,
            agent_name: data.agent_name,
            proposed_data: data.proposed_data,
            preview_data: data.preview_data,
            explanation: data.explanation,
            timestamp: data.timestamp,
          }

          setApprovalRequests(prev => [...prev, request])
          break
        }

        default:
          // Not an activity type we handle
          break
      }

      // Forward to parent callback
      onMessage?.(event)
    } catch (error) {
      console.error('[useActivityUpdates] Failed to parse message:', error)
    }
  }, [onMessage])

  // Clear all activities
  const clearActivities = useCallback(() => {
    setAgentProgress({ isExecuting: false })
    setToolCalls([])
    setApprovalRequests([])
  }, [])

  return {
    agentProgress,
    toolCalls,
    approvalRequests,
    clearActivities,
  }
}
