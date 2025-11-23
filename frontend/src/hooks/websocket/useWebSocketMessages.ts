/**
 * useWebSocketMessages - Message handling hook
 * 
 * Responsibilities:
 * - Parse and format messages
 * - Handle optimistic updates
 * - Message deduplication
 * - Manage message list state
 * 
 * Depends on: useWebSocket for connection
 */

import { useState, useCallback, useEffect, useRef } from 'react'
import { AuthorType, type Message } from '@/types/message'

export interface WebSocketMessageData {
  type: string
  data?: Message | any
  content?: string
  message_id?: string
  project_id?: string
  agent_name?: string
  agent_type?: string
  timestamp?: string
  created_at?: string
  metadata?: any
  message_metadata?: any
  structured_data?: any
  // Routing/delegation
  from_agent?: string
  to_agent?: string
  reason?: string
  context?: any
  // Activity updates
  is_new?: boolean
  updated_at?: string
}

export interface UseWebSocketMessagesOptions {
  /** Project ID */
  projectId?: string
  /** Callback when message received */
  onMessage?: (event: MessageEvent) => void
  /** WebSocket ref for sending pong responses */
  wsRef?: { current: WebSocket | null }
}

export interface UseWebSocketMessagesReturn {
  /** All messages */
  messages: Message[]
  /** Add message (optimistic) */
  addOptimisticMessage: (content: string) => string
  /** Update message status */
  updateMessageStatus: (messageId: string, status: 'sent' | 'delivered' | 'failed') => void
  /** Confirm optimistic message */
  confirmMessage: (tempId: string, serverMessage: Message) => void
  /** Remove stale temp messages */
  cleanupStaleMessages: () => void
  /** Clear all messages */
  clearMessages: () => void
}

/**
 * Format delegation message from Team Leader
 */
function formatDelegationMessage(data: WebSocketMessageData): string {
  const toAgent = data.to_agent || 'specialist'
  const taskDescription = data.reason || 'Xử lý yêu cầu'
  const context = data.context || {}
  const reasoning = context.reasoning || context.context || data.context || ''

  let message = `📋 **Đã giao nhiệm vụ cho @${toAgent}**\n\n`
  message += `**Nhiệm vụ:** ${taskDescription}`

  if (reasoning) {
    message += `\n\n**Lý do:** ${reasoning}`
  }

  return message
}

