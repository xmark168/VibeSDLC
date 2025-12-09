// File system-related types

export interface FileNode {
  name: string
  type: "file" | "folder"
  path: string
  size?: number
  modified?: string
  children?: FileNode[]
}

export interface FileTreeResponse {
  project_id: string
  project_path: string
  tree: FileNode[]
  root: FileNode
}

export interface FileContentResponse {
  path: string
  name: string
  content: string
  size: number
  encoding: string
  modified?: string
  is_binary?: boolean
}

export interface GitStatusResponse {
  project_id: string
  is_git_repo: boolean
  current_branch: string | null
  modified_files: string[]
  staged_files: string[]
  untracked_files: string[]
  ahead: number
  behind: number
}
