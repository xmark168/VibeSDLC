/**
 * useChatWebSocket - Facade hook combining all WebSocket functionality
 * 
 * This is the main hook that provides a complete interface for chat features.
 * It combines all specialized hooks using event emitter pattern.
 * 
 * Architecture (Refactored):
 * - useWebSocket: Base connection
 * - useWebSocketEvents: Event distribution (NEW!)
 * - useWebSocketMessages: Message handling (subscribes to events)
 * - useAgentStatus: Agent status tracking (subscribes to events)
 * - useActivityUpdates: Progress tracking (subscribes to events)
 * - useKanbanUpdates: Kanban board updates (subscribes to events)
 */

import { useEffect, useCallback } from 'react'
import { useWebSocket, type WebSocketState } from './useWebSocket'
import { useWebSocketEvents } from './useWebSocketEvents'
import { useWebSocketMessages } from './useWebSocketMessages'
import { useAgentStatus, type AgentStatusMap } from './useAgentStatus'
import { useActivityUpdates } from './useActivityUpdates'
import { useKanbanUpdates, type KanbanData } from './useKanbanUpdates'
import type { Message } from '@/types/message'

export interface UseChatWebSocketOptions {
  /** Project ID */
  projectId?: string
  /** Auth token */
  token?: string
  /** Auto-reconnect on disconnect */
  autoReconnect?: boolean
  /** Callback when connection changes */
  onConnectionChange?: (connected: boolean) => void
  /** Callback when kanban data changes */
  onKanbanDataChange?: (data: KanbanData | null) => void
  /** Callback when active tab changes */
  onActiveTabChange?: (tab: string | null) => void
  /** Callback when agent statuses change */
  onAgentStatusesChange?: (statuses: AgentStatusMap) => void
}

export interface SendMessageParams {
  content: string
  author_type?: 'user' | 'agent'
  agent_id?: string
  agent_name?: string
}

export interface UseChatWebSocketReturn {
  // Connection state
  isConnected: boolean
  isReady: boolean
  
  // Messages
  messages: Message[]
  
  // Agent status
  typingAgents: string[]
  agentStatus: {
    agentName: string | null
    status: 'idle' | 'thinking' | 'acting' | 'waiting' | 'error'
    currentAction?: string
    executionId?: string
  }
  agentStatuses: AgentStatusMap
  
  // Activity tracking
  agentProgress: {
    isExecuting: boolean
    currentStep?: string
    currentAgent?: string
    currentTool?: string
    stepNumber?: number
    totalSteps?: number
  }
  toolCalls: any[]
  approvalRequests: any[]
  
  // Kanban
  kanbanData: KanbanData | null
  activeTab: string | null
  
  // Actions
  sendMessage: (params: SendMessageParams) => boolean
  connect: () => void
  disconnect: () => void
}

export function useChatWebSocket(
  projectId: string | undefined,
  token: string | undefined,
  options: UseChatWebSocketOptions = {}
): UseChatWebSocketReturn {
  const {
    autoReconnect = true,
    onConnectionChange,
    onKanbanDataChange,
    onActiveTabChange,
    onAgentStatusesChange,
  } = options

  // Base WebSocket connection
  const ws = useWebSocket({
    projectId,
    token,
    autoReconnect,
    onStateChange: (state: WebSocketState) => {
      onConnectionChange?.(state === 'connected')
    },
  })

  // Event emitter (distributes messages to all hooks)
  const eventEmitter = useWebSocketEvents({
    ws: ws.ws,
  })

  // Message handling
  const messages = useWebSocketMessages({
    projectId,
    eventEmitter,
  })

  // Agent status tracking
  const status = useAgentStatus({
    eventEmitter,
  })

  // Activity tracking
  const activity = useActivityUpdates({
    eventEmitter,
  })

  // Kanban updates
  const kanban = useKanbanUpdates({
    eventEmitter,
    onKanbanChange: onKanbanDataChange,
    onTabChange: onActiveTabChange,
  })

  // Notify agent statuses changes
  useEffect(() => {
    onAgentStatusesChange?.(status.agentStatuses)
  }, [status.agentStatuses, onAgentStatusesChange])

  // Send message
  const sendMessage = useCallback((params: SendMessageParams): boolean => {
    if (!ws.isReady) {
      console.error('[useChatWebSocket] Cannot send - not connected')
      return false
    }

    // Add optimistic message with 'pending' status
    const tempId = messages.addOptimisticMessage(params.content)

    // Send via WebSocket
    const success = ws.send({
      type: 'message',
      content: params.content,
      author_type: params.author_type || 'user',
      agent_id: params.agent_id,
      agent_name: params.agent_name,
      temp_id: tempId,
    })

    // Update to 'sent' status after successful send
    if (success) {
      setTimeout(() => {
        messages.updateMessageStatus?.(tempId, 'sent')
      }, 100)
    }

    return success
  }, [ws.isReady, ws.send, messages])

  return {
    // Connection
    isConnected: ws.state === 'connected',
    isReady: ws.isReady,
    
    // Messages
    messages: messages.messages,
    
    // Agent status
    typingAgents: status.typingAgents,
    agentStatus: status.currentAgent,
    agentStatuses: status.agentStatuses,
    
    // Activity
    agentProgress: activity.agentProgress,
    toolCalls: activity.toolCalls,
    approvalRequests: activity.approvalRequests,
    
    // Kanban
    kanbanData: kanban.kanbanData,
    activeTab: kanban.activeTab,
    
    // Actions
    sendMessage,
    connect: ws.connect,
    disconnect: ws.disconnect,
  }
}

// Re-export types for convenience
export type { WebSocketState, AgentStatusMap, KanbanData }
