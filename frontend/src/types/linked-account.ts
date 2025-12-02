export type OAuthProvider = "google" | "github" | "facebook"

export interface LinkedAccount {
  id: string
  provider: OAuthProvider
  provider_user_id: string
  provider_email: string
  created_at: string
}

export interface LinkedAccountsResponse {
  linked_accounts: LinkedAccount[]
  available_providers: string[]
}

export interface UnlinkAccountRequest {
  provider: OAuthProvider
  password?: string
}

export interface UnlinkAccountResponse {
  message: string
  remaining_providers: string[]
}
