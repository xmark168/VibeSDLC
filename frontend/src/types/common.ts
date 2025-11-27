// Common utility types

import type { JSX } from "react"

export interface ToastMessages {
  loading: string | JSX.Element
  success: string | JSX.Element
  error: string | JSX.Element
}

export type Theme = "dark" | "light" | "system"

export type ThemeProviderProps = {
  children: React.ReactNode
  defaultTheme?: Theme
  storageKey?: string
}

export type ThemeProviderState = {
  theme: Theme
  setTheme: (theme: Theme) => void
}
