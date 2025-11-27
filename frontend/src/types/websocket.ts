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

export interface UseChatWebSocketReturn {
  isConnected: boolean
  readyState: ReadyState
  messages: Message[]
  agentStatus: AgentStatusType
  typingAgents: Map<string, TypingState>
  sendMessage: (content: string, agentName?: string) => void
}
