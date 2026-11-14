"use client";

/**
 * useUpdate10DlcProfile — PUT /api/v1/settings/10dlc-profile
 *
 * Location: apps/web/src/features/sms-compliance/hooks/useUpdate10DlcProfile.ts
 *
 * DLC-1: Upserts the tenant's 10DLC business profile.
 * On success, invalidates the GET query so the form re-populates fresh data.
 *
 * RULE 2: uses apiClient, never raw fetch().
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import {
  DLC_PROFILE_QUERY_KEY,
  type Tenant10DlcProfileData,
} from "./use10DlcProfile";

export interface Update10DlcProfilePayload {
  legal_business_name: string;
  dba_name?: string | null;
  ein?: string | null;
  hq_address_line1?: string | null;
  hq_address_line2?: string | null;
  hq_city?: string | null;
  hq_state?: string | null;
  hq_postal_code?: string | null;
  hq_country?: string;
  support_email?: string | null;
  support_phone?: string | null;
  website?: string | null;
}

export function useUpdate10DlcProfile() {
  const queryClient = useQueryClient();

  return useMutation<
    Tenant10DlcProfileData,
    unknown,
    Update10DlcProfilePayload
  >({
    mutationFn: async (payload) => {
      const res = await apiClient.put<Tenant10DlcProfileData>(
        "/api/v1/settings/10dlc-profile",
        payload,
      );
      return res.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: DLC_PROFILE_QUERY_KEY });
    },
  });
}
