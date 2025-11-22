import { useEffect, useRef, useState, useCallback } from 'react'
import { AuthorType, type Message } from '@/types/message'

// Track processed message IDs to prevent duplicates
const processedMessageIds = new Set<string>()

export type WebSocketMessage = {
  type: 'connected' | 'message' | 'agent_message' | 'agent_response' | 'typing' | 'pong' | 'error' | 'routing' | 'agent_routing' | 'agent_step' | 'agent_thinking' | 'tool_call' | 'kanban_update' | 'story_created' | 'story_updated' | 'story_status_changed' | 'scrum_master_step' | 'switch_tab' | 'agent_status' | 'agent_progress' | 'approval_request' | 'activity_update'
  data?: Message | any
  agent_name?: string
  agent_type?: string
  is_typing?: boolean
  message?: string
  project_id?: string
  // Routing
  agent_selected?: string
  confidence?: number
  reasoning?: string
  context?: any  // Full delegation context from Team Leader
  // For agent_thinking messages
  content?: string
  structured_data?: any
  message_id?: string
  timestamp?: string
  updated_at?: string  // For activity updates
  // Tool call
  tool?: string
  display_name?: string
  tool_name?: string
  parameters?: any
  result?: any
  error_message?: string
  status?: string
  // Story events
  story_id?: string
  story_title?: string
  old_status?: string
  new_status?: string
  updated_fields?: string[]
  // Tab switching
  tab?: string
  // Agent progress
  step_number?: number
  total_steps?: number
  description?: string
  // Approval request
  approval_request_id?: string
  request_type?: string
  proposed_data?: any
  preview_data?: any
  explanation?: string
}

export type SendMessageParams = {
  content: string
  author_type?: 'user' | 'agent'
  agent_id?: string  // ID of mentioned agent for routing
  agent_name?: string  // Name of mentioned agent for display
}

/**
 * Format delegation message from Team Leader to specialist agent
 */
function formatDelegationMessage(data: any): string {
  const toAgent = data.to_agent || 'specialist'
  const taskDescription = data.reason || 'Xử lý yêu cầu'

  // Extract detailed context if available
  const context = data.context || {}
  const reasoning = context.reasoning || context.context || data.reasoning || ''

  let message = `📋 **Đã giao nhiệm vụ cho @${toAgent}**\n\n`
  message += `**Nhiệm vụ:** ${taskDescription}`

  if (reasoning) {
    message += `\n\n**Lý do:** ${reasoning}`
  }

  return message
}

