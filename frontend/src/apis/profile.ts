import { request as __request } from "@client/core/request"
import { OpenAPI } from "@/client"
import type { Profile, ProfileUpdate, AvatarUploadResponse, PasswordStatusResponse, PasswordChangeResponse } from "@/types/profile"

export async function getProfile(): Promise<Profile> {
  return __request<Profile>(OpenAPI, {
    method: "GET",
    url: "/api/v1/profile/me",
  })
}

export async function updateProfile(data: ProfileUpdate): Promise<Profile> {
  return __request<Profile>(OpenAPI, {
    method: "PATCH",
    url: "/api/v1/profile/me",
    body: data,
  })
}

export async function uploadAvatar(file: Blob): Promise<AvatarUploadResponse> {
  const formData = new FormData()
  formData.append("file", file, "avatar.jpg")

  const token = localStorage.getItem("access_token")
  
  const response = await fetch(`${OpenAPI.BASE}/api/v1/profile/avatar`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || "Failed to upload avatar")
  }

  return response.json()
}

export async function deleteAvatar(): Promise<{ message: string; avatar_url: string }> {
  return __request(OpenAPI, {
    method: "DELETE",
    url: "/api/v1/profile/avatar",
  })
}

export async function getPasswordStatus(): Promise<PasswordStatusResponse> {
  return __request<PasswordStatusResponse>(OpenAPI, {
    method: "GET",
    url: "/api/v1/profile/password-status",
  })
}

export async function changePassword(data: {
  current_password: string
  new_password: string
  confirm_password: string
}): Promise<PasswordChangeResponse> {
  return __request<PasswordChangeResponse>(OpenAPI, {
    method: "POST",
    url: "/api/v1/profile/change-password",
    body: data,
  })
}

export async function setPassword(data: {
  new_password: string
  confirm_password: string
}): Promise<PasswordChangeResponse> {
  return __request<PasswordChangeResponse>(OpenAPI, {
    method: "POST",
    url: "/api/v1/profile/set-password",
    body: data,
  })
}
