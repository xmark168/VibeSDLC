import type React from "react"

// Extend CSSProperties to include custom CSS variables
export interface ThemeVars extends React.CSSProperties {
  // AI theme variables
  "--ai-primary-color"?: string
  "--ai-background-color"?: string
  "--ai-text-color"?: string
  "--ai-text-dark"?: string
  "--ai-border-color"?: string
  "--ai-border-main"?: string
  "--ai-highlight-primary"?: string
  "--ai-highlight-header"?: string

  // OCI theme variables
  "--oci-gradient-light-gray-start"?: string
  "--oci-gradient-light-gray-end"?: string
  "--oci-border-color"?: string
  "--oci-text-color"?: string
  "--oci-primary"?: string
  "--oci-secondary"?: string
  "--oci-highlight-primary"?: string
  "--oci-button-bg"?: string
  "--oci-card-bg"?: string
  "--oci-card-hover"?: string

  // Preview theme variables
  "--preview-bg-color"?: string
  "--preview-text-color"?: string
  "--preview-border-color"?: string
  "--preview-accent-color"?: string

  // Agent theme variables
  "--agent-primary-color"?: string
  "--agent-secondary-color"?: string
  "--agent-bg-gradient-start"?: string
  "--agent-bg-gradient-end"?: string
  "--agent-text-primary"?: string
  "--agent-border-color"?: string

  // Deploy theme variables
  "--deploy-primary"?: string
  "--deploy-secondary"?: string
  "--deploy-success"?: string
  "--deploy-warning"?: string
  "--deploy-error"?: string
  "--deploy-bg"?: string
  "--deploy-border"?: string

  // Allow any other CSS custom properties
  [key: `--${string}`]: string | number | undefined
}
