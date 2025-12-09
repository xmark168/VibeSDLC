import { useMutation, useQuery, useQueryClient, useInfiniteQuery } from "@tanstack/react-query"
import type {
  CreateMessageBody,
  CreateMessageWithFileParams,
  FetchMessagesParams,
  UpdateMessageBody,
} from "@/apis/messages"
import { messagesApi } from "@/apis/messages"

const MESSAGES_PER_PAGE = 50

export function useMessages(params: FetchMessagesParams) {
  return useQuery({
    queryKey: ["messages", params],
    queryFn: () => messagesApi.list(params),
    enabled: !!params.project_id,
    refetchOnWindowFocus: false, // Disable - chat uses WebSocket for real-time updates
  })
}

/**
 * Infinite scroll hook for loading messages in pages (REVERSE order for chat)
 * - Uses order=desc to get newest messages first from API
 * - Initial load: skip=0, limit=50, order=desc → newest 50 messages
 * - Scroll up: skip=50, limit=50, order=desc → next older 50 messages
 */
export function useInfiniteMessages(projectId: string) {
  return useInfiniteQuery({
    queryKey: ["messages-infinite", projectId],
    queryFn: async ({ pageParam = 0 }) => {
      const result = await messagesApi.list({
        project_id: projectId,
        skip: pageParam,
        limit: MESSAGES_PER_PAGE,
        order: 'desc',  // Newest first from API
      })
      
      return {
        messages: result.data,
        totalCount: result.count,
        currentSkip: pageParam,
      }
    },
    initialPageParam: 0,
    getNextPageParam: (lastPage, allPages) => {
      // Calculate total messages loaded so far
      const totalLoaded = allPages.reduce((acc, page) => acc + page.messages.length, 0)
      
      // If we've loaded all messages, no more pages
      if (totalLoaded >= lastPage.totalCount) {
        return undefined
      }
      
      // Return next skip value to load older messages
      return totalLoaded
    },
    enabled: !!projectId,
    refetchOnWindowFocus: false,
  })
}

export function useCreateMessage() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (body: CreateMessageBody) => messagesApi.create(body),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["messages", { project_id: variables.project_id }],
      })
    },
  })
}

export function useCreateMessageWithFile() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (params: CreateMessageWithFileParams) => messagesApi.createWithFile(params),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["messages", { project_id: variables.project_id }],
      })
    },
  })
}

export function useUpdateMessage() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: UpdateMessageBody }) =>
      messagesApi.update(id, body),
    onSuccess: (data) => {
      queryClient.invalidateQueries({
        queryKey: ["messages", { project_id: data.project_id }],
      })
    },
  })
}

export function useDeleteMessage() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => messagesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["messages"] })
    },
  })
}

export function useDeleteMessagesByProject() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (project_id: string) => messagesApi.deleteByProject(project_id),
    onSuccess: (_, project_id) => {
      queryClient.invalidateQueries({
        queryKey: ["messages", { project_id }],
      })
    },
  })
}
