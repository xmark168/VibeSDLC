import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { getProfile, updateProfile, uploadAvatar, deleteAvatar, getPasswordStatus, changePassword, setPassword } from "@/apis/profile"
import type { ProfileUpdate } from "@/types/profile"
import { isLoggedIn } from "@/hooks/useAuth"

export const profileKeys = {
  all: ["profile"] as const,
  me: () => [...profileKeys.all, "me"] as const,
  passwordStatus: () => [...profileKeys.all, "password-status"] as const,
}

export function useProfile() {
  return useQuery({
    queryKey: profileKeys.me(),
    queryFn: getProfile,
    enabled: isLoggedIn(), // Only fetch when user is logged in
    refetchOnWindowFocus: false, // Avoid unnecessary refetches
    refetchOnMount: false, // Avoid refetch on component remount
  })
}

export function useUpdateProfile() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: ProfileUpdate) => updateProfile(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: profileKeys.me() })
    },
  })
}

export function useUploadAvatar() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (file: Blob) => uploadAvatar(file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: profileKeys.me() })
    },
  })
}

export function useDeleteAvatar() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: deleteAvatar,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: profileKeys.me() })
    },
  })
}

export function usePasswordStatus() {
  return useQuery({
    queryKey: profileKeys.passwordStatus(),
    queryFn: getPasswordStatus,
    enabled: isLoggedIn(), // Only fetch when user is logged in
    refetchOnWindowFocus: false, // Avoid unnecessary refetches
  })
}

export function useChangePassword() {
  return useMutation({
    mutationFn: (data: { current_password: string; new_password: string; confirm_password: string }) =>
      changePassword(data),
  })
}

export function useSetPassword() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: { new_password: string; confirm_password: string }) => setPassword(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: profileKeys.passwordStatus() })
    },
  })
}
