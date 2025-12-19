import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { usersApi, type UserAdminCreate, type UserAdminUpdate } from "@/apis/users"
import { toast } from "@/lib/toast"

// Query Keys
export const userQueryKeys = {
  all: ["users"] as const,
  lists: () => [...userQueryKeys.all, "list"] as const,
  list: (filters?: Record<string, unknown>) => [...userQueryKeys.lists(), filters] as const,
  stats: () => [...userQueryKeys.all, "stats"] as const,
  detail: (userId: string) => [...userQueryKeys.all, "detail", userId] as const,
}

// Queries
export function useAdminUsers(
  params?: {
    skip?: number
    limit?: number
    search?: string
    role?: string
    status?: string
    order_by?: string
    order_dir?: 'asc' | 'desc'
  },
  options?: { enabled?: boolean }
) {
  return useQuery({
    queryKey: userQueryKeys.list(params),
    queryFn: () => usersApi.listUsers(params),
    enabled: options?.enabled ?? true,
    staleTime: 30000,
  })
}

export function useUserStats(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: userQueryKeys.stats(),
    queryFn: () => usersApi.getStats(),
    enabled: options?.enabled ?? true,
    staleTime: 30000,
  })
}

// Mutations
export function useCreateUser() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: UserAdminCreate) => usersApi.createUser(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: userQueryKeys.lists() })
      queryClient.invalidateQueries({ queryKey: userQueryKeys.stats() })
      toast.success("User created successfully")
    },
    onError: (error: any) => {
      const message = error?.body?.detail || error?.message || "Failed to create user"
      toast.error(message)
    },
  })
}

export function useUpdateUser() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ userId, data }: { userId: string; data: UserAdminUpdate }) =>
      usersApi.updateUser(userId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: userQueryKeys.lists() })
      queryClient.invalidateQueries({ queryKey: userQueryKeys.stats() })
      toast.success("User updated successfully")
    },
    onError: (error: any) => {
      const message = error?.body?.detail || error?.message || "Failed to update user"
      toast.error(message)
    },
  })
}

export function useDeleteUser() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (userId: string) => usersApi.deleteUser(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: userQueryKeys.all })
      toast.success("User deleted successfully")
    },
    onError: (error: any) => {
      const message = error?.body?.detail || error?.message || "Failed to delete user"
      toast.error(message)
    },
  })
}

export function useLockUser() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (userId: string) => usersApi.lockUser(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: userQueryKeys.lists() })
      queryClient.invalidateQueries({ queryKey: userQueryKeys.stats() })
      toast.success("User locked successfully")
    },
    onError: (error: any) => {
      const message = error?.body?.detail || error?.message || "Failed to lock user"
      toast.error(message)
    },
  })
}

export function useUnlockUser() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (userId: string) => usersApi.unlockUser(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: userQueryKeys.lists() })
      queryClient.invalidateQueries({ queryKey: userQueryKeys.stats() })
      toast.success("User unlocked successfully")
    },
    onError: (error: any) => {
      const message = error?.body?.detail || error?.message || "Failed to unlock user"
      toast.error(message)
    },
  })
}

export function useRevokeUserSessions() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (userId: string) => usersApi.revokeUserSessions(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: userQueryKeys.lists() })
      toast.success("All sessions revoked successfully")
    },
    onError: (error: any) => {
      const message = error?.body?.detail || error?.message || "Failed to revoke sessions"
      toast.error(message)
    },
  })
}

export function useBulkLockUsers() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (userIds: string[]) => usersApi.bulkLockUsers(userIds),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: userQueryKeys.all })
      toast.success(data.message)
    },
    onError: (error: any) => {
      const message = error?.body?.detail || error?.message || "Failed to lock users"
      toast.error(message)
    },
  })
}

export function useBulkUnlockUsers() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (userIds: string[]) => usersApi.bulkUnlockUsers(userIds),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: userQueryKeys.all })
      toast.success(data.message)
    },
    onError: (error: any) => {
      const message = error?.body?.detail || error?.message || "Failed to unlock users"
      toast.error(message)
    },
  })
}

export function useBulkDeleteUsers() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (userIds: string[]) => usersApi.bulkDeleteUsers(userIds),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: userQueryKeys.all })
      toast.success(data.message)
    },
    onError: (error: any) => {
      const message = error?.body?.detail || error?.message || "Failed to delete users"
      toast.error(message)
    },
  })
}
