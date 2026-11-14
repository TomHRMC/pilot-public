/**
 * useMfaStatus — BETA-B4
 *
 * Location: apps/web/src/features/account-settings/hooks/useMfaStatus.ts
 *
 * Fetches current MFA enrollment state for the logged-in user.
 * Used by the My Account > Security index page to show enrolled method count.
 *
 * Endpoint: GET /api/v1/users/me/mfa-status
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export interface MfaStatusResponse {
  enrolled_methods: Array<{ method: string; enrolled_at: string }>;
  method_count: number;
  totp_enabled: boolean;
  sms_enabled: boolean;
  email_enabled: boolean;
  recovery_codes_available: boolean;
}

export function useMfaStatus() {
  return useQuery({
    queryKey: ["mfa-status"],
    queryFn: async (): Promise<MfaStatusResponse> => {
      const res = await apiClient.get<MfaStatusResponse>(
        "/api/v1/users/me/mfa-status",
      );
      return res.data;
    },
    staleTime: 60_000,
  });
}
