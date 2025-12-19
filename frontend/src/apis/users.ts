import { request as __request } from "@client/core/request"
import { OpenAPI } from "@/client"
import type {
  BulkUserIds,
  UserAdmin,
  UserAdminCreate,
  UserAdminUpdate,
  UserStatsResponse,
  UsersAdminResponse,
} from "@/types/user"

// Re-export types
export type {
  UserAdmin,
  UserAdminCreate,
  UserAdminUpdate,
  UsersAdminResponse,
  UserStatsResponse,
  BulkUserIds,
}

export const usersApi = {
  // List users with pagination and filters (admin)
  listUsers: async (params?: {
    skip?: number
    limit?: number
    search?: string
    role?: string
    status?: string
    order_by?: string
    order_dir?: "asc" | "desc"
  }): Promise<UsersAdminResponse> => {
    return __request<UsersAdminResponse>(OpenAPI, {
      method: "GET",
      url: "/api/v1/users/admin/list",
      query: {
        skip: params?.skip ?? 0,
        limit: params?.limit ?? 100,
        search: params?.search,
        role: params?.role,
        status: params?.status,
        order_by: params?.order_by ?? "created_at",
        order_dir: params?.order_dir ?? "desc",
      },
    })
  },

  // Get user statistics (admin)
  getStats: async (): Promise<UserStatsResponse> => {
    return __request<UserStatsResponse>(OpenAPI, {
      method: "GET",
      url: "/api/v1/users/admin/stats",
    })
  },

  // Create user (admin)
  createUser: async (body: UserAdminCreate): Promise<UserAdmin> => {
    return __request<UserAdmin>(OpenAPI, {
      method: "POST",
      url: "/api/v1/users/admin/create",
      body,
    })
  },

  // Update user (admin)
  updateUser: async (
    userId: string,
    body: UserAdminUpdate,
  ): Promise<UserAdmin> => {
    return __request<UserAdmin>(OpenAPI, {
      method: "PATCH",
      url: `/api/v1/users/admin/${userId}`,
      body,
    })
  },

  // Delete user (admin)
  deleteUser: async (userId: string): Promise<{ message: string }> => {
    return __request<{ message: string }>(OpenAPI, {
      method: "DELETE",
      url: `/api/v1/users/${userId}`,
    })
  },

  // Lock user (admin)
  lockUser: async (userId: string): Promise<{ message: string }> => {
    return __request<{ message: string }>(OpenAPI, {
      method: "POST",
      url: `/api/v1/users/admin/${userId}/lock`,
    })
  },

  // Unlock user (admin)
  unlockUser: async (userId: string): Promise<{ message: string }> => {
    return __request<{ message: string }>(OpenAPI, {
      method: "POST",
      url: `/api/v1/users/admin/${userId}/unlock`,
    })
  },

  // Revoke all sessions for user (admin)
  revokeUserSessions: async (userId: string): Promise<{ message: string }> => {
    return __request<{ message: string }>(OpenAPI, {
      method: "POST",
      url: `/api/v1/users/admin/${userId}/revoke-sessions`,
    })
  },

  // Bulk lock users (admin)
  bulkLockUsers: async (userIds: string[]): Promise<{ message: string }> => {
    return __request<{ message: string }>(OpenAPI, {
      method: "POST",
      url: "/api/v1/users/admin/bulk/lock",
      body: { user_ids: userIds } as BulkUserIds,
    })
  },

  // Bulk unlock users (admin)
  bulkUnlockUsers: async (userIds: string[]): Promise<{ message: string }> => {
    return __request<{ message: string }>(OpenAPI, {
      method: "POST",
      url: "/api/v1/users/admin/bulk/unlock",
      body: { user_ids: userIds } as BulkUserIds,
    })
  },

  // Bulk delete users (admin)
  bulkDeleteUsers: async (userIds: string[]): Promise<{ message: string }> => {
    return __request<{ message: string }>(OpenAPI, {
      method: "DELETE",
      url: "/api/v1/users/admin/bulk",
      body: { user_ids: userIds } as BulkUserIds,
    })
  },
}

// Utility functions
export function getRoleLabel(role: string): string {
  return role === "admin" ? "Admin" : "User"
}

export function getRoleVariant(
  role: string,
): "default" | "secondary" | "destructive" | "outline" {
  return role === "admin" ? "default" : "secondary"
}

export function getStatusLabel(user: UserAdmin): string {
  if (user.is_locked) return "Locked"
  if (!user.is_active) return "Inactive"
  return "Active"
}

export function getStatusVariant(
  user: UserAdmin,
): "default" | "secondary" | "destructive" | "outline" {
  if (user.is_locked) return "destructive"
  if (!user.is_active) return "secondary"
  return "default"
}
