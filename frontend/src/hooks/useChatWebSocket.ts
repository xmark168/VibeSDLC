/**
 * Chat WebSocket Hook - Simplified with 4 message types only
 * 
 * Only handles:
 * 1. agent.messaging.start (thinking)
 * 2. agent.messaging.tool_call
 * 3. agent.messaging.response
 * 4. agent.messaging.finish (completed)
 */

import { useEffect, useRef, useState } from 'react'
import useWebSocket, { ReadyState } from 'react-use-websocket'
import type {
  Message,
  TypingState,
  AgentStatusType,
  UseChatWebSocketReturn,
} from '@/types'
import { AuthorType } from '@/types'

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
  const [agentStatus, setAgentStatus] = useState<AgentStatusType>('idle')
  const [typingAgents, setTypingAgents] = useState<Map<string, TypingState>>(new Map())
  
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
      
      case 'agent.messaging.tool_call':
        // Tool calls ignored - no dialog anymore
        console.log('[WS] 🔧 Tool call (ignored):', msg.action, msg.state)
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
     
  }
  
  const handleStart = (msg: any) => {
    console.log('[WS] 🚀 Start:', msg.agent_name, msg.content)
    setAgentStatus('thinking')
    
    // Add typing indicator
    const typingState: TypingState = {
      id: msg.id,
      agent_name: msg.agent_name,
      started_at: msg.timestamp,
      message: msg.content || undefined
    }
    
    setTypingAgents(prev => {
      const updated = new Map(prev)
      updated.set(msg.id, typingState)
      return updated
    })
  }
  
  const handleResponse = (msg: any) => {
    console.log('[WS] 💬 Response:', msg.agent_name)
    
    // Remove typing indicator for this execution
    setTypingAgents(prev => {
      const updated = new Map(prev)
      const executionId = msg.execution_id || msg.id
      updated.delete(executionId)
      return updated
    })
    
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
    
    // Remove typing indicators for this agent
    setTypingAgents(prev => {
      const updated = new Map(prev)
      for (const [id, state] of prev) {
        if (state.agent_name === msg.agent_name) {
          updated.delete(id)
        }
      }
      return updated
    })
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
  
  // Cleanup typing indicators on disconnect
  useEffect(() => {
    if (readyState !== ReadyState.OPEN) {
      setTypingAgents(new Map())
    }
  }, [readyState])

  return {
    isConnected,
    readyState,
    messages,
    agentStatus,
    typingAgents,
    sendMessage,
  }
}
