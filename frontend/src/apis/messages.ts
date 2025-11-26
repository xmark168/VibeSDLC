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

export const messagesApi = {
  list: async (params: FetchMessagesParams): Promise<MessagesPage> => {
    return __request<MessagesPage>(OpenAPI, {
      method: "GET",
      url: "/api/v1/messages/",
      query: {
        project_id: params.project_id,
        skip: params.skip ?? 0,
        limit: params.limit ?? 100,
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
}
