export enum AuthorType {
  USER = "user",
  AGENT = "agent",
}

export type MessageStatus = 'pending' | 'sent' | 'delivered' | 'failed'

// Structured data interfaces for message cards
export interface ArtifactData {
  artifact_id: string
  artifact_type: string
  title: string
  description?: string
  version: number
  status: string
  agent_name?: string
}

export interface StoriesCreatedData {
  count: number
  story_ids: string[]
  prd_artifact_id?: string
}

export interface AgentQuestionData {
  question_id: string
  question_text: string
  question_type: 'open' | 'multichoice'
  options?: string[]
  allow_multiple?: boolean
  context?: any
}

export type Message = {
  id: string
  project_id: string
  author_type: AuthorType
  user_id?: string
  agent_id?: string
  agent_name?: string    // "Team Leader" | "Business Analyst" | "Developer" | "Tester"
  content: string
  message_type?: string  // "text" | "artifact_created" (PRD, analysis, etc.) | "stories_created" | "agent_question" | etc.
  structured_data?: ArtifactData | StoriesCreatedData | AgentQuestionData | any  // JSON data for cards/previews
  message_metadata?: any // Message metadata (agent_name, preview_id, incomplete_flag, etc.)
  created_at: string
  updated_at: string
  status?: MessageStatus // Message delivery status (for user messages)
}

export type MessagesPage = {
  data: Message[]
  count: number
}
