// Chat-related types for project communication with AI agents

export type AgentType = 'FLOW_MANAGER' | 'BUSINESS_ANALYST' | 'DEVELOPER' | 'TESTER'

export interface Agent {
  id: number
  type: AgentType
  name: string
  description: string
  avatar?: string
  color: string // For UI differentiation
}

export type MessageRole = 'user' | 'agent'

export interface Message {
  id: string
  role: MessageRole
  content: string
  agentType?: AgentType // Only for agent messages
  timestamp: Date
  isTyping?: boolean
}

export interface Conversation {
  agentType: AgentType | 'ALL' // 'ALL' for general project assistant
  messages: Message[]
}

// Agent metadata for UI
export const AGENT_INFO: Record<AgentType, { name: string; description: string; color: string; icon: string }> = {
  FLOW_MANAGER: {
    name: 'Flow Manager',
    description: 'Manages project workflow and priorities',
    color: '#3b82f6', // blue
    icon: 'workflow',
  },
  BUSINESS_ANALYST: {
    name: 'Business Analyst',
    description: 'Analyzes requirements and creates user stories',
    color: '#8b5cf6', // purple
    icon: 'briefcase',
  },
  DEVELOPER: {
    name: 'Developer',
    description: 'Implements features and technical solutions',
    color: '#10b981', // green
    icon: 'code',
  },
  TESTER: {
    name: 'Tester',
    description: 'Ensures quality through testing',
    color: '#f59e0b', // amber
    icon: 'bug',
  },
}
