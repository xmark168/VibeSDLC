import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { messagesApi } from '@/apis/messages'
import type { FetchMessagesParams, CreateMessageBody, UpdateMessageBody } from '@/apis/messages'

export function useMessages(params: FetchMessagesParams) {
  return useQuery({
    queryKey: ['messages', params],
    queryFn: () => messagesApi.list(params),
    enabled: !!params.project_id,
  })
}

export function useCreateMessage() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (body: CreateMessageBody) => messagesApi.create(body),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ 
        queryKey: ['messages', { project_id: variables.project_id }] 
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
        queryKey: ['messages', { project_id: data.project_id }] 
      })
    },
  })
}

export function useDeleteMessage() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (id: string) => messagesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['messages'] })
    },
  })
}

export function useDeleteMessagesByProject() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (project_id: string) => messagesApi.deleteByProject(project_id),
    onSuccess: (_, project_id) => {
      queryClient.invalidateQueries({ 
        queryKey: ['messages', { project_id }] 
      })
    },
  })
}


