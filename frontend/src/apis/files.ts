import { request as __request } from "@client/core/request"
import { OpenAPI } from "@/client"
import type {
  FileContentResponse,
  FileNode,
  FileTreeResponse,
  GitStatusResponse,
} from "@/types"

// Re-export types for convenience
export type {
  FileNode,
  FileTreeResponse,
  FileContentResponse,
  GitStatusResponse,
}

// ============= API =============

export const filesApi = {
  /**
   * Get file tree for a project
   */
  getFileTree: async (
    projectId: string,
    depth: number = 15,
    worktree?: string,
  ): Promise<FileTreeResponse> => {
    return __request<FileTreeResponse>(OpenAPI, {
      method: "GET",
      url: `/api/v1/projects/${projectId}/files/`,
      query: { depth, ...(worktree && { worktree }) },
    })
  },

  /**
   * Lazy load children of a folder
   */
  getFolderChildren: async (
    projectId: string,
    path: string,
    worktree?: string,
    depth: number = 1,
  ): Promise<FolderChildrenResponse> => {
    return __request<FolderChildrenResponse>(OpenAPI, {
      method: "GET",
      url: `/api/v1/projects/${projectId}/files/children`,
      query: { path, depth, ...(worktree && { worktree }) },
    })
  },

  /**
   * Get content of a specific file
   */
  getFileContent: async (
    projectId: string,
    path: string,
    worktree?: string,
  ): Promise<FileContentResponse> => {
    return __request<FileContentResponse>(OpenAPI, {
      method: "GET",
      url: `/api/v1/projects/${projectId}/files/content`,
      query: { path, ...(worktree && { worktree }) },
    })
  },

  /**
   * Get git status (modified, added, deleted, untracked files)
   */
  getGitStatus: async (
    projectId: string,
    worktree?: string,
  ): Promise<GitStatusResponse> => {
    return __request<GitStatusResponse>(OpenAPI, {
      method: "GET",
      url: `/api/v1/projects/${projectId}/files/git-status`,
      query: { ...(worktree && { worktree }) },
    })
  },

  /**
   * Get branches and worktrees in project repository
   */
  getBranches: async (projectId: string): Promise<BranchesResponse> => {
    return __request<BranchesResponse>(OpenAPI, {
      method: "GET",
      url: `/api/v1/projects/${projectId}/files/branches`,
    })
  },

  /**
   * Get git diff for a specific file in story worktree
   */
  getFileDiff: async (
    storyId: string,
    filePath: string,
  ): Promise<FileDiffResponse> => {
    return __request<FileDiffResponse>(OpenAPI, {
      method: "GET",
      url: `/api/v1/stories/${storyId}/file-diff`,
      query: { file_path: filePath },
    })
  },
}

export interface FileDiffResponse {
  file_path: string
  diff: string
  has_changes: boolean
  base_branch?: string
  error?: string
}

export interface FolderChildrenResponse {
  path: string
  children: FileNode[]
}

// Types for branch operations
export interface Worktree {
  path: string
  branch?: string
  head?: string
  bare?: boolean
}

export interface BranchesResponse {
  current: string | null
  branches: string[]
  worktrees: Worktree[]
}

export const getFileDiff = async (
  projectId: string,
  filePath: string,
  worktree?: string,
): Promise<FileDiffResponse> => {
  return __request<FileDiffResponse>(OpenAPI, {
    method: "GET",
    url: `/api/v1/projects/${projectId}/files/file-diff`,
    query: { file_path: filePath, ...(worktree && { worktree }) },
  })
}