export function useWebSocketMessages(options: UseWebSocketMessagesOptions): UseWebSocketMessagesReturn {
  const { projectId, onMessage, wsRef } = options

  const [messages, setMessages] = useState<Message[]>([])
  const processedIdsRef = useRef(new Set<string>())

  // Add optimistic message
  const addOptimisticMessage = useCallback((content: string): string => {
    const tempId = `temp_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`

    const optimisticMessage: Message = {
      id: tempId,
      project_id: projectId || '',
      author_type: AuthorType.USER,
      content,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      status: 'pending', // Start with pending status
    }

    setMessages(prev => [...prev, optimisticMessage])
    return tempId
  }, [projectId])

  // Update message status (no replacement, just status change)
  const updateMessageStatus = useCallback((messageId: string, status: 'sent' | 'delivered' | 'failed') => {
    setMessages(prev => prev.map(m => 
      m.id === messageId ? { ...m, status } : m
    ))
  }, [])

  // Confirm optimistic message with server data (update ID and status)
  const confirmMessage = useCallback((tempId: string, serverMessage: Message) => {
    setMessages(prev => {
      const tempIndex = prev.findIndex(m => m.id === tempId)
      if (tempIndex === -1) return prev

      const newMessages = [...prev]
      // Update temp message with server ID and mark as delivered
      newMessages[tempIndex] = {
        ...newMessages[tempIndex],
        id: serverMessage.id,
        status: 'delivered',
        updated_at: serverMessage.updated_at,
      }
      return newMessages
    })
  }, [])

  // Cleanup stale temp messages (>10 seconds old)
  const cleanupStaleMessages = useCallback(() => {
    const now = Date.now()
    setMessages(prev => {
      const filtered = prev.filter(m => {
        if (!m.id.startsWith('temp_')) return true
        const msgTime = new Date(m.created_at).getTime()
        const isStale = now - msgTime > 10000 // 10 seconds
            return !isStale
      })
      return filtered.length === prev.length ? prev : filtered
    })
  }, [])

  // Clear all messages
  const clearMessages = useCallback(() => {
    setMessages([])
    processedIdsRef.current.clear()
  }, [])

  // Handle incoming WebSocket message
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const data: WebSocketMessageData = JSON.parse(event.data)

      // Handle different message types
      switch (data.type) {
        case 'message':
        case 'agent_message':
        case 'agent_response':
        case 'user_message': {
          let messageData: Message | null = null

          if (data.data) {
            // Format 1: Wrapped in data field
            messageData = data.data
          } else if (data.content && data.message_id) {
            // Format 2: Flat structure
            const messageType = data.structured_data?.message_type || 'text'
            const structuredData = data.structured_data?.data || data.structured_data

            messageData = {
              id: data.message_id,
              project_id: data.project_id || projectId || '',
              author_type: data.type === 'user_message' ? AuthorType.USER : AuthorType.AGENT,
              content: data.content,
              created_at: data.timestamp || data.created_at || new Date().toISOString(),
              updated_at: data.timestamp || new Date().toISOString(),
              agent_name: data.agent_name,
              message_type: messageType,
              structured_data: structuredData,
              metadata: data.metadata,
              message_metadata: {
                agent_name: data.agent_name,
                agent_type: data.agent_type,
              },
            }
          }

          if (messageData) {
            setMessages(prev => {
              // Check if already exists
              if (prev.some(m => m.id === messageData!.id)) {
                return prev
              }

              // Check if confirming optimistic message
              if (messageData!.author_type === AuthorType.USER) {
                const tempIndex = prev.findIndex(m =>
                  m.id.startsWith('temp_') && 
                  m.content === messageData!.content &&
                  m.author_type === messageData!.author_type
                )

                if (tempIndex !== -1) {
                  // Update temp message with server ID and status (no replacement)
                  const newMessages = [...prev]
                  newMessages[tempIndex] = {
                    ...newMessages[tempIndex],
                    id: messageData!.id,
                    status: 'delivered',
                    updated_at: messageData!.updated_at,
                  }
                  return newMessages
                }
              }

              // Add new message
              return [...prev, messageData!]
            })
          }
          break
        }

        case 'routing':
        case 'agent_routing': {
          // Create delegation message
          const delegationMessage: Message = {
            id: `delegation_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            project_id: projectId || '',
            author_type: AuthorType.AGENT,
            content: formatDelegationMessage(data),
            created_at: data.timestamp || new Date().toISOString(),
            updated_at: data.timestamp || new Date().toISOString(),
            agent_name: data.from_agent,
            message_type: 'delegation',
            message_metadata: {
              from_agent: data.from_agent,
              to_agent: data.to_agent,
              delegation_reason: data.reason,
              context: data.context,
            }
          }

          setMessages(prev => [...prev, delegationMessage])
          break
        }

        case 'ping': {
          // Respond to ping with pong to keep connection alive
          if (wsRef?.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'pong' }))
          }
          break
        }

        case 'pong': {
          // Pong received (if we send ping)
          break
        }

        case 'activity_update': {
          if (!data.message_id) break

          setMessages(prev => {
            const existingIndex = prev.findIndex(m => m.id === data.message_id)

            if (existingIndex !== -1) {
              // Update existing activity message
              return prev.map((msg, idx) =>
                idx === existingIndex
                  ? {
                      ...msg,
                      structured_data: data.structured_data,
                      content: data.content || msg.content,
                      updated_at: data.updated_at || new Date().toISOString()
                    }
                  : msg
              )
            } else {
              // Create new activity message
              const newMessage: Message = {
                id: data.message_id,
                project_id: data.project_id || projectId || '',
                author_type: AuthorType.AGENT,
                content: data.content || '',
                created_at: data.created_at || new Date().toISOString(),
                updated_at: data.updated_at || new Date().toISOString(),
                agent_name: data.agent_name,
                message_type: 'activity',
                structured_data: data.structured_data,
                message_metadata: { agent_name: data.agent_name }
              }
              return [...prev, newMessage]
            }
          })
          break
        }

        default:
          // Not a message type we handle
          break
      }

      // Forward to parent callback
      onMessage?.(event)
    } catch (error) {
      console.error('[useWebSocketMessages] Failed to parse message:', error)
    }
  }, [projectId, onMessage])

  // Auto-cleanup stale messages every 5 seconds
  useEffect(() => {
    const interval = setInterval(cleanupStaleMessages, 5000)
    return () => clearInterval(interval)
  }, [cleanupStaleMessages])

  return {
    messages,
    addOptimisticMessage,
    updateMessageStatus,
    confirmMessage,
    cleanupStaleMessages,
    clearMessages,
  }
}
