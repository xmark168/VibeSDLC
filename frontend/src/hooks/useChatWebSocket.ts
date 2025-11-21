import { useEffect, useRef, useState, useCallback } from 'react'
import { AuthorType, type Message } from '@/types/message'

export type WebSocketMessage = {
  type: 'connected' | 'message' | 'agent_message' | 'agent_response' | 'typing' | 'pong' | 'error' | 'routing' | 'agent_routing' | 'agent_thinking' | 'agent_question' | 'agent_preview' | 'kanban_update' | 'story_created' | 'story_updated' | 'story_status_changed' | 'switch_tab'
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
  // For agent_thinking messages
  content?: string
  structured_data?: any
  // For agent_question messages
  question_id?: string
  question_type?: 'text' | 'choice' | 'multiple_choice'
  question_text?: string
  question_number?: number
  total_questions?: number
  timeout?: number
  context?: string
  options?: string[]
  // For agent_preview messages
  preview_id?: string
  preview_type?: string
  title?: string
  brief?: any
  flows?: any
  backlog?: any
  sprint_plan?: any
  incomplete_flag?: boolean
  options?: string[]
  prompt?: string
  // Story events
  story_id?: string
  story_title?: string
  old_status?: string
  new_status?: string
  updated_fields?: string[]
  // Tab switching
  tab?: string
}

export type AgentPreview = {
  preview_id: string
  agent: string
  preview_type: string
  title: string
  brief?: any  // For Gatherer Agent (product_brief)
  vision?: any  // For Vision Agent (product_vision)
  backlog?: any  // For Backlog Agent (product_backlog)
  quality_score?: number  // For Vision Agent
  validation_result?: string  // For Vision Agent
  incomplete_flag: boolean
  options: string[]
  prompt: string
  receivedAt: number
}

export type SendMessageParams = {
  content: string
  author_type?: 'user' | 'agent'
}

export function useChatWebSocket(projectId: string | undefined, token: string | undefined) {
  const [isConnected, setIsConnected] = useState(false)
  const [isReady, setIsReady] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [typingAgents, setTypingAgents] = useState<Set<string>>(new Set())
  const [pendingQuestions, setPendingQuestions] = useState<any[]>([])
  const [pendingPreviews, setPendingPreviews] = useState<AgentPreview[]>([])
  const [agentStatus, setAgentStatus] = useState<{
    agentName: string | null
    status: 'idle' | 'thinking' | 'acting' | 'waiting' | 'error'
    currentAction?: string
    executionId?: string
  }>({
    agentName: null,
    status: 'idle'
  })
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
            console.log('[WebSocket] Received message:', data.type, data.data?.content?.substring(0, 100))
            if (data.data) {
              setMessages((prev) => {
                // Check if message already exists by ID
                const existsById = prev.some(m => m.id === data.data!.id)
                if (existsById) {
                  console.log('[WebSocket] Message already exists, skipping:', data.data!.id)
                  return prev
                }

                // Check if this is confirming an optimistic message (match by content for user messages)
                if (data.data!.author_type === AuthorType.USER || data.type === 'user_message') {
                  const tempIndex = prev.findIndex(m =>
                    m.id.startsWith('temp_') &&
                    m.content === data.data!.content
                  )

                  if (tempIndex !== -1) {
                    // Replace optimistic message with server-confirmed message
                    console.log('[WebSocket] Replacing optimistic message:', prev[tempIndex].id, '->', data.data!.id)
                    const newMessages = [...prev]
                    newMessages[tempIndex] = data.data!
                    return newMessages
                  }
                }

                console.log('[WebSocket] Adding new message:', data.data!.id)
                return [...prev, data.data!]
              })
            } else {
              console.warn('[WebSocket] Received message without data:', data)
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
            // Agent routing info - can be used for UI feedback
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

          case 'story_created':
          case 'story_updated':
          case 'story_status_changed':
            // Story events - kanban will auto-refresh via kanban_update
            break

          case 'agent_preview':
            if (data.preview_id && data.title) {
              setPendingPreviews(prev => [...prev, {
                preview_id: data.preview_id!,
                agent: data.agent || 'Agent',
                preview_type: data.preview_type || 'unknown',
                title: data.title,
                brief: data.brief,  // For Gatherer Agent
                vision: data.vision,  // For Vision Agent
                backlog: data.backlog,  // For Backlog Agent
                quality_score: data.quality_score,  // For Vision Agent
                validation_result: data.validation_result,  // For Vision Agent
                incomplete_flag: data.incomplete_flag || false,
                options: data.options || ['approve', 'edit', 'regenerate'],
                prompt: data.prompt || 'What would you like to do?',
                receivedAt: Date.now()
              }])
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
        temp_id: tempId, // Send temp_id for potential deduplication
      }))

      return true
    } catch (error) {
      console.error('Failed to send message:', error)
      return false
    }
  }, [projectId])

  const submitAnswer = useCallback((question_id: string, answer: string) => {
    console.log('[submitAnswer] Called with:', { question_id, answer })
    console.log('[submitAnswer] WebSocket state:', wsRef.current?.readyState)

    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.error('[submitAnswer] WebSocket is not connected')
      return false
    }

    try {
      const message = {
        type: 'user_answer',
        question_id: question_id,
        answer: answer,
      }
      console.log('[submitAnswer] Sending message:', message)

      wsRef.current.send(JSON.stringify(message))

      // Remove question from pending queue
      setPendingQuestions(prev => prev.filter(q => q.question_id !== question_id))

      console.log('[submitAnswer] ✓ Answer submitted successfully for question:', question_id)
      return true
    } catch (error) {
      console.error('[submitAnswer] ✗ Failed to submit answer:', error)
      return false
    }
  }, [])

  const submitPreviewChoice = useCallback((preview_id: string, choice: string, edit_changes?: string) => {
    if (!isWsReady()) {
      console.error('WebSocket is not connected')
      return false
    }

    try {
      wsRef.current!.send(JSON.stringify({
        type: 'user_answer',
        question_id: preview_id,
        answer: edit_changes ? { choice, edit_changes } : choice,
      }))
      setPendingPreviews(prev => prev.filter(p => p.preview_id !== preview_id))
      return true
    } catch (error) {
      console.error('Failed to submit choice:', error)
      return false
    }
  }, [isWsReady])

  const ping = useCallback(() => {
    if (isWsReady()) {
      wsRef.current!.send(JSON.stringify({ type: 'ping' }))
    }
  }, [isWsReady])

  const reopenPreview = useCallback((preview: AgentPreview) => {
    setPendingPreviews(prev => [...prev, preview])
  }, [])

  const closePreview = useCallback(() => {
    setPendingPreviews(prev => prev.slice(1))
  }, [])

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

  return {
    isConnected,
    isReady,
    messages,
    typingAgents: Array.from(typingAgents),
    agentStatus,
    pendingQuestions,
    pendingPreviews,
    kanbanData,
    activeTab,
    sendMessage,
    submitPreviewChoice,
    reopenPreview,
    closePreview,
    connect,
    disconnect,
  }
}
