/**
 * Chat WebSocket Hook using react-use-websocket
 * 
 * Simple, stable WebSocket connection for chat using battle-tested library
 */

import { useEffect, useRef, useState } from 'react'
import useWebSocket, { ReadyState } from 'react-use-websocket'
import { AuthorType, Message } from '@/types/message'

// ============================================================================
// Types
// ============================================================================

export type AgentStatusType = 'idle' | 'thinking' | 'acting' | 'waiting' | 'error'

export interface AgentStatus {
  status: AgentStatusType
  agentName?: string
  currentAction?: string
}

export interface UseChatWebSocketReturn {
  // Connection state
  isConnected: boolean
  readyState: ReadyState
  
  // Messages
  messages: Message[]
  
  // Agent status
  agentStatus: AgentStatus
  
  // Actions
  sendMessage: (content: string, agentName?: string) => void
}

// ============================================================================
// Helper Functions
// ============================================================================

function getWebSocketUrl(projectId: string, token: string): string {
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.hostname
  const port = import.meta.env.DEV ? '8000' : window.location.port
  const portStr = port ? `:${port}` : ''
  
  // Backend route: /api/v1/chat/ws (API prefix + router prefix + websocket path)
  return `${wsProtocol}//${host}${portStr}/api/v1/chat/ws?project_id=${projectId}&token=${token}`
}

