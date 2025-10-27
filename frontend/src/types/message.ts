export enum AuthorType {
  USER = 'user',
  AGENT = 'agent'
}

export type Message = {
  id: string
  project_id: string
  author_type: AuthorType
  user_id?: string
  agent_id?: string
  content: string
  created_at: string
  updated_at: string
}

export type MessagesPage = {
  data: Message[]
  count: number
}