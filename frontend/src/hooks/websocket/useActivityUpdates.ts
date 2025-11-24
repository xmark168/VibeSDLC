/**
 * useActivityUpdates - Activity and progress tracking hook
 * 
 * Responsibilities:
 * - Track agent execution progress
 * - Monitor tool calls
 * - Handle approval requests
 * 
 * Now uses event emitter pattern
 */

import { useState, useCallback, useEffect } from 'react'

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
  /** Event emitter from useWebSocketEvents */
  eventEmitter?: {
    on: (eventType: string, handler: (data: any) => void) => () => void
  }
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
  const { eventEmitter } = options

  const [agentProgress, setAgentProgress] = useState<AgentProgress>({
    isExecuting: false,
  })

  const [toolCalls, setToolCalls] = useState<ToolCall[]>([])
  const [approvalRequests, setApprovalRequests] = useState<ApprovalRequest[]>([])

  // Subscribe to events
  useEffect(() => {
    if (!eventEmitter) return

    const unsubscribers: Array<() => void> = []

    // Handle agent progress events
    const handleAgentProgress = (data: any) => {
      setAgentProgress({
        isExecuting: data.status === 'in_progress',
        currentStep: data.description || data.step_description,
        currentAgent: data.agent_name,
        stepNumber: data.step_number,
        totalSteps: data.total_steps,
      })
    }

    // Handle tool call events
    const handleToolCall = (data: any) => {
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
    }

    // Handle approval request events
    const handleApprovalRequest = (data: any) => {
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
    }

    // Subscribe to events
    unsubscribers.push(eventEmitter.on('agent_progress', handleAgentProgress))
    unsubscribers.push(eventEmitter.on('tool_call', handleToolCall))
    unsubscribers.push(eventEmitter.on('approval_request', handleApprovalRequest))

    // Cleanup
    return () => {
      unsubscribers.forEach(unsubscribe => unsubscribe())
    }
  }, [eventEmitter])

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
