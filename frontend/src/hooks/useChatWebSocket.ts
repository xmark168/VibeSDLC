import { useEffect, useRef, useState, useCallback } from 'react'
import type { Message } from '@/types/message'

export type WebSocketMessage = {
  type: 'connected' | 'message' | 'agent_message' | 'typing' | 'pong' | 'error' | 'routing' | 'agent_step' | 'agent_thinking' | 'tool_call' | 'agent_question' | 'agent_preview'
  data?: Message
  agent_name?: string
  is_typing?: boolean
  message?: string
  project_id?: string
  // For routing messages
  agent_selected?: string
  confidence?: number
  user_intent?: string
  reasoning?: string
  // For agent_step messages
  step?: string
  agent?: string
  node?: string
  step_number?: number
  // For agent_thinking messages
  content?: string
  // For tool_call messages
  tool?: string
  display_name?: string
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
  const [agentProgress, setAgentProgress] = useState<{
    isExecuting: boolean
    currentStep?: string
    currentAgent?: string
    currentTool?: string
    stepNumber?: number
  }>({
    isExecuting: false
  })
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
            if (data.data) {
              setMessages((prev) => {
                // Check if message already exists
                const exists = prev.some(m => m.id === data.data!.id)
                if (exists) return prev
                return [...prev, data.data!]
              })
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
            console.log('Agent routing:', data.agent_selected, 'confidence:', data.confidence)
            break

          case 'agent_step':
            // Update agent progress
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
              setAgentProgress({
                isExecuting: false,
                currentStep: data.message
              })
              // Clear after a short delay
              setTimeout(() => {
                setAgentProgress({ isExecuting: false })
              }, 2000)
            } else if (data.step === 'error') {
              setAgentProgress({
                isExecuting: false,
                currentStep: data.message
              })
            }
            break

          case 'agent_thinking':
            console.log('Agent thinking:', data.content?.substring(0, 100))
            // Could display this in UI as streaming text
            break

          case 'tool_call':
            console.log('Tool called:', data.display_name || data.tool)
            setAgentProgress(prev => ({
              ...prev,
              currentTool: data.display_name || data.tool
            }))
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
      wsRef.current.send(JSON.stringify({
        type: 'message',
        content: params.content,
        author_type: params.author_type || 'user',
      }))
      return true
    } catch (error) {
      console.error('Failed to send message:', error)
      return false
    }
  }, [])

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
    console.log('[submitPreviewChoice] Called with:', { preview_id, choice, edit_changes })
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

  return {
    isConnected,
    isReady,
    messages,
    typingAgents: Array.from(typingAgents),
    agentProgress,
    pendingQuestions,
    pendingPreviews,
    sendMessage,
    submitAnswer,
    submitPreviewChoice,
    connect,
    disconnect,
  }
}
