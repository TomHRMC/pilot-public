import { Platform } from "react-native";
/**
 * useOwnerPlanUsage — TanStack Query hook for tenant subscription / plan tier
 *
 * Location: apps/mobile/features/owner-tab/hooks/useOwnerPlanUsage.ts
 *
 * GET /api/v1/tenants/{tenantId}/subscription
 * tenantId sourced from useAuth().user.tenantId (PilotUser.tenantId — confirmed).
 *
 * UsageSummaryResponse schema (from openapi.json):
 *   { period_start, period_end, current_user_count, current_sms_segment_count }
 *
 * Fails silently if no tenantId available (PlanUsageSection returns null).
 * staleTime = 5 minutes — plan changes rarely.
 *
 * MOB-B5
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import { useAuth } from "@pilot/ui/auth";

export const OWNER_PLAN_USAGE_QUERY_KEY = (tenantId: string | null) =>
  ["owner-plan-usage", tenantId] as const;

// ─── Types (confirmed from openapi.json) ──────────────────────────────────────

export interface SubscriptionTierResponse {
  tier_id: string;
  tier_name: string;
  display_label: string;
  monthly_price_cents: number;
  is_trial: boolean;
  trial_duration_days: number | null;
  max_users: number;
  max_sms_segments_per_month: number | null;
  display_order: number;
  is_active: boolean;
}

export interface UsageSummaryResponse {
  period_start: string | null;
  period_end: string | null;
  current_user_count: number;
  current_sms_segment_count: number;
}

export interface TenantSubscriptionSummary {
  current_tier: SubscriptionTierResponse;
  trial_ends_at: string | null;
  stripe_customer_id: string | null;
  usage: UsageSummaryResponse | null;
  tier_override: Record<string, unknown> | null;
}

// ─── Hook ──────────────────────────────────────────────────────────────────────

export function useOwnerPlanUsage() {
  const { user } = useAuth();
  const tenantId = user?.tenantId ?? null; // PilotUser.tenantId — confirmed from types.ts
  const isMockAuth =
    Platform.OS === "web" && process.env.EXPO_PUBLIC_USE_MOCK_AUTH === "true";

  return useQuery({
    queryKey: OWNER_PLAN_USAGE_QUERY_KEY(tenantId),
    queryFn: async () => {
      if (!tenantId) throw new Error("No tenantId available");
      const res = await apiClient.get<TenantSubscriptionSummary>(
        `/api/v1/tenants/${tenantId}/subscription`,
      );
      return res.data;
    },
    staleTime: 5 * 60_000, // 5 minutes — plan info changes rarely
    refetchOnWindowFocus: false,
    retry: 0, // Fail silently if not implemented / no tenantId
    enabled: !isMockAuth && !!tenantId,
  });
}
