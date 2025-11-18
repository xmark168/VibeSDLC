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
  // For routing messages
  agent_selected?: string
  confidence?: number
  user_intent?: string
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
  incomplete_flag?: boolean
  prompt?: string
  // For story events
  story_id?: string
  story_title?: string
  old_status?: string
  new_status?: string
  updated_fields?: string[]
  // For switch_tab messages
  tab?: string
}

export type AgentQuestion = {
  question_id: string
  agent: string
  question_type: 'text' | 'choice' | 'multiple_choice'
  question_text: string
  question_number: number
  total_questions: number
  timeout: number
  context?: string
  options?: string[]
  receivedAt: number // timestamp
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
  const [pendingQuestions, setPendingQuestions] = useState<AgentQuestion[]>([])
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
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>()
  const reconnectAttemptsRef = useRef(0)
  const maxReconnectAttempts = 5

  const connect = useCallback(() => {
    if (!projectId || !token) return

    // Close existing connection
    if (wsRef.current) {
      wsRef.current.close()
    }

    // Determine WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = import.meta.env.VITE_API_URL?.replace(/^https?:\/\//, '') || 'localhost:8000'
    const wsUrl = `${protocol}//${host}/api/v1/chat/ws?project_id=${projectId}&token=${token}`

    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      console.log('WebSocket connected')
      setIsConnected(true)
      reconnectAttemptsRef.current = 0

      // Double check readyState and set isReady
      if (ws.readyState === WebSocket.OPEN) {
        setIsReady(true)
      }
    }

    ws.onmessage = (event) => {
      try {
        const data: WebSocketMessage = JSON.parse(event.data)

        switch (data.type) {
          case 'connected':
            console.log('Connected to chat:', data.message)
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
                if (data.is_typing) {
                  newSet.add(data.agent_name!)
                } else {
                  newSet.delete(data.agent_name!)
                }
                return newSet
              })
            }
            break

          case 'routing':
          case 'agent_routing':
            console.log('Agent routing:', data.agent_selected || data.agent_type, 'confidence:', data.confidence)
            break

          case 'agent_thinking':
            console.log('Agent thinking:', data.content?.substring(0, 100))
            // Could display this in UI as streaming text
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
            // Update kanban board data
            console.log('Kanban update received:', data.data)
            if (data.data) {
              setKanbanData(data.data)
            }
            break

          case 'switch_tab':
            // Auto-switch to specified tab
            console.log('Switch tab request:', data.tab)
            if (data.tab) {
              setActiveTab(data.tab)
            }
            break

          case 'story_created':
            console.log('Story created:', data.story_id, data.story_title)
            // Could trigger Kanban board refresh or optimistic update
            break

          case 'story_updated':
            console.log('Story updated:', data.story_id, 'fields:', data.updated_fields)
            // Could trigger Kanban board refresh or optimistic update
            break

          case 'story_status_changed':
            console.log('Story status changed:', data.story_id, data.old_status, '->', data.new_status)
            // Could trigger Kanban board refresh or optimistic update
            break

          case 'agent_question':
            // Agent asking user a question
            if (data.question_id && data.question_text) {
              const question: AgentQuestion = {
                question_id: data.question_id,
                agent: data.agent || 'Agent',
                question_type: data.question_type || 'text',
                question_text: data.question_text,
                question_number: data.question_number || 1,
                total_questions: data.total_questions || 1,
                timeout: data.timeout || 600,
                context: data.context,
                options: data.options,
                receivedAt: Date.now()
              }

              setPendingQuestions(prev => [...prev, question])
              console.log('Agent question received:', question.question_text.substring(0, 100))
            }
            break

          case 'agent_preview':
            // Agent showing preview for approval
            if (data.preview_id && data.title) {
              const preview: AgentPreview = {
                preview_id: data.preview_id,
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
              }

              setPendingPreviews(prev => [...prev, preview])
              console.log('Agent preview received:', preview.title)
            }
            break

          case 'pong':
            // Handle ping/pong for keep-alive
            break

          case 'error':
            console.error('WebSocket error:', data.message)
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
      console.log('WebSocket disconnected')
      setIsConnected(false)
      setIsReady(false)
      wsRef.current = null

      // Attempt to reconnect
      if (reconnectAttemptsRef.current < maxReconnectAttempts) {
        reconnectAttemptsRef.current++
        const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000)
        console.log(`Reconnecting in ${delay}ms... (attempt ${reconnectAttemptsRef.current})`)

        reconnectTimeoutRef.current = setTimeout(() => {
          connect()
        }, delay)
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
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
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
    console.log('[submitPreviewChoice] ===== SUBMITTING PREVIEW CHOICE =====')
    console.log('[submitPreviewChoice] preview_id:', preview_id)
    console.log('[submitPreviewChoice] choice:', choice)
    console.log('[submitPreviewChoice] edit_changes:', edit_changes)
    console.log('[submitPreviewChoice] WebSocket state:', wsRef.current?.readyState)

    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.error('[submitPreviewChoice] WebSocket is not connected')
      return false
    }

    try {
      const message: any = {
        type: 'user_answer',
        question_id: preview_id,
        answer: edit_changes ? { choice, edit_changes } : choice,
      }
      console.log('[submitPreviewChoice] Sending message:', message)

      wsRef.current.send(JSON.stringify(message))

      // Remove preview from pending queue
      setPendingPreviews(prev => prev.filter(p => p.preview_id !== preview_id))

      console.log('[submitPreviewChoice] ✓ Choice submitted successfully for preview:', preview_id)
      return true
    } catch (error) {
      console.error('[submitPreviewChoice] ✗ Failed to submit choice:', error)
      return false
    }
  }, [])

  const ping = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'ping' }))
    }
  }, [])

  // Connect on mount and when dependencies change
  useEffect(() => {
    connect()
    return () => {
      disconnect()
    }
  }, [connect, disconnect])

  // Ping every 30 seconds to keep connection alive
  useEffect(() => {
    if (!isConnected) return

    const interval = setInterval(() => {
      ping()
    }, 30000)

    return () => clearInterval(interval)
  }, [isConnected, ping])

  // Polling mechanism to sync isReady with actual WebSocket readyState
  useEffect(() => {
    const checkReadyState = () => {
      if (wsRef.current) {
        const actuallyReady = wsRef.current.readyState === WebSocket.OPEN
        setIsReady(actuallyReady)
      } else {
        setIsReady(false)
      }
    }

    // Check immediately and then every 100ms
    checkReadyState()
    const interval = setInterval(checkReadyState, 100)

    return () => clearInterval(interval)
  }, [isConnected])

  // Function to programmatically open preview (for edit functionality)
  const reopenPreview = useCallback((preview: AgentPreview) => {
    setPendingPreviews(prev => [...prev, preview])
  }, [])

  // Function to close current preview (remove from queue)
  const closePreview = useCallback(() => {
    setPendingPreviews(prev => prev.slice(1)) // Remove first preview
  }, [])

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
    submitAnswer,
    submitPreviewChoice,
    reopenPreview,
    closePreview,
    connect,
    disconnect,
  }
}
