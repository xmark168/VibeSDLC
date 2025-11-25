import { request as __request } from "@client/core/request"
import { OpenAPI } from "@/client"
import type {
  FileNode,
  FileTreeResponse,
  FileContentResponse,
  GitStatusResponse,
} from "@/types"

// Re-export types for convenience
export type { FileNode, FileTreeResponse, FileContentResponse, GitStatusResponse }

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