export function useChatWebSocket(projectId: string | undefined, token: string | undefined) {
  const [isConnected, setIsConnected] = useState(false)
  const [isReady, setIsReady] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [typingAgents, setTypingAgents] = useState<Set<string>>(new Set())
  const [agentProgress, setAgentProgress] = useState<{
    isExecuting: boolean
    currentStep?: string
    currentAgent?: string
    currentTool?: string
    stepNumber?: number
    totalSteps?: number
  }>({ isExecuting: false })
  const [agentStatus, setAgentStatus] = useState<{
    agentName: string | null
    status: 'idle' | 'thinking' | 'acting' | 'waiting' | 'error'
    currentAction?: string
    executionId?: string
  }>({ agentName: null, status: 'idle' })
  const [approvalRequests, setApprovalRequests] = useState<any[]>([])
  const [toolCalls, setToolCalls] = useState<any[]>([])
  const [kanbanData, setKanbanData] = useState<{
    sprints: any[]
    kanban_board: {
      Backlog: any[]
      Todo: any[]
      Doing: any[]
      Done: any[]
    }
    total_items: number
    timestamp?: string
  } | null>(null)
  const [activeTab, setActiveTab] = useState<string | null>(null)

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | undefined>(undefined)
  const reconnectAttemptsRef = useRef(0)
  const maxReconnectAttempts = 5

  // Helper to check if WebSocket is ready
  const isWsReady = useCallback(() => {
    return wsRef.current?.readyState === WebSocket.OPEN
  }, [])

  const connect = useCallback(() => {
    if (!projectId || !token) return

    if (wsRef.current) {
      wsRef.current.close()
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = import.meta.env.VITE_API_URL?.replace(/^https?:\/\//, '') || 'localhost:8000'
    const wsUrl = `${protocol}//${host}/api/v1/chat/ws?project_id=${projectId}&token=${token}`

    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      setIsConnected(true)
      setIsReady(true)
      reconnectAttemptsRef.current = 0
    }

    ws.onmessage = (event) => {
      try {
        const data: WebSocketMessage = JSON.parse(event.data)

        switch (data.type) {
          case 'connected':
            break

          case 'message':
          case 'agent_message':
          case 'agent_response':
          case 'user_message':
            console.log('[WebSocket] Received message:', data.type, data.data?.content?.substring(0, 100) || data.content?.substring(0, 100))

            // Handle both formats: with data field or flat structure
            let messageData: Message | null = null

            if (data.data) {
              // Format 1: Message wrapped in data field
              messageData = data.data
            } else if (data.content && data.message_id) {
              // Format 2: Flat structure from backend
              // Extract message_type from structured_data or default to 'text'
              const messageType = data.structured_data?.message_type || 'text'
              const structuredData = data.structured_data?.data || data.structured_data

              messageData = {
                id: data.message_id,
                project_id: data.project_id || projectId || '',
                author_type: data.type === 'user_message' ? AuthorType.USER : AuthorType.AGENT,
                content: data.content,
                created_at: data.timestamp || new Date().toISOString(),
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
              setMessages((prev) => {
                // Check if message already exists by ID
                const existsById = prev.some(m => m.id === messageData!.id)
                if (existsById) {
                  console.log('[WebSocket] Message already exists, skipping:', messageData!.id)
                  return prev
                }

                // Check if this is confirming an optimistic message (match by content for user messages)
                if (messageData!.author_type === AuthorType.USER || data.type === 'user_message') {
                  const tempIndex = prev.findIndex(m =>
                    m.id.startsWith('temp_') &&
                    m.content === messageData!.content
                  )

                  if (tempIndex !== -1) {
                    // Replace optimistic message with server-confirmed message
                    console.log('[WebSocket] Replacing optimistic message:', prev[tempIndex].id, '->', messageData!.id)
                    const newMessages = [...prev]
                    newMessages[tempIndex] = messageData!
                    return newMessages
                  }
                }

                console.log('[WebSocket] Adding new message:', messageData!.id)
                return [...prev, messageData!]
              })
            } else {
              console.warn('[WebSocket] Received message without valid data:', data)
            }
            break

          case 'typing':
            if (data.agent_name) {
              setTypingAgents((prev) => {
                const newSet = new Set(prev)
                data.is_typing ? newSet.add(data.agent_name!) : newSet.delete(data.agent_name!)
                return newSet
              })
            }
            break

          case 'routing':
          case 'agent_routing':
            console.log('[WebSocket] Agent routing:', data.from_agent, '→', data.to_agent)

            // Create delegation message from Team Leader
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

          case 'agent_thinking':
            // Could display as streaming text
            break

          case 'agent_status':
            console.log('[WebSocket] Agent status:', data.status, data.agent_name)
            // Normalize status: "agent.thinking" -> "thinking"
            const normalizedStatus = (data.status || 'idle').replace('agent.', '') as 'idle' | 'thinking' | 'acting' | 'waiting' | 'error'
            setAgentStatus({
              agentName: data.agent_name || null,
              status: normalizedStatus,
              currentAction: data.current_action,
              executionId: data.execution_id,
            })
            break

          case 'kanban_update':
            if (data.data) {
              setKanbanData(data.data)
            }
            break

          case 'switch_tab':
            if (data.tab) {
              setActiveTab(data.tab)
            }
            break

          case 'agent_progress':
            console.log('[WebSocket] Agent progress:', data)
            setAgentProgress({
              isExecuting: data.status === 'in_progress',
              currentStep: data.description,
              currentAgent: data.agent_name,
              stepNumber: data.step_number,
              totalSteps: data.total_steps,
            })
            break

          case 'tool_call':
            console.log('[WebSocket] Tool call:', data.tool_name, data.status)
            setToolCalls(prev => [...prev, {
              agent_name: data.agent_name,
              tool_name: data.tool_name,
              display_name: data.display_name,
              status: data.status,
              timestamp: data.timestamp,
              parameters: data.parameters,
              result: data.result,
              error_message: data.error_message,
            }])

            // Also update agentProgress to show tool being used
            if (data.status === 'started') {
              setAgentProgress(prev => ({
                ...prev,
                currentTool: data.display_name || data.tool_name,
              }))
            }
            break

          case 'approval_request':
            console.log('[WebSocket] Approval request:', data.request_type)
            setApprovalRequests(prev => [...prev, {
              id: data.approval_request_id,
              request_type: data.request_type,
              agent_name: data.agent_name,
              proposed_data: data.proposed_data,
              preview_data: data.preview_data,
              explanation: data.explanation,
              timestamp: data.timestamp,
            }])
            break

          case 'story_created':
          case 'story_updated':
          case 'story_status_changed':
            // Story events - kanban will auto-refresh via kanban_update
            break

          case 'activity_update':
            console.log('[WebSocket] Activity update:', data.message_id)
            // Update existing activity message
            if (data.message_id) {
              setMessages((prev) => prev.map(msg =>
                msg.id === data.message_id
                  ? {
                      ...msg,
                      structured_data: data.structured_data,
                      content: data.content || msg.content,
                      updated_at: data.updated_at || new Date().toISOString()
                    }
                  : msg
              ))
            }
            break

          case 'pong':
          case 'error':
            if (data.type === 'error') {
              console.error('WebSocket error:', data.message)
            }
            break
        }
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error)
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    ws.onclose = () => {
      setIsConnected(false)
      setIsReady(false)
      wsRef.current = null

      if (reconnectAttemptsRef.current < maxReconnectAttempts) {
        reconnectAttemptsRef.current++
        const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000)
        reconnectTimeoutRef.current = setTimeout(connect, delay)
      }
    }
  }, [projectId, token])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    // Clear processed message tracking on disconnect
    processedMessageIds.clear()
    setIsConnected(false)
    setIsReady(false)
  }, [])

  const sendMessage = useCallback((params: SendMessageParams) => {
    if (!isWsReady()) {
      console.error('WebSocket is not connected')
      return false
    }

    try {
      // Generate temporary ID for optimistic update
      const tempId = `temp_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`

      // Create optimistic message
      const optimisticMessage: Message = {
        id: tempId,
        project_id: projectId || '',
        author_type: AuthorType.USER,
        content: params.content,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }

      // Add to local state immediately (optimistic update)
      setMessages(prev => [...prev, optimisticMessage])

      // Send via WebSocket
      wsRef.current.send(JSON.stringify({
        type: 'message',
        content: params.content,
        author_type: params.author_type || 'user',
        agent_id: params.agent_id,  // Include agent_id for routing
        agent_name: params.agent_name,  // Include agent_name for display
        temp_id: tempId, // Send temp_id for potential deduplication
      }))

      return true
    } catch (error) {
      console.error('Failed to send message:', error)
      return false
    }
  }, [isWsReady, projectId])

  const ping = useCallback(() => {
    if (isWsReady()) {
      wsRef.current!.send(JSON.stringify({ type: 'ping' }))
    }
  }, [isWsReady])

  // Connect on mount
  useEffect(() => {
    connect()
    return () => disconnect()
  }, [connect, disconnect])

  // Keep-alive ping every 30 seconds
  useEffect(() => {
    if (!isConnected) return
    const interval = setInterval(ping, 30000)
    return () => clearInterval(interval)
  }, [isConnected, ping])

  // Clean up stale temp messages (older than 10 seconds without server confirmation)
  useEffect(() => {
    const cleanup = setInterval(() => {
      const now = Date.now()
      setMessages(prev => {
        const filtered = prev.filter(m => {
          if (!m.id.startsWith('temp_')) return true
          const msgTime = new Date(m.created_at).getTime()
          const isStale = now - msgTime > 10000 // 10 seconds
          if (isStale) {
            console.log('[WebSocket] Removing stale temp message:', m.id)
          }
          return !isStale
        })
        return filtered.length === prev.length ? prev : filtered
      })
    }, 5000) // Check every 5 seconds

    return () => clearInterval(cleanup)
  }, [])

  return {
    isConnected,
    isReady,
    messages,
    typingAgents: Array.from(typingAgents),
    agentProgress,
    agentStatus,
    approvalRequests,
    toolCalls,
    kanbanData,
    activeTab,
    sendMessage,
    connect,
    disconnect,
  }
}
