export enum AuthorType {
  USER = "user",
  AGENT = "agent",
}

export type MessageStatus = "pending" | "sent" | "delivered" | "failed"

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
  question_type: "open" | "multichoice"
  options?: string[]
  allow_multiple?: boolean
  context?: any
}

export interface MessageAttachment {
  type: "document"
  filename: string
  file_path: string
  file_size: number
  mime_type?: string
  extracted_text?: string
}

export type Message = {
  id: string
  project_id: string
  author_type: AuthorType
  user_id?: string
  agent_id?: string
  agent_name?: string // "Team Leader" | "Business Analyst" | "Developer" | "Tester"
  persona_avatar?: string // Agent's persona avatar URL
  content: string
  message_type?: string // "text" | "artifact_created" (PRD, analysis, etc.) | "stories_created" | "agent_question" | "document_upload" | etc.
  structured_data?: ArtifactData | StoriesCreatedData | AgentQuestionData | any // JSON data for cards/previews
  message_metadata?: any // Message metadata (agent_name, preview_id, incomplete_flag, etc.)
  attachments?: MessageAttachment[] // File attachments (for document uploads)
  created_at: string
  updated_at: string
  status?: MessageStatus // Message delivery status (for user messages)
}

export type MessagesPage = {
  data: Message[]
  count: number
}
