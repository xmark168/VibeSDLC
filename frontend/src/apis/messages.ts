import { OpenAPI } from "@client"
import { request as __request } from "@client/core/request"
import type {
  AuthorType,
  Message,
  MessagesPage,
  FetchMessagesParams,
  CreateMessageBody,
  UpdateMessageBody,
} from "@/types"

// Re-export types for convenience
export type { FetchMessagesParams, CreateMessageBody, UpdateMessageBody }

export interface CreateMessageWithFileParams {
  project_id: string
  content: string
  file?: File
}

export const messagesApi = {
  list: async (params: FetchMessagesParams): Promise<MessagesPage> => {
    return __request<MessagesPage>(OpenAPI, {
      method: "GET",
      url: "/api/v1/messages/",
      query: {
        project_id: params.project_id,
        skip: params.skip ?? 0,
        limit: params.limit ?? 100,
        order: params.order ?? 'asc',
      },
    })
  },
  create: async (body: CreateMessageBody): Promise<Message> => {
    return __request<Message>(OpenAPI, {
      method: "POST",
      url: "/api/v1/messages/",
      body,
    })
  },
  createWithFile: async (params: CreateMessageWithFileParams): Promise<Message> => {
    const formData = new FormData()
    formData.append("project_id", params.project_id)
    formData.append("content", params.content)
    if (params.file) {
      formData.append("file", params.file)
    }
    return __request<Message>(OpenAPI, {
      method: "POST",
      url: "/api/v1/messages/with-file",
      body: formData,
    })
  },
  update: async (id: string, body: UpdateMessageBody): Promise<Message> => {
    return __request<Message>(OpenAPI, {
      method: "PATCH",
      url: `/api/v1/messages/${id}`,
      body,
    })
  },
  delete: async (id: string): Promise<void> => {
    return __request<void>(OpenAPI, {
      method: "DELETE",
      url: `/api/v1/messages/${id}`,
    })
  },
  deleteByProject: async (project_id: string): Promise<{ message: string }> => {
    return __request<{ message: string }>(OpenAPI, {
      method: "DELETE",
      url: `/api/v1/messages/by-project/${project_id}`,
    })
  },
  getAttachmentDownloadUrl: (messageId: string, attachmentIndex: number = 0): string => {
    const baseUrl = OpenAPI.BASE || ''
    return `${baseUrl}/api/v1/messages/${messageId}/attachments/${attachmentIndex}/download`
  },
  downloadAttachment: async (messageId: string, filename: string, attachmentIndex: number = 0): Promise<void> => {
    const url = `/api/v1/messages/${messageId}/attachments/${attachmentIndex}/download`
    // OpenAPI.TOKEN is an async function, need to call it
    const token = typeof OpenAPI.TOKEN === 'function' ? await OpenAPI.TOKEN() : OpenAPI.TOKEN
    const response = await fetch(`${OpenAPI.BASE || ''}${url}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    })
    
    if (!response.ok) {
      throw new Error(`Download failed: ${response.statusText}`)
    }
    
    const blob = await response.blob()
    const blobUrl = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = blobUrl
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(blobUrl)
  },
}
