import { request as __request } from "@client/core/request"
import { OpenAPI } from "@/client"
import type {
  TwoFactorSetupResponse,
  TwoFactorVerifySetupRequest,
  TwoFactorVerifySetupResponse,
  TwoFactorDisableRequest,
  TwoFactorDisableResponse,
  TwoFactorVerifyRequest,
  TwoFactorVerifyResponse,
  TwoFactorStatusResponse,
  TwoFactorBackupCodesResponse,
} from "@/types/two-factor"

export async function get2FAStatus(): Promise<TwoFactorStatusResponse> {
  return __request<TwoFactorStatusResponse>(OpenAPI, {
    method: "GET",
    url: "/api/v1/2fa/status",
  })
}

export async function setup2FA(): Promise<TwoFactorSetupResponse> {
  return __request<TwoFactorSetupResponse>(OpenAPI, {
    method: "POST",
    url: "/api/v1/2fa/setup",
  })
}

export async function verifySetup2FA(
  data: TwoFactorVerifySetupRequest
): Promise<TwoFactorVerifySetupResponse> {
  return __request<TwoFactorVerifySetupResponse>(OpenAPI, {
    method: "POST",
    url: "/api/v1/2fa/verify-setup",
    body: data,
  })
}

export async function disable2FA(
  data: TwoFactorDisableRequest
): Promise<TwoFactorDisableResponse> {
  return __request<TwoFactorDisableResponse>(OpenAPI, {
    method: "POST",
    url: "/api/v1/2fa/disable",
    body: data,
  })
}

export async function verify2FALogin(
  data: TwoFactorVerifyRequest
): Promise<TwoFactorVerifyResponse> {
  return __request<TwoFactorVerifyResponse>(OpenAPI, {
    method: "POST",
    url: "/api/v1/2fa/verify",
    body: data,
  })
}

export async function regenerateBackupCodes(): Promise<TwoFactorBackupCodesResponse> {
  return __request<TwoFactorBackupCodesResponse>(OpenAPI, {
    method: "POST",
    url: "/api/v1/2fa/backup-codes",
  })
}
