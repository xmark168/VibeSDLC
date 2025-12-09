// API request and response types

// Message API types
export type FetchMessagesParams = {
  project_id: string
  skip?: number
  limit?: number
  order?: 'asc' | 'desc'  // asc = oldest first, desc = newest first
}

export type CreateMessageBody = {
  project_id: string
  content: string
  agent_name?: string
}

export type UpdateMessageBody = {
  content?: string
}

// Project API types
export type FetchProjectsParams = {
  search?: string
  page?: number
  pageSize?: number
  limit?: number
}

export type CreateProjectBody = {
  code: string
  name: string
  description?: string
}

export type UpdateProjectBody = {
  code?: string
  name?: string
  description?: string
}

// Time range type for admin dashboard
export type TimeRange = "1h" | "6h" | "24h" | "7d" | "30d"
