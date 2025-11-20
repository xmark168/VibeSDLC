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
  agent_name?: string    // "Team Leader" | "Business Analyst" | "Developer" | "Tester"
  content: string
  message_type?: string  // "text" | "prd" | "business_flows" | "product_backlog" | "sprint_plan"
  structured_data?: any  // JSON data for previews (brief/flows/backlog/sprint)
  metadata?: any         // Preview metadata (preview_id, incomplete_flag, etc.)
  created_at: string
  updated_at: string
}

export type MessagesPage = {
  data: Message[]
  count: number
}
