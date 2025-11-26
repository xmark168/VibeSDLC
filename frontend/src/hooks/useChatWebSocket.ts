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
  MessageStatus,
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
  const [conversationOwner, setConversationOwner] = useState<{
    agentId: string
    agentName: string
    status: 'active' | 'thinking' | 'waiting'
  } | null>(null)
  
  // Refs
  const projectIdRef = useRef(projectId)
  const tempMessageTimeoutsRef = useRef<Map<string, NodeJS.Timeout>>(new Map())
  
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
      
      case 'message_delivered':
        // Router confirms message was routed to agent
        handleMessageDelivered(msg)
        break
      
      case 'error':
        // Backend error occurred
        handleError(msg)
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
      
      case 'agent.question':
        handleAgentQuestion(msg)
        break
      
      case 'agent.question_batch':
        handleQuestionBatch(msg)
        break
      
      case 'question_answer_received':
        handleQuestionAnswerReceived(msg)
        break
      
      case 'batch_answers_received':
        handleBatchAnswersReceived(msg)
        break
      
      case 'agent.resumed':
        handleAgentResumed(msg)
        break
      
      case 'agent.resumed_batch':
        // Similar to agent.resumed, just log it
        console.log('[WS] ✅ Agent resumed from batch answers:', msg.agent_name)
        break
      
      case 'conversation.ownership_changed':
        handleOwnershipChanged(msg)
        break
      
      case 'conversation.ownership_released':
        handleOwnershipReleased(msg)
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
    
    // Replace optimistic (temp_xxx) message with real message from backend
    setMessages(prev => {
      // Find optimistic message by content match
      const optimisticIndex = prev.findIndex(m => 
        m.id.startsWith('temp_') && 
        m.content === msg.content &&
        m.author_type === AuthorType.USER
      )
      
      if (optimisticIndex >= 0) {
        // Clear timeout for this temp message
        const tempId = prev[optimisticIndex].id
        const timeoutId = tempMessageTimeoutsRef.current.get(tempId)
        if (timeoutId) {
          clearTimeout(timeoutId)
          tempMessageTimeoutsRef.current.delete(tempId)
        }
        
        // Replace optimistic with real message
        const newMessages = [...prev]
        newMessages[optimisticIndex] = {
          id: msg.message_id,
          project_id: msg.project_id,
          author_type: AuthorType.USER,
          user_id: msg.user_id,
          content: msg.content,
          message_type: msg.message_type || 'text',
          created_at: msg.created_at || msg.timestamp,
          updated_at: msg.updated_at || msg.timestamp,
          status: 'sent', // Update status to 'sent'
        }
        return newMessages
      }
      
      // Fallback: add as new message if optimistic not found
      return [...prev, {
        id: msg.message_id,
        project_id: msg.project_id,
        author_type: AuthorType.USER,
        user_id: msg.user_id,
        content: msg.content,
        message_type: msg.message_type || 'text',
        created_at: msg.created_at || msg.timestamp,
        updated_at: msg.updated_at || msg.timestamp,
        status: 'sent',
      }]
    })
  }
  
  const handleMessageDelivered = (msg: any) => {
    console.log('[WS] ✓✓ Message delivered to agent:', msg.message_id)
    
    // Update message status to 'delivered'
    setMessages(prev => prev.map(m => 
      m.id === msg.message_id 
        ? { ...m, status: 'delivered' as MessageStatus }
        : m
    ))
  }
  
  const handleError = (msg: any) => {
    console.error('[WS] ❌ Server error:', msg.message)
    
    // Mark last pending message as failed
    setMessages(prev => {
      const lastPending = [...prev].reverse().find(m => m.status === 'pending')
      if (lastPending) {
        return prev.map(m => 
          m.id === lastPending.id 
            ? { ...m, status: 'failed' as MessageStatus }
            : m
        )
      }
      return prev
    })
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
  
  const handleAgentQuestion = (msg: any) => {
    console.log('[WS] ❓ Agent question:', msg.agent_name, msg.question)
    
    const questionMessage: Message = {
      id: msg.question_id,
      project_id: projectIdRef.current!,
      author_type: AuthorType.AGENT,
      agent_name: msg.agent_name,
      content: msg.question,
      message_type: 'agent_question',
      structured_data: {
        question_id: msg.question_id,
        question_type: msg.question_type,
        options: msg.options || [],
        allow_multiple: msg.allow_multiple || false,
      },
      created_at: msg.timestamp,
      updated_at: msg.timestamp,
    }
    
    setMessages(prev => [...prev, questionMessage])
  }
  
  const handleQuestionBatch = (msg: any) => {
    console.log('[WS] ❓❓❓ Question batch:', msg.questions?.length, 'questions')
    
    // Create a single message representing the batch
    const batchMessage: Message = {
      id: msg.batch_id,
      project_id: projectIdRef.current!,
      author_type: AuthorType.AGENT,
      agent_name: msg.agent_name,
      content: `Asking ${msg.questions?.length || 0} questions...`,
      message_type: 'agent_question_batch',
      structured_data: {
        batch_id: msg.batch_id,
        question_ids: msg.question_ids || [],
        questions: msg.questions || [],
        status: 'waiting_answer',
      },
      created_at: msg.timestamp,
      updated_at: msg.timestamp,
    }
    
    setMessages(prev => [...prev, batchMessage])
  }
  
  const handleBatchAnswersReceived = (msg: any) => {
    console.log('[WS] ✓✓✓ Batch answers received:', msg.batch_id, msg.answer_count, 'answers')
    
    // Mark batch as answered
    setMessages(prev => prev.map(m => {
      if (m.structured_data?.batch_id === msg.batch_id) {
        return {
          ...m,
          structured_data: {
            ...m.structured_data,
            answered: true,
            answered_at: msg.timestamp,
            status: 'answered',
          }
        }
      }
      return m
    }))
  }
  
  const handleOwnershipChanged = (msg: any) => {
    console.log('[WS] 👑 Ownership changed:', msg.new_agent_name)
    
    setConversationOwner({
      agentId: msg.new_agent_id,
      agentName: msg.new_agent_name,
      status: 'active'
    })
    
    // Create handoff notification message
    const handoffMessage: Message = {
      id: `handoff_${Date.now()}`,
      project_id: projectIdRef.current!,
      author_type: AuthorType.SYSTEM,
      content: '',
      message_type: 'agent_handoff',
      structured_data: {
        previous_agent_id: msg.previous_agent_id,
        previous_agent_name: msg.previous_agent_name,
        new_agent_id: msg.new_agent_id,
        new_agent_name: msg.new_agent_name,
        reason: msg.reason,
      },
      created_at: msg.timestamp,
      updated_at: msg.timestamp,
    }
    
    setMessages(prev => [...prev, handoffMessage])
  }
  
  const handleOwnershipReleased = (msg: any) => {
    console.log('[WS] ✅ Ownership released:', msg.agent_name)
    
    setConversationOwner(prev => 
      prev?.agentId === msg.agent_id ? null : prev
    )
  }
  
  const handleQuestionAnswerReceived = (msg: any) => {
    console.log('[WS] ✓ Answer received:', msg.question_id)
    
    // Mark question as answered and store user's answer
    setMessages(prev => prev.map(m => {
      if (m.structured_data?.question_id === msg.question_id) {
        return {
          ...m,
          structured_data: {
            ...m.structured_data,
            answered: true,
            answered_at: msg.timestamp,
            user_answer: msg.answer || '',
            user_selected_options: msg.selected_options || [],
          }
        }
      }
      return m
    }))
  }
  
  const handleAgentResumed = (msg: any) => {
    console.log('[WS] ▶️ Agent resumed:', msg.agent_name, 'for question:', msg.question_id)
    
    // Mark question as processing
    setMessages(prev => prev.map(m => {
      if (m.structured_data?.question_id === msg.question_id) {
        return {
          ...m,
          structured_data: {
            ...m.structured_data,
            answered: true,
            processing: true,
          }
        }
      }
      return m
    }))
    
    // Show agent thinking indicator
    setTypingAgents(prev => new Map(prev).set(msg.agent_id, {
      id: msg.agent_id,
      agent_name: msg.agent_name,
      started_at: new Date().toISOString(),
      message: 'Processing your answer...'
    }))
  }
  
  // ========================================================================
  // Send Message
  // ========================================================================
  
  const sendMessage = (content: string, agentName?: string) => {
    if (!projectIdRef.current) {
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
      const optimisticMsg = createOptimisticMessage(content, projectIdRef.current)
      setMessages(prev => [...prev, optimisticMsg])

      // Set timeout to mark as failed if no confirmation within 10s
      const timeoutId = setTimeout(() => {
        setMessages(prev => prev.map(m => 
          m.id === optimisticMsg.id 
            ? { ...m, status: 'failed' as MessageStatus }
            : m
        ))
        tempMessageTimeoutsRef.current.delete(optimisticMsg.id)
        console.warn(`[WebSocket] ⚠️ Message timeout: ${optimisticMsg.id}`)
      }, 10000) // 10 seconds timeout
      
      tempMessageTimeoutsRef.current.set(optimisticMsg.id, timeoutId)

      // Send to server
      sendJsonMessage({
        type: 'message',
        content: content.trim(),
        agent_name: agentName,
        project_id: projectIdRef.current,
      })
      
      console.log('[WebSocket] 📤 Sent:', content.substring(0, 50))
    } catch (error) {
      console.error('[WebSocket] ❌ Failed to send:', error)
    }
  }
  
  const sendQuestionAnswer = (
    question_id: string,
    answer: string,
    selected_options?: string[]
  ) => {
    if (readyState !== ReadyState.OPEN) {
      console.error('[WS] Cannot send answer: not connected')
      return false
    }
    
    try {
      sendJsonMessage({
        type: 'question_answer',
        question_id,
        answer: answer || '',
        selected_options: selected_options || [],
      })
      
      console.log('[WS] 📨 Sent answer:', { question_id, answer, selected_options })
      return true
    } catch (error) {
      console.error('[WS] Failed to send answer:', error)
      return false
    }
  }
  
  const sendBatchAnswers = (
    batch_id: string,
    answers: Array<{ question_id: string; answer: string; selected_options?: string[] }>
  ) => {
    if (readyState !== ReadyState.OPEN) {
      console.error('[WS] Cannot send batch answers: not connected')
      return false
    }
    
    try {
      sendJsonMessage({
        type: 'question_batch_answer',
        batch_id,
        answers,
      })
      
      console.log('[WS] 📨📨📨 Sent batch answers:', { batch_id, count: answers.length })
      return true
    } catch (error) {
      console.error('[WS] Failed to send batch answers:', error)
      return false
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

  // Cleanup timeouts on unmount
  useEffect(() => {
    return () => {
      // Clear all timeouts on unmount
      tempMessageTimeoutsRef.current.forEach(timeoutId => clearTimeout(timeoutId))
      tempMessageTimeoutsRef.current.clear()
    }
  }, [])

  return {
    isConnected,
    readyState,
    messages,
    agentStatus,
    typingAgents,
    conversationOwner,
    sendMessage,
    sendQuestionAnswer,
    sendBatchAnswers,
  }
}
