/**
 * useWebSocketMessages - Message handling hook
 * 
 * Responsibilities:
 * - Parse and format messages
 * - Handle optimistic updates
 * - Message deduplication
 * - Manage message list state
 * 
 * Now uses event emitter pattern for better separation
 */

import { useState, useCallback, useEffect } from 'react'
import { AuthorType, type Message } from '@/types/message'

export interface UseWebSocketMessagesOptions {
  /** Project ID */
  projectId?: string
  /** Event emitter from useWebSocketEvents */
  eventEmitter?: {
    on: (eventType: string, handler: (data: any) => void) => () => void
  }
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
  const { projectId, eventEmitter } = options

  const [messages, setMessages] = useState<Message[]>([])

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

  // Subscribe to WebSocket events
  useEffect(() => {
    if (!eventEmitter) return

    const unsubscribers: Array<() => void> = []

    // Handle message events
    const handleMessageEvent = (data: any) => {
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
    }

    // Handle routing events
    const handleRoutingEvent = (data: any) => {
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
    }

    // Handle activity updates
    const handleActivityUpdate = (data: any) => {
      if (!data.message_id) return
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
    }

    // Subscribe to events
    unsubscribers.push(eventEmitter.on('message', handleMessageEvent))
    unsubscribers.push(eventEmitter.on('agent_message', handleMessageEvent))
    unsubscribers.push(eventEmitter.on('agent_response', handleMessageEvent))
    unsubscribers.push(eventEmitter.on('user_message', handleMessageEvent))
    unsubscribers.push(eventEmitter.on('routing', handleRoutingEvent))
    unsubscribers.push(eventEmitter.on('agent_routing', handleRoutingEvent))
    unsubscribers.push(eventEmitter.on('activity_update', handleActivityUpdate))

    // Cleanup
    return () => {
      unsubscribers.forEach(unsubscribe => unsubscribe())
    }
  }, [eventEmitter, projectId])

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
