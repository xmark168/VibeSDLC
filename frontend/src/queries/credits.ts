import { useQuery } from "@tanstack/react-query"
import { creditsApi } from "@/apis/credits"

export const creditQueryKeys = {
  all: ["credits"] as const,
  activities: (params: { limit?: number; offset?: number; project_id?: string }) =>
    [...creditQueryKeys.all, "activities", params] as const,
}

export function useCreditActivities(params: { limit?: number; offset?: number; project_id?: string }) {
  return useQuery({
    queryKey: creditQueryKeys.activities(params),
    queryFn: () => creditsApi.getActivities(params),
  })
}