function createOptimisticMessage(content: string, projectId: string): Message {
  const tempId = `temp_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  return {
    id: tempId,
    project_id: projectId,
    author_type: AuthorType.USER,
    content,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    status: 'pending',
  }
}

// ============================================================================
// Hook
// ============================================================================

export function useChatWebSocket(
  projectId: string | null,
  token: string | undefined
): UseChatWebSocketReturn {
  // State
  const [messages, setMessages] = useState<Message[]>([])
  const [agentStatus, setAgentStatus] = useState<AgentStatus>({ status: 'idle' })
  
  // Refs
  const projectIdRef = useRef(projectId)
  
  useEffect(() => {
    projectIdRef.current = projectId
  }, [projectId])

  // WebSocket URL
  const socketUrl = projectId && token ? getWebSocketUrl(projectId, token) : null

  // react-use-websocket hook
  const { sendJsonMessage, lastJsonMessage, readyState } = useWebSocket(
    socketUrl,
    {
      // Reconnection configuration
      shouldReconnect: (closeEvent) => {
        // Don't reconnect if explicitly closed (code 1000) or auth failed (1008)
        if (closeEvent.code === 1000 || closeEvent.code === 1008) {
          console.log('[WebSocket] Clean close or auth failed - not reconnecting')
          return false
        }
        return true
      },
      reconnectAttempts: 10,
      reconnectInterval: (attemptNumber) => 
        Math.min(1000 * Math.pow(2, attemptNumber), 30000),
      
      // Connection options
      share: false, // Don't share connection across components
      retryOnError: true,
      
      // Callbacks
      onOpen: () => {
        console.log('[WebSocket] ✅ Connected successfully')
      },
      onClose: (event) => {
        console.log('[WebSocket] ❌ Disconnected - Code:', event.code, 'Reason:', event.reason)
      },
      onError: (event) => {
        console.error('[WebSocket] ⚠️ Error:', event)
      },
      onReconnectStop: (numAttempts) => {
        console.error('[WebSocket] ⛔ Failed to reconnect after', numAttempts, 'attempts')
      },
    },
    !!socketUrl // Only connect when URL is available
  )

  // Handle incoming messages
  useEffect(() => {
    if (!lastJsonMessage) return

    const data = lastJsonMessage as any
    
    // Validate message structure
    if (!data || typeof data !== 'object') {
      console.warn('[WebSocket] Invalid message format:', data)
      return
    }

    const messageType = data.type
    if (!messageType) {
      console.warn('[WebSocket] Message missing type field:', data)
      return
    }

    console.log('[WebSocket] 📨 Received:', messageType, data)

    switch (messageType) {
      case 'connected':
        console.log('[WebSocket] Connection confirmed by server')
        break

      case 'user_message':
      case 'agent_message': {
        const message: Message = {
          id: data.message_id,
          project_id: data.project_id || projectIdRef.current || '',
          author_type: data.author_type === 'user' ? AuthorType.USER : AuthorType.AGENT,
          content: data.content,
          created_at: data.created_at || data.timestamp || new Date().toISOString(),
          updated_at: data.updated_at || data.timestamp || new Date().toISOString(),
          agent_name: data.agent_name,
          message_type: data.message_type || 'text',
          structured_data: data.structured_data,
          message_metadata: data.message_metadata,
        }

        setMessages((prev) => {
          // Check if already exists
          if (prev.some((m) => m.id === message.id)) {
            return prev
          }

          // Check if confirming optimistic message
          if (message.author_type === AuthorType.USER) {
            const tempIndex = prev.findIndex(
              (m) =>
                m.id.startsWith('temp_') &&
                m.content === message.content &&
                m.author_type === message.author_type
            )

            if (tempIndex !== -1) {
              // Replace temp message with real one
              const newMessages = [...prev]
              newMessages[tempIndex] = { ...message, status: 'delivered' }
              return newMessages
            }
          }

          // Add new message
          return [...prev, message]
        })
        break
      }

      case 'agent_status': {
        // Map backend status to frontend status types
        const statusMap: Record<string, AgentStatusType> = {
          'idle': 'idle',
          'thinking': 'thinking',
          'working': 'acting',
          'completed': 'idle',
          'error': 'error',
        }
        
        const mappedStatus = statusMap[data.status] || 'idle'
        
        setAgentStatus({
          status: mappedStatus,
          agentName: data.agent_name,
          currentAction: data.current_action,
        })
        break
      }

      case 'agent_progress': {
        // Agent progress updates (e.g., "Understanding user requirements")
        // These are intermediate status updates, not full messages
        console.log('[WebSocket] 🔄 Agent progress:', data.agent_name, '-', data.content)
        
        // Update agent status with progress info
        setAgentStatus({
          status: 'acting',
          agentName: data.agent_name,
          currentAction: data.content,
        })
        break
      }

      case 'activity_update': {
        // Activity updates can have or not have message_id
        // If no message_id, it's a summary/status update
        if (!data.message_id) {
          console.log('[WebSocket] 📊 Activity:', data.agent_name, '-', data.content)
          
          // If has structured_data with events, create a summary message
          if (data.structured_data?.events && Array.isArray(data.structured_data.events)) {
            const summaryMessage: Message = {
              id: `activity_${data.execution_id || Date.now()}`,
              project_id: data.project_id || projectIdRef.current || '',
              author_type: AuthorType.AGENT,
              content: data.content || 'Activity completed',
              created_at: data.timestamp || new Date().toISOString(),
              updated_at: data.timestamp || new Date().toISOString(),
              agent_name: data.agent_name,
              message_type: 'activity',
              structured_data: data.structured_data,
              message_metadata: { 
                agent_name: data.agent_name,
                execution_id: data.execution_id,
              },
            }
            
            // Add as new message (avoid duplicates)
            setMessages((prev) => {
              if (prev.some(m => m.id === summaryMessage.id)) {
                return prev
              }
              return [...prev, summaryMessage]
            })
          }
          
          // Update agent status from structured_data if available
          if (data.structured_data?.status) {
            const statusMap: Record<string, AgentStatusType> = {
              'idle': 'idle',
              'thinking': 'thinking',
              'working': 'acting',
              'running': 'acting',
              'completed': 'idle',
              'success': 'idle',
              'failed': 'error',
              'error': 'error',
            }
            
            const mappedStatus = statusMap[data.structured_data.status] || 'acting'
            
            setAgentStatus({
              status: mappedStatus,
              agentName: data.agent_name,
              currentAction: data.content,
            })
          } else {
            // Just update current action
            setAgentStatus((prev) => ({
              ...prev,
              agentName: data.agent_name,
              currentAction: data.content,
            }))
          }
          
          break
        }

        // If has message_id, create or update message
        setMessages((prev) => {
          const existingIndex = prev.findIndex((m) => m.id === data.message_id)

          if (existingIndex !== -1) {
            // Update existing
            return prev.map((msg, idx) =>
              idx === existingIndex
                ? {
                    ...msg,
                    structured_data: data.structured_data,
                    content: data.content || msg.content,
                    updated_at: new Date().toISOString(),
                  }
                : msg
            )
          } else {
            // Create new activity message
            const newMessage: Message = {
              id: data.message_id,
              project_id: data.project_id || projectIdRef.current || '',
              author_type: AuthorType.AGENT,
              content: data.content || '',
              created_at: data.created_at || new Date().toISOString(),
              updated_at: new Date().toISOString(),
              agent_name: data.agent_name,
              message_type: 'activity',
              structured_data: data.structured_data,
              message_metadata: { agent_name: data.agent_name },
            }
            return [...prev, newMessage]
          }
        })
        break
      }

      case 'execution_started': {
        // Agent execution has started
        console.log('[WebSocket] 🚀 Execution started:', data.agent_name, 'ID:', data.execution_id)
        setAgentStatus({
          status: 'acting',
          agentName: data.agent_name,
          currentAction: 'Starting execution',
        })
        break
      }

      case 'execution_completed': {
        // Agent execution completed
        console.log('[WebSocket] ✅ Execution completed:', data.agent_name)
        setAgentStatus({
          status: 'idle',
          agentName: data.agent_name,
          currentAction: 'Completed',
        })
        break
      }

      case 'execution_failed': {
        // Agent execution failed
        console.error('[WebSocket] ❌ Execution failed:', data.agent_name, data.error)
        setAgentStatus({
          status: 'error',
          agentName: data.agent_name,
          currentAction: `Failed: ${data.error || 'Unknown error'}`,
        })
        break
      }

      case 'error':
        console.error('[WebSocket] ⚠️ Server error:', data.message)
        break

      default:
        console.log('[WebSocket] ⚡ Unhandled message type:', messageType, data)
    }
  }, [lastJsonMessage])

  // Send message function
  const sendMessage = (content: string, agentName?: string) => {
    if (!projectId) {
      console.error('[WebSocket] ❌ Cannot send message: no project ID')
      return
    }

    if (readyState !== ReadyState.OPEN) {
      console.warn('[WebSocket] ⚠️ Cannot send message: connection state =', 
        ReadyState[readyState])
      return
    }

    if (!content || !content.trim()) {
      console.warn('[WebSocket] ⚠️ Cannot send empty message')
      return
    }

    try {
      // Add optimistic message
      const optimisticMsg = createOptimisticMessage(content, projectId)
      setMessages((prev) => [...prev, optimisticMsg])

      // Send to server (backend expects "message" type, not "chat_message")
      sendJsonMessage({
        type: 'message',
        content: content.trim(),
        agent_name: agentName,
        project_id: projectId,
      })
      
      console.log('[WebSocket] 📤 Sent message:', content.substring(0, 50) + '...')
    } catch (error) {
      console.error('[WebSocket] ❌ Failed to send message:', error)
    }
  }

  // Connection status
  const isConnected = readyState === ReadyState.OPEN

  return {
    isConnected,
    readyState,
    messages,
    agentStatus,
    sendMessage,
  }
}
