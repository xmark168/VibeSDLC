import { create } from "zustand"
import type { UserPublic } from "@/client"

type AppStoreType = {
  user: UserPublic | undefined
  isLoading: boolean
  setUser: (user?: UserPublic | undefined) => void
  setIsLoading: (loading: boolean) => void
}

export const useAppStore = create<AppStoreType>((set, get) => ({
  user: undefined,
  isLoading: true,
  setUser: (user?: UserPublic | undefined) => {
    set({ user, isLoading: false })
    if (!user) {
      localStorage.removeItem("access_token")
    }
  },
  setIsLoading: (loading: boolean) => set({ isLoading: loading }),
  get isAuthenticated() {
    return !!get().user
  },
}))
