export type Project = {
  id: string
  code: string
  name: string
  owner_id: string
  is_init: boolean
  created_at?: string
  updated_at?: string
}

export type ProjectsPage = {
  data: Project[]
  count: number
}