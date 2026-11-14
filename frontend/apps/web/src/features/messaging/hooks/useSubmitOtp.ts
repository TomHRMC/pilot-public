"use client";

/**
 * useSubmitOtp — POST /api/v1/tenants/{tenant_id}/messaging/otp
 *
 * Location: apps/web/src/features/messaging/hooks/useSubmitOtp.ts
 *
 * C-B9: Submits the sole-proprietor OTP code. Only valid when status is
 * awaiting_otp. On success, transitions to brand_verified.
 *
 * RULE 2: uses apiClient, never raw fetch().
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import { useAuth } from "@pilot/ui/auth";
import type { components } from "@pilot/shared-types";
import { PROVISIONING_STATUS_QUERY_KEY } from "./useProvisioningStatus";

type OtpRequest = components["schemas"]["OtpRequest"];
type OtpResponse = components["schemas"]["OtpResponse"];

export function useSubmitOtp() {
  const { user } = useAuth();
  const tenantId = user?.tenantId;
  const queryClient = useQueryClient();

  return useMutation<OtpResponse, unknown, OtpRequest>({
    mutationFn: async (payload) => {
      if (!tenantId) throw new Error("No tenant ID");
      const res = await apiClient.post<OtpResponse>(
        `/api/v1/tenants/${tenantId}/messaging/otp`,
        payload,
      );
      return res.data;
    },
    onSettled: () => {
      void queryClient.invalidateQueries({
        queryKey: PROVISIONING_STATUS_QUERY_KEY,
      });
    },
  });
}
