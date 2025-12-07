export type Role = 'admin' | 'user'

export interface UserAdmin {
  id: string
  username: string | null
  full_name: string | null
  email: string
  role: Role
  is_active: boolean
  is_locked: boolean
  locked_until: string | null
  failed_login_attempts: number
  login_provider: string | null
  balance: number
  created_at: string
  updated_at: string
}

export interface UserAdminCreate {
  username?: string | null
  full_name?: string | null
  email: string
  password: string
  role?: Role
  is_active?: boolean
}

export interface UserAdminUpdate {
  username?: string | null
  full_name?: string | null
  email?: string
  password?: string
  role?: Role
  is_active?: boolean
}

export interface UsersAdminResponse {
  data: UserAdmin[]
  count: number
}

export interface UserStatsResponse {
  total_users: number
  active_users: number
  inactive_users: number
  locked_users: number
  admin_users: number
  regular_users: number
  users_with_oauth: number
}

export interface UserFilters {
  search?: string
  role?: string
  status?: string
  order_by?: string
  order_dir?: 'asc' | 'desc'
}

export interface BulkUserIds {
  user_ids: string[]
}
