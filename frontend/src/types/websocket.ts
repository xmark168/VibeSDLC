// WebSocket and real-time communication types

import type { Message } from './message'
import type { ReadyState } from 'react-use-websocket'

export interface TypingState {
  id: string
  agent_name: string
  started_at: string
  message?: string
}

export type AgentStatusType = 'idle' | 'thinking' | 'acting'

// NEW: Execution context from backend
export interface ExecutionContext {
  mode: 'interactive' | 'background' | 'silent'
  task_id: string
  task_type: string
  display_mode: 'chat' | 'progress_bar' | 'notification' | 'none'
}

// NEW: Background task tracking
export interface BackgroundTask {
  task_id: string
  agent_name: string
  status: 'in_progress' | 'completed' | 'failed'
  current: number
  total: number
  percentage: number
  message: string
  updated_at: string
}

export interface UseChatWebSocketReturn {
  isConnected: boolean
  readyState: ReadyState
  messages: Message[]
  agentStatus: AgentStatusType
  agentStatuses: Map<string, { status: string; lastUpdate: string }>  // Individual agent statuses
  typingAgents: Map<string, TypingState>
  backgroundTasks: Map<string, BackgroundTask>  // NEW
  answeredBatchIds: Set<string>  // Track answered batch question IDs
  conversationOwner: {
    agentId: string
    agentName: string
    status: 'active' | 'thinking' | 'waiting'
  } | null
  refetchTrigger: number  // Trigger for refetching messages (file uploads)
  sendMessage: (content: string, agentName?: string) => void
  sendQuestionAnswer: (question_id: string, answer: string, selected_options?: string[]) => boolean
  sendBatchAnswers: (batch_id: string, answers: Array<{ question_id: string; answer: string; selected_options?: string[] }>) => boolean
}
