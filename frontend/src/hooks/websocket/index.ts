/**
 * WebSocket Hooks - Modular WebSocket functionality
 * 
 * This package provides a set of composable hooks for WebSocket communication.
 * 
 * Architecture:
 * - Base hooks: Individual concerns (connection, messages, status, etc.)
 * - Facade hook: Combined interface for convenience
 * 
 * Usage:
 * 
 * // Option 1: Use facade hook (recommended for most cases)
 * import { useChatWebSocket } from '@/hooks/websocket'
 * 
 * const { messages, sendMessage, agentStatus } = useChatWebSocket(projectId, token)
 * 
 * // Option 2: Use individual hooks (for custom compositions)
 * import { useWebSocket, useWebSocketMessages, useAgentStatus } from '@/hooks/websocket'
 * 
 * const ws = useWebSocket({ projectId, token })
 * const messages = useWebSocketMessages({ projectId })
 * const status = useAgentStatus()
 */

// Base hooks
export { useWebSocket } from './useWebSocket'
export type { 
  UseWebSocketOptions, 
  UseWebSocketReturn,
  WebSocketState 
} from './useWebSocket'

export { useWebSocketMessages } from './useWebSocketMessages'
export type {
  UseWebSocketMessagesOptions,
  UseWebSocketMessagesReturn,
  WebSocketMessageData
} from './useWebSocketMessages'

export { useAgentStatus } from './useAgentStatus'
export type {
  UseAgentStatusOptions,
  UseAgentStatusReturn,
  AgentStatus,
  AgentStatusType,
  AgentStatusMap
} from './useAgentStatus'

export { useActivityUpdates } from './useActivityUpdates'
export type {
  UseActivityUpdatesOptions,
  UseActivityUpdatesReturn,
  AgentProgress,
  ToolCall,
  ApprovalRequest
} from './useActivityUpdates'

export { useKanbanUpdates } from './useKanbanUpdates'
export type {
  UseKanbanUpdatesOptions,
  UseKanbanUpdatesReturn,
  KanbanData,
  KanbanBoard
} from './useKanbanUpdates'

// Facade hook (recommended)
export { useChatWebSocket } from './useChatWebSocket'
export type {
  UseChatWebSocketOptions,
  UseChatWebSocketReturn,
  SendMessageParams
} from './useChatWebSocket'
