import { request as __request } from "@client/core/request"
import { OpenAPI } from "@/client"

// ============= Types =============

export interface FileNode {
  name: string
  type: "file" | "folder"
  path: string
  size?: number
  modified?: string
  children?: FileNode[]
  change_type?: string  // Git change type: M, A, D, R, U
}

export interface FileTreeResponse {
  project_id: string
  project_path: string
  root: FileNode
}

export interface FileContentResponse {
  path: string
  name: string
  content: string
  size: number
  modified: string
}

export interface GitStatusResponse {
  project_id: string
  is_git_repo: boolean
  files: Record<string, string>  // {path: change_type}
}

// ============= API =============

export const filesApi = {
  /**
   * Get file tree for a project
   */
  getFileTree: async (projectId: string, depth: number = 3): Promise<FileTreeResponse> => {
    return __request<FileTreeResponse>(OpenAPI, {
      method: "GET",
      url: `/api/v1/projects/${projectId}/files/`,
      query: { depth },
    })
  },

  /**
   * Get content of a specific file
   */
  getFileContent: async (projectId: string, path: string): Promise<FileContentResponse> => {
    return __request<FileContentResponse>(OpenAPI, {
      method: "GET",
      url: `/api/v1/projects/${projectId}/files/content`,
      query: { path },
    })
  },

  /**
   * Get git status (modified, added, deleted, untracked files)
   */
  getGitStatus: async (projectId: string): Promise<GitStatusResponse> => {
    return __request<GitStatusResponse>(OpenAPI, {
      method: "GET",
      url: `/api/v1/projects/${projectId}/files/git-status`,
    })
  },
}
