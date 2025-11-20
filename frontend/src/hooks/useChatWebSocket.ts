import { useEffect, useRef, useState, useCallback } from 'react'
import { AuthorType, type Message } from '@/types/message'

export type WebSocketMessage = {
  type: 'connected' | 'message' | 'agent_message' | 'agent_response' | 'typing' | 'pong' | 'error' | 'routing' | 'agent_routing' | 'agent_step' | 'agent_thinking' | 'tool_call' | 'agent_preview' | 'kanban_update' | 'story_created' | 'story_updated' | 'story_status_changed' | 'scrum_master_step' | 'switch_tab'
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
  // Agent step
  step?: string
  agent?: string
  node?: string
  step_number?: number
  // Content
  content?: string
  structured_data?: any
  message_id?: string
  timestamp?: string
  // Tool call
  tool?: string
  display_name?: string
  // Preview (BA agent: brief, flows, backlog)
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
  brief?: any
  flows?: any
  backlog?: any
  sprint_plan?: any
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
  const [pendingPreviews, setPendingPreviews] = useState<AgentPreview[]>([])
  const [agentProgress, setAgentProgress] = useState<{
    isExecuting: boolean
    currentStep?: string
    currentAgent?: string
    currentTool?: string
    stepNumber?: number
  }>({ isExecuting: false })
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
            {
              // Handle both formats:
              // 1. Message with data field: { type: 'message', data: {...} }
              // 2. Agent message from kafka_bridge: { type: 'agent_message', content: ..., message_id: ... }
              let messageData: Message | null = null

              if (data.data) {
                messageData = data.data as Message
              } else if (data.content && data.message_id) {
                // Flat structure from kafka_bridge
                messageData = {
                  id: data.message_id,
                  project_id: data.project_id || projectId || '',
                  author_type: AuthorType.AGENT,
                  agent_name: data.agent_name || undefined,
                  content: data.content,
                  message_type: data.structured_data ? 'structured' : 'text',
                  structured_data: data.structured_data,
                  created_at: data.timestamp || new Date().toISOString(),
                  updated_at: data.timestamp || new Date().toISOString(),
                }
              }

              if (messageData) {
                setMessages((prev) => {
                  const existsById = prev.some(m => m.id === messageData!.id)
                  if (existsById) return prev
                  return [...prev, messageData!]
                })
              }
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

          case 'agent_step':
            if (data.step === 'started') {
              setAgentProgress({
                isExecuting: true,
                currentAgent: data.agent,
                currentStep: data.message
              })
            } else if (data.step === 'executing') {
              setAgentProgress(prev => ({
                ...prev,
                isExecuting: true,
                currentStep: data.node,
                stepNumber: data.step_number
              }))
            } else if (data.step === 'completed') {
              setAgentProgress({ isExecuting: false, currentStep: data.message })
              setTimeout(() => setAgentProgress({ isExecuting: false }), 2000)
            } else if (data.step === 'error') {
              setAgentProgress({ isExecuting: false, currentStep: data.message })
            }
            break

          case 'agent_thinking':
            // Could display as streaming text
            break

          case 'tool_call':
            setAgentProgress(prev => ({
              ...prev,
              currentTool: data.display_name || data.tool
            }))
            break

          case 'scrum_master_step':
            if (['sprint_planner_started', 'starting', 'saving'].includes(data.step || '')) {
              setAgentProgress({
                isExecuting: true,
                currentAgent: 'Scrum Master',
                currentStep: data.message
              })
            } else if (['sprint_planner_completed', 'completed'].includes(data.step || '')) {
              setAgentProgress({ isExecuting: false, currentStep: data.message })
              setTimeout(() => setAgentProgress({ isExecuting: false }), 2000)
            }
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
                title: data.title!,
                brief: data.brief,
                flows: data.flows,
                backlog: data.backlog,
                sprint_plan: data.sprint_plan,
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
      const authorType = params.author_type || 'user'

      // Add optimistic message for user messages
      if (authorType === 'user' && projectId) {
        const tempMessage: Message = {
          id: `temp-${Date.now()}`,
          project_id: projectId,
          author_type: AuthorType.USER,
          content: params.content,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        }
        setMessages(prev => [...prev, tempMessage])
      }

      wsRef.current!.send(JSON.stringify({
        type: 'message',
        content: params.content,
        author_type: authorType,
      }))
      return true
    } catch (error) {
      console.error('Failed to send message:', error)
      return false
    }
  }, [isWsReady, projectId])

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
    agentProgress,
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
