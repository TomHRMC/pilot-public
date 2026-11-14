/**
 * useTenantMfaPolicy — BETA-B4 / STEP 2
 *
 * Location: apps/web/src/features/settings/hooks/useTenantMfaPolicy.ts
 *
 * Manages the tenant-level MFA required policy.
 * GET: /api/v1/settings/tenant/mfa-required (BETA-B4-BE-03 — covered by MSW until BE ships)
 * PUT: /api/v1/settings/tenant/mfa-required
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export interface TenantMfaPolicy {
  tenantMfaRequired: boolean;
  gracePeriodStartsAt: string | null;
}

interface TenantMfaPolicyRaw {
  tenant_mfa_required: boolean;
  grace_period_starts_at: string | null;
}

const QUERY_KEY = ["tenant-mfa-policy"] as const;

export function useTenantMfaPolicy() {
  const qc = useQueryClient();

  const query = useQuery({
    queryKey: QUERY_KEY,
    queryFn: async (): Promise<TenantMfaPolicy> => {
      // GET endpoint added by BETA-B4-BE-03; MSW handler covers test env
      const res = await apiClient.get<TenantMfaPolicyRaw>(
        "/api/v1/settings/tenant/mfa-required",
      );
      return {
        tenantMfaRequired: res.data.tenant_mfa_required,
        gracePeriodStartsAt: res.data.grace_period_starts_at,
      };
    },
    staleTime: 60_000,
  });

  const mutation = useMutation({
    mutationFn: async (required: boolean): Promise<TenantMfaPolicy> => {
      const res = await apiClient.put<TenantMfaPolicyRaw>(
        "/api/v1/settings/tenant/mfa-required",
        { tenant_mfa_required: required },
      );
      return {
        tenantMfaRequired: res.data.tenant_mfa_required,
        gracePeriodStartsAt: res.data.grace_period_starts_at,
      };
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: QUERY_KEY });
    },
  });

  return {
    policy: query.data ?? null,
    isLoading: query.isLoading,
    isError: query.isError,
    setMfaRequired: async (required: boolean) => {
      await mutation.mutateAsync(required);
    },
    isUpdating: mutation.isPending,
  };
}
