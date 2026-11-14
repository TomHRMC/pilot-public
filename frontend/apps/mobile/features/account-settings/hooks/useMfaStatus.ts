/**
 * useMfaStatus — Mobile hook for GET /api/v1/users/me/mfa-status
 *
 * MOB-B10: MFA enrollment screen
 */
import { apiClient } from "@pilot/shared-api";
import { useQuery } from "@tanstack/react-query";
import type { MFAEnrollmentPath } from "@pilot/ui";

export const MFA_STATUS_QUERY_KEY = ["users", "me", "mfa-status"] as const;

interface MfaStatusResponse {
  enrolled_methods: MFAEnrollmentPath[];
  tenant_policy_required: boolean;
  grace_period_active: boolean;
  grace_ends_at: string | null;
  enforcement_activated: boolean;
}

export function useMfaStatus() {
  return useQuery({
    queryKey: MFA_STATUS_QUERY_KEY,
    queryFn: async () => {
      const res = await apiClient.get("/api/v1/users/me/mfa-status");
      return res.data as MfaStatusResponse;
    },
    staleTime: 30_000,
  });
}
