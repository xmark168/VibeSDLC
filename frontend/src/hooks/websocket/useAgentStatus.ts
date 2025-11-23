/**
 * useAgentStatus - Agent status tracking hook
 * 
 * Responsibilities:
 * - Track typing indicators
 * - Monitor current agent status (thinking, acting, etc.)
 * - Track all agent statuses (for avatars)
 * - Handle agent status events
 * 
 * Depends on: WebSocket message events
 */

import { useState, useCallback } from 'react'

export type AgentStatusType = 
  | 'idle' 
  | 'thinking' 
  | 'acting' 
  | 'waiting' 
  | 'error'
  | 'busy'
  | 'running'
  | 'stopped'
  | 'starting'
  | 'stopping'
  | 'terminated'
  | 'created'

export interface AgentStatus {
  agentName: string | null
  status: AgentStatusType
  currentAction?: string
  executionId?: string
}

export interface AgentStatusMap {
  [agentName: string]: {
    status: AgentStatusType
    lastUpdate: string
  }
}

export interface UseAgentStatusOptions {
  /** Callback when message received */
  onMessage?: (event: MessageEvent) => void
}

export interface UseAgentStatusReturn {
  /** Currently active agent */
  currentAgent: AgentStatus
  /** Agents currently typing */
  typingAgents: string[]
  /** Map of all agent statuses */
  agentStatuses: AgentStatusMap
  /** Clear all statuses */
  clearStatuses: () => void
}

/**
 * Normalize status from backend format
 * "agent.thinking" -> "thinking"
 */
function normalizeStatus(status: string): AgentStatusType {
  const normalized = status.replace('agent.', '')
  return normalized as AgentStatusType
}

export function useAgentStatus(options: UseAgentStatusOptions = {}): UseAgentStatusReturn {
  const { onMessage } = options

  const [currentAgent, setCurrentAgent] = useState<AgentStatus>({
    agentName: null,
    status: 'idle',
  })

  const [typingAgents, setTypingAgents] = useState<Set<string>>(new Set())
  const [agentStatuses, setAgentStatuses] = useState<AgentStatusMap>({})

  // Handle incoming WebSocket message
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data)

      switch (data.type) {
        case 'typing': {
          if (data.agent_name) {
            setTypingAgents(prev => {
              const newSet = new Set(prev)
              if (data.is_typing) {
                newSet.add(data.agent_name)
              } else {
                newSet.delete(data.agent_name)
              }
              return newSet
            })
          }
          break
        }

        case 'agent_status': {
          const normalizedStatus = normalizeStatus(data.status || 'idle')
          
          // Update current agent
          setCurrentAgent({
            agentName: data.agent_name || null,
            status: normalizedStatus,
            currentAction: data.current_action,
            executionId: data.execution_id,
          })

          // Update global agent statuses map
          if (data.agent_name) {
            setAgentStatuses(prev => ({
              ...prev,
              [data.agent_name]: {
                status: normalizedStatus,
                lastUpdate: new Date().toISOString()
              }
            }))
          }
          break
        }

        default:
          // Not a status type we handle
          break
      }

      // Forward to parent callback
      onMessage?.(event)
    } catch (error) {
      console.error('[useAgentStatus] Failed to parse message:', error)
    }
  }, [onMessage])

  // Clear all statuses
  const clearStatuses = useCallback(() => {
    setCurrentAgent({ agentName: null, status: 'idle' })
    setTypingAgents(new Set())
    setAgentStatuses({})
  }, [])

  return {
    currentAgent,
    typingAgents: Array.from(typingAgents),
    agentStatuses,
    clearStatuses,
  }
}
