export interface Profile {
  id: string
  email: string
  full_name: string | null
  avatar_url: string | null
  login_provider: string | null
}

export interface ProfileUpdate {
  full_name?: string
}

export interface AvatarUploadResponse {
  avatar_url: string
  message: string
}
