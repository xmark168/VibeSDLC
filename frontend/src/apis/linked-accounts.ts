import { request as __request } from "@client/core/request"
import { OpenAPI } from "@/client"
import type {
  LinkedAccountsResponse,
  UnlinkAccountRequest,
  UnlinkAccountResponse,
  OAuthProvider,
} from "@/types/linked-account"

export interface InitiateLinkResponse {
  auth_url: string
  provider: string
}

export async function getLinkedAccounts(): Promise<LinkedAccountsResponse> {
  return __request<LinkedAccountsResponse>(OpenAPI, {
    method: "GET",
    url: "/api/v1/account/linked",
  })
}

export async function unlinkAccount(
  data: UnlinkAccountRequest
): Promise<UnlinkAccountResponse> {
  return __request<UnlinkAccountResponse>(OpenAPI, {
    method: "POST",
    url: "/api/v1/account/unlink",
    body: data,
  })
}

export async function initiateLink(provider: OAuthProvider): Promise<InitiateLinkResponse> {
  return __request<InitiateLinkResponse>(OpenAPI, {
    method: "POST",
    url: `/api/v1/account/link/${provider}`,
  })
}
