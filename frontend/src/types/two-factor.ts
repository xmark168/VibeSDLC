export interface TwoFactorSetupResponse {
  secret: string;
  qr_code_uri: string;
  message: string;
}

export interface TwoFactorVerifySetupRequest {
  code: string;
}

export interface TwoFactorVerifySetupResponse {
  message: string;
  backup_codes: string[];
}

export interface TwoFactorDisableRequest {
  password: string;
  code: string;
}

export interface TwoFactorDisableResponse {
  message: string;
}

export interface TwoFactorVerifyRequest {
  temp_token: string;
  code: string;
}

export interface TwoFactorVerifyResponse {
  user_id: string;
  access_token: string;
  refresh_token: string;
}

export interface TwoFactorStatusResponse {
  enabled: boolean;
  has_backup_codes: boolean;
}

export interface TwoFactorBackupCodesResponse {
  backup_codes: string[];
  message: string;
}

export interface LoginRequires2FAResponse {
  requires_2fa: boolean;
  temp_token: string;
  message: string;
}

export interface LoginResponse {
  user_id: string;
  access_token: string;
  refresh_token: string;
}

export type LoginResult = LoginResponse | LoginRequires2FAResponse;

export function isLoginRequires2FA(response: LoginResult): response is LoginRequires2FAResponse {
  return 'requires_2fa' in response && response.requires_2fa === true;
}
