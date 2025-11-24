/**
 * useAgentStatus - Agent status tracking hook
 * 
 * Responsibilities:
 * - Track typing indicators
 * - Monitor current agent status (thinking, acting, etc.)
 * - Track all agent statuses (for avatars)
 * 
 * Now uses event emitter pattern
 */

import { useState, useCallback, useEffect } from 'react'

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
  /** Event emitter from useWebSocketEvents */
  eventEmitter?: {
    on: (eventType: string, handler: (data: any) => void) => () => void
  }
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
  const { eventEmitter } = options

  const [currentAgent, setCurrentAgent] = useState<AgentStatus>({
    agentName: null,
    status: 'idle',
  })

  const [typingAgents, setTypingAgents] = useState<Set<string>>(new Set())
  const [agentStatuses, setAgentStatuses] = useState<AgentStatusMap>({})

  // Subscribe to events
  useEffect(() => {
    if (!eventEmitter) return

    const unsubscribers: Array<() => void> = []

    // Handle typing events
    const handleTyping = (data: any) => {
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
    }

    // Handle agent status events
    const handleAgentStatus = (data: any) => {
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
    }

    // Subscribe to events
    unsubscribers.push(eventEmitter.on('typing', handleTyping))
    unsubscribers.push(eventEmitter.on('agent_status', handleAgentStatus))

    // Cleanup
    return () => {
      unsubscribers.forEach(unsubscribe => unsubscribe())
    }
  }, [eventEmitter])

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
