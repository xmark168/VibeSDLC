import { useQuery } from "@tanstack/react-query"
import { subscriptionApi } from "@/apis/subscription"

// Query Keys
export const subscriptionQueryKeys = {
  all: ["subscription"] as const,
  current: () => [...subscriptionQueryKeys.all, "current"] as const,
}

// Get current user's subscription and credit wallet
export function useCurrentSubscription() {
  return useQuery({
    queryKey: subscriptionQueryKeys.current(),
    queryFn: () => subscriptionApi.getCurrentSubscription(),
    staleTime: 60000, // Cache for 1 minute
  })
}
