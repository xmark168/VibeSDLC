/**
 * Chat WebSocket Hook - Simplified with 5 message types only
 * 
 * Only handles:
 * 1. agent.messaging.start
 * 2. agent.messaging.analyzing
 * 3. agent.messaging.tool_call
 * 4. agent.messaging.response
 * 5. agent.messaging.finish
 */

import { useEffect, useRef, useState } from 'react'
import useWebSocket, { ReadyState } from 'react-use-websocket'
import { AuthorType, Message } from '@/types/message'

// ============================================================================
// Types
// ============================================================================

export interface Execution {
  id: string
  agent_name: string
  steps: string[]
  tools: ToolCall[]
  startedAt: string
}

export interface ToolCall {
  id: string
  tool: string
  action: string
  state: 'started' | 'completed' | 'failed'
}

export type AgentStatusType = 'idle' | 'thinking' | 'acting'

export interface UseChatWebSocketReturn {
  // Connection state
  isConnected: boolean
  readyState: ReadyState
  
  // Messages
  messages: Message[]
  
  // Active execution (for dialog)
  activeExecution: Execution | null
  
  // Agent status
  agentStatus: AgentStatusType
  
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
  const [activeExecution, setActiveExecution] = useState<Execution | null>(null)
  const [agentStatus, setAgentStatus] = useState<AgentStatusType>('idle')
  
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
        // Don't reconnect if explicitly closed or auth failed
        if (closeEvent.code === 1000 || closeEvent.code === 1008) {
          console.log('[WebSocket] Clean close or auth failed - not reconnecting')
          return false
        }
        return true
      },
      reconnectAttempts: 10,
      reconnectInterval: (attemptNumber) => 
        Math.min(1000 * Math.pow(2, attemptNumber), 30000),
      
      share: false,
      retryOnError: true,
      
      onOpen: () => {
        console.log('[WebSocket] ✅ Connected')
      },
      onClose: (event) => {
        console.log('[WebSocket] ❌ Disconnected - Code:', event.code)
      },
      onError: (event) => {
        console.error('[WebSocket] ⚠️ Error:', event)
      },
    },
    !!socketUrl
  )

  // Handle messages - ONLY 5 types
  useEffect(() => {
    if (!lastJsonMessage) return
    
    const msg = lastJsonMessage as any
    
    // Validate message
    if (!msg || typeof msg !== 'object' || !msg.type) {
      console.warn('[WebSocket] Invalid message:', msg)
      return
    }
    
    console.log('[WebSocket] 📨', msg.type, msg)
    
    switch (msg.type) {
      case 'connected':
        console.log('[WS] ✅ Server confirmed connection')
        break
      
      case 'user_message':
        // Backend confirms user message was saved
        handleUserMessage(msg)
        break
      
      case 'agent.messaging.start':
        handleStart(msg)
        break
      
      case 'agent.messaging.analyzing':
        handleAnalyzing(msg)
        break
      
      case 'agent.messaging.tool_call':
        handleToolCall(msg)
        break
      
      case 'agent.messaging.response':
        handleResponse(msg)
        break
      
      case 'agent.messaging.finish':
        handleFinish(msg)
        break
      
      default:
        console.warn('[WebSocket] ⚠️ Unknown message type:', msg.type)
    }
  }, [lastJsonMessage])
  
  // ========================================================================
  // Message Handlers
  // ========================================================================
  
  const handleUserMessage = (msg: any) => {
    console.log('[WS] 📤 User message confirmed:', msg.message_id)
    // Replace optimistic message with real one
    // setMessages(prev => {
    //   const tempIndex = prev.findIndex(m => m.id.startsWith('temp_'))
    //   if (tempIndex !== -1) {
    //     const newMessages = [...prev]
    //     newMessages[tempIndex] = {
    //       id: msg.message_id,
    //       project_id: msg.project_id,
    //       author_type: AuthorType.USER,
    //       content: msg.content,
    //       created_at: msg.created_at || msg.timestamp,
    //       updated_at: msg.updated_at || msg.timestamp,
    //       status: 'delivered',
    //     }
        // return newMessages
      // }
    //   // return prev
    // })
  }
  
  const handleStart = (msg: any) => {
    console.log('[WS] 🚀 Start:', msg.agent_name)
    setAgentStatus('thinking')
    setActiveExecution({
      id: msg.id,
      agent_name: msg.agent_name,
      steps: [],
      tools: [],
      startedAt: msg.timestamp,
    })
  }
  
  const handleAnalyzing = (msg: any) => {
    console.log('[WS] 🔄 Analyzing:', msg.step)
    setAgentStatus('acting')
    setActiveExecution(prev => prev ? {
      ...prev,
      steps: [...prev.steps, msg.step]
    } : null)
  }
  
  const handleToolCall = (msg: any) => {
    console.log('[WS] 🔧 Tool:', msg.action, msg.state)
    setActiveExecution(prev => prev ? {
      ...prev,
      tools: [
        ...prev.tools.filter(t => t.id !== msg.id),
        { 
          id: msg.id, 
          tool: msg.tool, 
          action: msg.action, 
          state: msg.state 
        }
      ]
    } : null)
  }
  
  const handleResponse = (msg: any) => {
    console.log('[WS] 💬 Response:', msg.agent_name)
    const message: Message = {
      id: msg.id,
      project_id: projectIdRef.current!,
      agent_name: msg.agent_name,
      author_type: AuthorType.AGENT,
      content: msg.content,
      message_type: msg.message_type,
      structured_data: msg.structured_data,
      created_at: msg.timestamp,
      updated_at: msg.timestamp,
    }
    
    setMessages(prev => {
      // Avoid duplicates
      if (prev.some(m => m.id === message.id)) {
        return prev
      }
      return [...prev, message]
    })
  }
  
  const handleFinish = (msg: any) => {
    console.log('[WS] ✅ Finish:', msg.summary)
    setAgentStatus('idle')
    
    // Auto-close execution after 3s
    setTimeout(() => {
      setActiveExecution(null)
    }, 3000)
  }
  
  // ========================================================================
  // Send Message
  // ========================================================================
  
  const sendMessage = (content: string, agentName?: string) => {
    if (!projectId) {
      console.error('[WebSocket] ❌ Cannot send: no project ID')
      return
    }

    if (readyState !== ReadyState.OPEN) {
      console.warn('[WebSocket] ⚠️ Cannot send: not connected')
      return
    }

    if (!content || !content.trim()) {
      console.warn('[WebSocket] ⚠️ Cannot send empty message')
      return
    }

    try {
      // Add optimistic message
      const optimisticMsg = createOptimisticMessage(content, projectId)
      setMessages(prev => [...prev, optimisticMsg])

      // Send to server
      sendJsonMessage({
        type: 'message',
        content: content.trim(),
        agent_name: agentName,
        project_id: projectId,
      })
      
      console.log('[WebSocket] 📤 Sent:', content.substring(0, 50))
    } catch (error) {
      console.error('[WebSocket] ❌ Failed to send:', error)
    }
  }

  // Connection status
  const isConnected = readyState === ReadyState.OPEN

  return {
    isConnected,
    readyState,
    messages,
    activeExecution,
    agentStatus,
    sendMessage,
  }
}
