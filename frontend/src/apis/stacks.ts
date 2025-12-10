import { request as __request } from "@client/core/request"
import { OpenAPI } from "@/client"
import type {
  TechStack,
  TechStackCreate,
  TechStackUpdate,
  TechStacksResponse,
  FileNode,
  FileContent,
} from "@/types/stack"

export const stacksApi = {
  // CRUD Operations
  listStacks: async (params?: {
    skip?: number
    limit?: number
    search?: string
    is_active?: boolean
  }): Promise<TechStacksResponse> => {
    return __request<TechStacksResponse>(OpenAPI, {
      method: "GET",
      url: "/api/v1/tech-stacks",
      query: params,
    })
  },

  getStack: async (stackId: string): Promise<TechStack> => {
    return __request<TechStack>(OpenAPI, {
      method: "GET",
      url: `/api/v1/tech-stacks/${stackId}`,
    })
  },

  getStackByCode: async (code: string): Promise<TechStack> => {
    return __request<TechStack>(OpenAPI, {
      method: "GET",
      url: `/api/v1/tech-stacks/by-code/${code}`,
    })
  },

  createStack: async (data: TechStackCreate): Promise<TechStack> => {
    return __request<TechStack>(OpenAPI, {
      method: "POST",
      url: "/api/v1/tech-stacks",
      body: data,
    })
  },

  updateStack: async (stackId: string, data: TechStackUpdate): Promise<TechStack> => {
    return __request<TechStack>(OpenAPI, {
      method: "PUT",
      url: `/api/v1/tech-stacks/${stackId}`,
      body: data,
    })
  },

  deleteStack: async (stackId: string, deleteFiles: boolean = false): Promise<void> => {
    return __request<void>(OpenAPI, {
      method: "DELETE",
      url: `/api/v1/tech-stacks/${stackId}`,
      query: { delete_files: deleteFiles },
    })
  },

  getAvailableSkills: async (): Promise<{ skills: string[] }> => {
    return __request<{ skills: string[] }>(OpenAPI, {
      method: "GET",
      url: "/api/v1/tech-stacks/available-skills",
    })
  },

  // Skill File Operations
  getSkillTree: async (code: string): Promise<FileNode> => {
    return __request<FileNode>(OpenAPI, {
      method: "GET",
      url: `/api/v1/tech-stacks/${code}/skills/tree`,
    })
  },

  readSkillFile: async (code: string, path: string): Promise<FileContent> => {
    return __request<FileContent>(OpenAPI, {
      method: "GET",
      url: `/api/v1/tech-stacks/${code}/skills/file`,
      query: { path },
    })
  },

  createSkillFile: async (code: string, path: string, content: string = ""): Promise<void> => {
    return __request<void>(OpenAPI, {
      method: "POST",
      url: `/api/v1/tech-stacks/${code}/skills/file`,
      body: { path, content },
    })
  },

  updateSkillFile: async (code: string, path: string, content: string): Promise<void> => {
    return __request<void>(OpenAPI, {
      method: "PUT",
      url: `/api/v1/tech-stacks/${code}/skills/file`,
      body: { path, content },
    })
  },

  deleteSkillFile: async (code: string, path: string): Promise<void> => {
    return __request<void>(OpenAPI, {
      method: "DELETE",
      url: `/api/v1/tech-stacks/${code}/skills/file`,
      query: { path },
    })
  },

  createSkillFolder: async (code: string, path: string): Promise<void> => {
    return __request<void>(OpenAPI, {
      method: "POST",
      url: `/api/v1/tech-stacks/${code}/skills/folder`,
      body: { path },
    })
  },

  deleteSkillFolder: async (code: string, path: string): Promise<void> => {
    return __request<void>(OpenAPI, {
      method: "DELETE",
      url: `/api/v1/tech-stacks/${code}/skills/folder`,
      query: { path },
    })
  },

  // Boilerplate File Operations
  getBoilerplateTree: async (code: string): Promise<FileNode> => {
    return __request<FileNode>(OpenAPI, {
      method: "GET",
      url: `/api/v1/tech-stacks/${code}/boilerplate/tree`,
    })
  },

  readBoilerplateFile: async (code: string, path: string): Promise<FileContent> => {
    return __request<FileContent>(OpenAPI, {
      method: "GET",
      url: `/api/v1/tech-stacks/${code}/boilerplate/file`,
      query: { path },
    })
  },

  createBoilerplateFile: async (code: string, path: string, content: string = ""): Promise<void> => {
    return __request<void>(OpenAPI, {
      method: "POST",
      url: `/api/v1/tech-stacks/${code}/boilerplate/file`,
      body: { path, content },
    })
  },

  updateBoilerplateFile: async (code: string, path: string, content: string): Promise<void> => {
    return __request<void>(OpenAPI, {
      method: "PUT",
      url: `/api/v1/tech-stacks/${code}/boilerplate/file`,
      body: { path, content },
    })
  },

  deleteBoilerplateFile: async (code: string, path: string): Promise<void> => {
    return __request<void>(OpenAPI, {
      method: "DELETE",
      url: `/api/v1/tech-stacks/${code}/boilerplate/file`,
      query: { path },
    })
  },

  createBoilerplateFolder: async (code: string, path: string): Promise<void> => {
    return __request<void>(OpenAPI, {
      method: "POST",
      url: `/api/v1/tech-stacks/${code}/boilerplate/folder`,
      body: { path },
    })
  },

  deleteBoilerplateFolder: async (code: string, path: string): Promise<void> => {
    return __request<void>(OpenAPI, {
      method: "DELETE",
      url: `/api/v1/tech-stacks/${code}/boilerplate/folder`,
      query: { path },
    })
  },

  uploadBoilerplateFolder: async (
    code: string,
    files: File[],
    paths: string[],
    clearExisting: boolean = false
  ): Promise<{ message: string; uploaded: number; skipped: number }> => {
    const formData = new FormData()
    files.forEach((file) => {
      formData.append("files", file)
    })

    const queryParams = new URLSearchParams()
    paths.forEach((p) => queryParams.append("paths", p))
    queryParams.append("clear_existing", String(clearExisting))

    const response = await fetch(
      `${OpenAPI.BASE}/api/v1/tech-stacks/${code}/boilerplate/upload?${queryParams.toString()}`,
      {
        method: "POST",
        body: formData,
        headers: {
          Authorization: `Bearer ${typeof OpenAPI.TOKEN === "function" ? await OpenAPI.TOKEN({} as any) : OpenAPI.TOKEN}`,
        },
      }
    )

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || "Upload failed")
    }

    return response.json()
  },
}
