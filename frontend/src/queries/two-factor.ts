import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  get2FAStatus,
  setup2FA,
  verifySetup2FA,
  disable2FA,
  verify2FALogin,
  regenerateBackupCodes,
} from "@/apis/two-factor";
import type {
  TwoFactorVerifySetupRequest,
  TwoFactorDisableRequest,
  TwoFactorVerifyRequest,
} from "@/types/two-factor";

export const twoFactorKeys = {
  all: ["two-factor"] as const,
  status: () => [...twoFactorKeys.all, "status"] as const,
};

export function use2FAStatus() {
  return useQuery({
    queryKey: twoFactorKeys.status(),
    queryFn: get2FAStatus,
  });
}

export function useSetup2FA() {
  return useMutation({
    mutationFn: setup2FA,
  });
}

export function useVerifySetup2FA() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: TwoFactorVerifySetupRequest) => verifySetup2FA(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: twoFactorKeys.status() });
    },
  });
}

export function useDisable2FA() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: TwoFactorDisableRequest) => disable2FA(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: twoFactorKeys.status() });
    },
  });
}

export function useVerify2FALogin() {
  return useMutation({
    mutationFn: (data: TwoFactorVerifyRequest) => verify2FALogin(data),
  });
}

export function useRegenerateBackupCodes() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: regenerateBackupCodes,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: twoFactorKeys.status() });
    },
  });
}
