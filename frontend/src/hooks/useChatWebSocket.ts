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
  BackgroundTask,
  ExecutionContext,
} from '@/types'
import { AuthorType } from '@/types'
import { toast } from "@/lib/toast"

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
  const [backgroundTasks, setBackgroundTasks] = useState<Map<string, BackgroundTask>>(new Map())  // NEW
  const [answeredBatchIds, setAnsweredBatchIds] = useState<Set<string>>(new Set())  // Track answered batches
  const [conversationOwner, setConversationOwner] = useState<{
    agentId: string
    agentName: string
    status: 'active' | 'thinking' | 'waiting'
  } | null>(null)
  // Track individual agent statuses for avatar display
  const [agentStatuses, setAgentStatuses] = useState<Map<string, { status: string; lastUpdate: string }>>(new Map())
  // Trigger for refetching messages (increments when new_message received)
  const [refetchTrigger, setRefetchTrigger] = useState(0)
  
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
          return false
        }
        return true
      },
      reconnectAttempts: 10,
      reconnectInterval: (attemptNumber) => 
        Math.min(1000 * Math.pow(2, attemptNumber), 30000),
      
      share: false,
      retryOnError: true,
    },
    !!socketUrl
  )

  // Handle messages - ONLY 5 types
  useEffect(() => {
    if (!lastJsonMessage) return
    
    const msg = lastJsonMessage as any
    
    // Validate message
    if (!msg || typeof msg !== 'object' || !msg.type) {
      return
    }
    
    
    switch (msg.type) {
      case 'connected':
        break
      
      case 'messages_updated':
        handleMessagesUpdated()
        break
      
      case 'user_message':
        handleUserMessage(msg)
        break
      
      case 'message_delivered':
        handleMessageDelivered(msg)
        break
      
      case 'error':
        handleError(msg)
        break
      
      case 'agent.messaging.start':
        handleStart(msg)
        break
      
      case 'agent.messaging.progress':
        handleProgress(msg)
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
        break
      
      case 'conversation.ownership_changed':
        handleOwnershipChanged(msg)
        break
      
      case 'conversation.ownership_released':
        handleOwnershipReleased(msg)
        break
      
      case 'story_message':
        handleStoryMessage(msg)
        break
      
      case 'story_log':
        handleStoryLog(msg)
        break
      
      case 'story_task':
        handleStoryTask(msg)
        break
      
      case 'story_state_changed':
        handleStoryStateChanged(msg)
        break
      
      case 'story_status_changed':
        handleStoryStatusChanged(msg)
        break
      
      case 'branch_changed':
        handleBranchChanged(msg)
        break
      
      case 'project_dev_server':
        handleProjectDevServer(msg)
        break
      
      case 'dev_server_log':
        handleDevServerLog(msg)
        break
      
      default:
        console.warn('[WebSocket] Unknown message type:', msg.type)
    }
  }, [lastJsonMessage])
  
  // ========================================================================
  // Message Handlers
  // ========================================================================
  
  const handleMessagesUpdated = () => {
    setRefetchTrigger(prev => prev + 1)
  }
  
  const handleUserMessage = (msg: any) => {
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
    // Update message status to 'delivered'
    setMessages(prev => prev.map(m => 
      m.id === msg.message_id 
        ? { ...m, status: 'delivered' as MessageStatus }
        : m
    ))
  }
  
  const handleError = (msg: any) => {
    
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
    const displayMode = msg.execution_context?.display_mode || 'chat'
        
    // Update agent status to busy/working
    if (msg.agent_name) {
      setAgentStatuses(prev => {
        const updated = new Map(prev)
        updated.set(msg.agent_name, { status: 'busy', lastUpdate: msg.timestamp || new Date().toISOString() })
        return updated
      })
    }
    
    // Handle based on display mode
    if (displayMode === 'none') {
      // Silent mode - skip
      return
    }
    
    if (displayMode === 'chat') {
      // Interactive mode - show typing indicator
      setAgentStatus('thinking')
      
      const typingState: TypingState = {
        id: msg.id,
        agent_name: msg.agent_name,
        started_at: msg.timestamp,
        message: msg.content || undefined
      }
      
      setTypingAgents(prev => {
        const updated = new Map(prev)
        // Clear existing typing indicators for this agent first (prevent duplicates)
        // for (const [id, state] of prev) {
        //   if (state.agent_name === msg.agent_name) {
        //     updated.delete(id)
        //   }
        // }
        // Add new typing indicator
        updated.set(msg.id, typingState)
        return updated
      })
    }
  }
  
  const handleProgress = (msg: any) => {
    const displayMode = msg.execution_context?.display_mode || 'chat'
    const details = msg.details || {}
        
    // Handle based on display mode
    switch (displayMode) {
      case 'chat':
        // Show as chat message
        const progressMessage: Message = {
          id: `progress_${msg.timestamp}_${Math.random()}`,
          project_id: projectIdRef.current!,
          agent_name: msg.agent_name,
          author_type: AuthorType.AGENT,
          content: msg.content,
          message_type: 'agent_progress',
          structured_data: details,
          created_at: msg.timestamp,
          updated_at: msg.timestamp,
        }
        setMessages(prev => [...prev, progressMessage])
        break
      
      case 'progress_bar':
        // Update background task
        const taskId = msg.execution_context?.task_id || msg.task_id
        if (taskId) {
          setBackgroundTasks(prev => {
            const updated = new Map(prev)
            updated.set(taskId, {
              task_id: taskId,
              agent_name: msg.agent_name,
              status: 'in_progress',
              current: details.step || 0,
              total: details.total || 100,
              percentage: details.percentage || 0,
              message: msg.content,
              updated_at: msg.timestamp,
            })
            return updated
          })
        }
        break
      
      case 'notification':
        // Show as toast
        const stepInfo = details.step ? ` (${details.step}/${details.total})` : ''
        toast.success(`${msg.agent_name}${stepInfo}: ${msg.content}`)
        break
      
      case 'none':
        // Silent - skip
        break
    }
  }
  
  const handleResponse = (msg: any) => {
    const displayMode = msg.execution_context?.display_mode || 'chat'
        
    // Remove typing indicator for this execution
    setTypingAgents(prev => {
      const updated = new Map(prev)
      const executionId = msg.execution_id || msg.id
      updated.delete(executionId)
      return updated
    })
    
    // Handle based on display mode
    if (displayMode === 'none') {
      // Silent - skip
      return
    }
    
    if (displayMode === 'notification') {
      // Show as toast
      toast.success(`${msg.agent_name}: ${msg.content}`)
      return
    }
    
    // Chat or progress_bar mode: Add to messages
    // Note: Backend sends 'details' but DB stores as 'structured_data'
    const message: Message = {
      id: msg.id,
      project_id: projectIdRef.current!,
      agent_name: msg.agent_name,
      author_type: AuthorType.AGENT,
      content: msg.content,
      message_type: msg.details?.message_type || msg.message_type || 'text',
      structured_data: msg.details || msg.structured_data || {},
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
    const displayMode = msg.execution_context?.display_mode || 'chat'
    setAgentStatus('idle')
    
    // Update agent status back to idle
    if (msg.agent_name) {
      setAgentStatuses(prev => {
        const updated = new Map(prev)
        updated.set(msg.agent_name, { status: 'idle', lastUpdate: msg.timestamp || new Date().toISOString() })
        return updated
      })
    }
    
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
    
    // Mark background task as completed (if any)
    const taskId = msg.execution_context?.task_id || msg.task_id
    if (taskId && displayMode === 'progress_bar') {
      setBackgroundTasks(prev => {
        const task = prev.get(taskId)
        if (task) {
          const updated = new Map(prev)
          updated.set(taskId, {
            ...task,
            status: 'completed',
            percentage: 100,
            message: msg.summary || 'Completed',
            updated_at: msg.timestamp,
          })
          
          // Remove after 3 seconds
          setTimeout(() => {
            setBackgroundTasks(current => {
              const next = new Map(current)
              next.delete(taskId)
              return next
            })
          }, 3000)
          
          return updated
        }
        return prev
      })
    }
  }
  
  const handleAgentQuestion = (msg: any) => {
    
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
    
    // Track this batch as answered (for messages from API that won't update via setMessages)
    setAnsweredBatchIds(prev => new Set([...prev, msg.batch_id]))
    
    // Also update wsMessages for consistency
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
    
    setConversationOwner({
      agentId: msg.new_agent_id,
      agentName: msg.new_agent_name,
      status: 'active'
    })
    
    // Create handoff notification message
    const handoffMessage: Message = {
      id: `handoff_${Date.now()}`,
      project_id: projectIdRef.current!,
      author_type: AuthorType.AGENT,  // System notification shown as agent message
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
    
    setConversationOwner(prev => 
      prev?.agentId === msg.agent_id ? null : prev
    )
  }
  
  const handleStoryTask = (msg: any) => {
    
    window.dispatchEvent(new CustomEvent('story-task', {
      detail: {
        story_id: msg.story_id,
        content: msg.content,
        node: msg.node,
        progress: msg.progress,
        timestamp: msg.timestamp,
      }
    }))
  }
  
  const handleStoryLog = (msg: any) => {
    
    window.dispatchEvent(new CustomEvent('story-log', {
      detail: {
        story_id: msg.story_id,
        content: msg.content,
        level: msg.level,
        node: msg.node,
        timestamp: msg.timestamp,
      }
    }))
  }
  
  const handleStoryMessage = (msg: any) => {    
    // Dispatch message event for Chat tab in story detail
    window.dispatchEvent(new CustomEvent('story-message', {
      detail: {
        story_id: msg.story_id,
        content: msg.content,
        message_type: msg.message_type,
        author_name: msg.author_name,
        timestamp: msg.timestamp,
        details: msg.details,
      }
    }))
    
    // Dispatch custom event for story state updates
    if (msg.agent_state) {
      window.dispatchEvent(new CustomEvent('story-state-changed', {
        detail: { story_id: msg.story_id, agent_state: msg.agent_state }
      }))
    }
  }
  
  const handleStoryStateChanged = (msg: any) => {    
    // Dispatch custom event for components to listen
    window.dispatchEvent(new CustomEvent('story-state-changed', {
      detail: { 
        story_id: msg.story_id, 
        agent_state: msg.agent_state,
        sub_status: msg.sub_status,  // NEW: sub-status for PENDING state (queued/cleaning/starting)
        old_state: msg.old_state,
        running_port: msg.running_port,
        running_pid: msg.running_pid,
        pr_state: msg.pr_state,
        merge_status: msg.merge_status,
      }
    }))
  }
  
  const handleStoryStatusChanged = (msg: any) => {    
    // Dispatch custom event for KanbanBoard to listen
    window.dispatchEvent(new CustomEvent('story-status-changed', {
      detail: { 
        story_id: msg.story_id, 
        status: msg.status,
        merge_status: msg.merge_status,
        pr_state: msg.pr_state,
      }
    }))
  }
  
  const handleBranchChanged = (msg: any) => {    
    // Dispatch custom event for FileExplorer to listen
    window.dispatchEvent(new CustomEvent('branch-changed', {
      detail: { 
        project_id: msg.project_id, 
        branch: msg.branch
      }
    }))
  }
  
  const handleProjectDevServer = (msg: any) => {    
    // Dispatch custom event for AppViewer to listen
    window.dispatchEvent(new CustomEvent('project_dev_server', {
      detail: { 
        project_id: msg.project_id, 
        running_port: msg.running_port,
        running_pid: msg.running_pid,
      }
    }))
  }
  
  const handleDevServerLog = (msg: any) => {    
    // Dispatch custom event for AppViewer to listen
    window.dispatchEvent(new CustomEvent('dev_server_log', {
      detail: { 
        project_id: msg.project_id, 
        message: msg.message,
        status: msg.status,
      }
    }))
  }
  
  const handleQuestionAnswerReceived = (msg: any) => {    
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
    // setTypingAgents(prev => new Map(prev).set(msg.agent_id, {
    //   id: msg.agent_id,
    //   agent_name: msg.agent_name,
    //   started_at: new Date().toISOString(),
    //   message: 'Processing your answer...'
    // }))
  }
  
  // ========================================================================
  // Send Message
  // ========================================================================
  
  const sendMessage = (content: string, agentName?: string) => {
    if (!projectIdRef.current) {
      return
    }

    if (readyState !== ReadyState.OPEN) {
      return
    }

    if (!content || !content.trim()) {
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
      }, 10000) // 10 seconds timeout
      
      tempMessageTimeoutsRef.current.set(optimisticMsg.id, timeoutId)

      // Send to server
      sendJsonMessage({
        type: 'message',
        content: content.trim(),
        agent_name: agentName,
        project_id: projectIdRef.current,
      })   
    } catch (error) {
    }
  }
  
  const sendQuestionAnswer = (
    question_id: string,
    answer: string,
    selected_options?: string[]
  ) => {
    if (readyState !== ReadyState.OPEN) {
      return false
    }
    
    try {
      sendJsonMessage({
        type: 'question_answer',
        question_id,
        answer: answer || '',
        selected_options: selected_options || [],
      })
      return true
    } catch (error) {
      return false
    }
  }
  
  const sendBatchAnswers = (
    batch_id: string,
    answers: Array<{ question_id: string; answer: string; selected_options?: string[] }>
  ) => {
    if (readyState !== ReadyState.OPEN) {
      return false
    }
    
    try {
      sendJsonMessage({
        type: 'question_batch_answer',
        batch_id,
        answers,
      })
      
      
      // Immediately update local state with answers (don't wait for server confirmation)
      setMessages(prev => prev.map(m => {
        if (m.structured_data?.batch_id === batch_id) {
          return {
            ...m,
            structured_data: {
              ...m.structured_data,
              answered: true,
              status: 'answered',
              answers: answers,  // Save answers locally
            }
          }
        }
        return m
      }))
      
      // Also mark as answered
      setAnsweredBatchIds(prev => new Set([...prev, batch_id]))
      
      return true
    } catch (error) {
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
    agentStatuses,  // Individual agent statuses for avatar display
    typingAgents,
    backgroundTasks,  // NEW
    answeredBatchIds,  // Track batches that have been answered
    conversationOwner,
    refetchTrigger,  // Trigger for refetching messages (file uploads)
    sendMessage,
    sendQuestionAnswer,
    sendBatchAnswers,
  }
}
