export interface TechStack {
  id: string
  code: string
  name: string
  description?: string
  image?: string
  stack_config: Record<string, string>
  is_active: boolean
  display_order: number
  created_at: string
  updated_at: string
}

export interface TechStackCreate {
  code: string
  name: string
  description?: string
  image?: string
  stack_config?: Record<string, string>
  display_order?: number
}

export interface TechStackUpdate {
  code?: string
  name?: string
  description?: string
  image?: string
  stack_config?: Record<string, string>
  display_order?: number
  is_active?: boolean
}

export interface TechStacksResponse {
  data: TechStack[]
  count: number
}

export interface FileNode {
  name: string
  type: "file" | "folder"
  path: string
  children?: FileNode[]
}

export interface FileContent {
  path: string
  content: string
}
