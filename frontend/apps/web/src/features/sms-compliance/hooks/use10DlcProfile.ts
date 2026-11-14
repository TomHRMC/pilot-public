"use client";

/**
 * use10DlcProfile — GET /api/v1/settings/10dlc-profile
 *
 * Location: apps/web/src/features/sms-compliance/hooks/use10DlcProfile.ts
 *
 * DLC-1: Fetches the tenant's 10DLC business profile.
 * Returns null (not throws) on 404 — profile not yet configured.
 *
 * RULE 2: uses apiClient, never raw fetch().
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export interface Tenant10DlcProfileData {
  tenant_id: string;
  legal_business_name: string | null;
  dba_name: string | null;
  ein_masked: string | null;
  hq_address_line1: string | null;
  hq_address_line2: string | null;
  hq_city: string | null;
  hq_state: string | null;
  hq_postal_code: string | null;
  hq_country: string;
  support_email: string | null;
  support_phone: string | null;
  website: string | null;
  stock_symbol: string | null;
  vertical: string | null;
  updated_at: string | null;
}

export const DLC_PROFILE_QUERY_KEY = ["settings", "10dlc-profile"] as const;

export function use10DlcProfile() {
  return useQuery<Tenant10DlcProfileData | null>({
    queryKey: DLC_PROFILE_QUERY_KEY,
    queryFn: async () => {
      try {
        const res = await apiClient.get<Tenant10DlcProfileData>(
          "/api/v1/settings/10dlc-profile",
        );
        return res.data;
      } catch (err: unknown) {
        // 404 means not yet configured — return null instead of throwing
        if (
          typeof err === "object" &&
          err !== null &&
          "response" in err &&
          (err as { response: { status: number } }).response?.status === 404
        ) {
          return null;
        }
        throw err;
      }
    },
    retry: false,
    staleTime: 60_000,
  });
}
