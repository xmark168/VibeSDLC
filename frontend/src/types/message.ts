export enum AuthorType {
  USER = "user",
  AGENT = "agent",
}

export type Message = {
  id: string
  project_id: string
  author_type: AuthorType
  user_id?: string
  agent_id?: string
  content: string
  message_type?: string  // "text" | "product_brief" | "product_vision" | "product_backlog" | "sprint_plan"
  structured_data?: any  // JSON data for previews (brief/vision/backlog/sprint)
  metadata?: any         // Preview metadata (preview_id, quality_score, etc.)
  created_at: string
  updated_at: string
}

export type MessagesPage = {
  data: Message[]
  count: number
}
