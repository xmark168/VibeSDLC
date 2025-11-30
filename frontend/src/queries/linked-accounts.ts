import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  getLinkedAccounts,
  unlinkAccount,
  initiateLink,
} from "@/apis/linked-accounts"
import type { UnlinkAccountRequest, OAuthProvider } from "@/types/linked-account"

export const linkedAccountKeys = {
  all: ["linked-accounts"] as const,
  list: () => [...linkedAccountKeys.all, "list"] as const,
}

export function useLinkedAccounts() {
  return useQuery({
    queryKey: linkedAccountKeys.list(),
    queryFn: getLinkedAccounts,
  })
}

export function useUnlinkAccount() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: UnlinkAccountRequest) => unlinkAccount(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: linkedAccountKeys.list() })
    },
  })
}

export function useInitiateLink() {
  return useMutation({
    mutationFn: (provider: OAuthProvider) => initiateLink(provider),
    onSuccess: (data) => {
      // Redirect to OAuth provider
      window.location.href = data.auth_url
    },
  })
}
