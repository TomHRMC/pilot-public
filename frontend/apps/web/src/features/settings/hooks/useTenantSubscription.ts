/**
 * useTenantSubscription — BETA-B4 / STEP 4
 *
 * Location: apps/web/src/features/settings/hooks/useTenantSubscription.ts
 *
 * Fetches and manages tenant subscription / billing state.
 * GET  /api/v1/tenants/{tenant_id}/subscription
 * POST /api/v1/tenants/{tenant_id}/subscription/change-tier
 * POST /api/v1/tenants/{tenant_id}/subscription/upgrade-from-charter  (C-B12)
 *
 * PLP-FIX-5 (Issue 8): true-up to the post-Part-A payload. The BE now exposes
 * `plan_summary` (status, billing_interval, renews_at, free_period_ends_at),
 * `charter_eligible` (tenant column — retires the FE derivation), and `limits`
 * (ppfv-resolved metered-feature caps). The tier object gains `annual_price_cents`.
 * The phantom `max_users` / `max_sms_segments_per_month` fields are removed
 * (the BE never sent them — design-time finding 8a).
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient, getApiProblem, type ApiProblem } from "@pilot/shared-api";
import { useAuth } from "@pilot/ui/auth";

// ── Normalized (exported) types ───────────────────────────────────────────────

export interface SubscriptionTier {
  tierId: string;
  tierName: string;
  displayLabel: string;
  monthlyPriceCents: number;
  /** PLP-FIX-5: yearly total (e.g. 58800 = $588/yr). Null on charter (no annual price). */
  annualPriceCents: number;
  isTrial: boolean;
  trialDurationDays: number | null;
  /** Number of schedule lanes included with this tier (always sent by BE). */
  scheduleLanes: number;
}

export interface PlanSummary {
  statusCode: string | null;
  statusName: string | null;
  isBillingActive: boolean;
  billingInterval: "monthly" | "annual" | null;
  renewsAt: string | null;
  freePeriodEndsAt: string | null;
}

export interface PlanLimits {
  outboundSmsSegments: number | null;
  scheduleLanes: number | null;
  voiceAiMinutes: number | null;
}

export interface TenantSubscription {
  currentTier: SubscriptionTier;
  trialEndsAt: string | null;
  stripeCustomerId: string | null;
  usage: {
    currentUserCount?: number;
    currentSmsSegments?: number;
  };
  tierOverride: object | null;
  /** PLP-FIX-5: from tenant.charter_eligible (no longer derived client-side). */
  charterEligible: boolean;
  /** PLP-FIX-5: subscription-row status surfaced from the BE. */
  planSummary: PlanSummary;
  /** PLP-FIX-5: ppfv-resolved metered-feature caps. */
  limits: PlanLimits;
}

export type BillingInterval = "monthly" | "annual";

export interface UseTenantSubscriptionReturn {
  subscription: TenantSubscription | null;
  isLoading: boolean;
  isError: boolean;
  changeTier: (targetTierId: string) => Promise<void>;
  isChangingTier: boolean;
  upgradeFromCharter: (billingInterval: BillingInterval) => Promise<void>;
  isUpgradingFromCharter: boolean;
  upgradeError: string | null;
}

// ── Raw interfaces (match the post-Part-A backend payload) ────────────────────

interface SubscriptionTierRaw {
  tier_id: string;
  tier_name: string;
  display_label: string;
  monthly_price_cents: number;
  annual_price_cents: number;
  is_trial: boolean;
  trial_duration_days: number | null;
  schedule_lanes: number;
  display_order: number;
  is_active: boolean;
  free_period_days: number | null;
  requires_payment_method: boolean;
  signup_cap: number | null;
  price_locked: boolean;
}

interface PlanSummaryRaw {
  status_code: string | null;
  status_name: string | null;
  is_billing_active: boolean;
  billing_interval: string | null;
  renews_at: string | null;
  free_period_ends_at: string | null;
}

interface PlanLimitsRaw {
  outbound_sms_segments: number | null;
  schedule_lanes: number | null;
  voice_ai_minutes: number | null;
}

interface SubscriptionRaw {
  current_tier: SubscriptionTierRaw;
  trial_ends_at: string | null;
  stripe_customer_id: string | null;
  usage: {
    current_user_count?: number;
    current_sms_segments?: number;
  } | null;
  tier_override: object | null;
  plan_summary: PlanSummaryRaw;
  charter_eligible: boolean;
  limits: PlanLimitsRaw;
}

// ── Normalizers ───────────────────────────────────────────────────────────────

function normalizeTier(raw: SubscriptionTierRaw): SubscriptionTier {
  return {
    tierId: raw.tier_id,
    tierName: raw.tier_name,
    displayLabel: raw.display_label,
    monthlyPriceCents: raw.monthly_price_cents,
    annualPriceCents: raw.annual_price_cents,
    isTrial: raw.is_trial,
    trialDurationDays: raw.trial_duration_days,
    scheduleLanes: raw.schedule_lanes,
  };
}

function normalizePlanSummary(raw: PlanSummaryRaw): PlanSummary {
  const interval =
    raw.billing_interval === "monthly" || raw.billing_interval === "annual"
      ? raw.billing_interval
      : null;
  return {
    statusCode: raw.status_code,
    statusName: raw.status_name,
    isBillingActive: raw.is_billing_active,
    billingInterval: interval,
    renewsAt: raw.renews_at,
    freePeriodEndsAt: raw.free_period_ends_at,
  };
}

function normalizeLimits(raw: PlanLimitsRaw): PlanLimits {
  return {
    outboundSmsSegments: raw.outbound_sms_segments,
    scheduleLanes: raw.schedule_lanes,
    voiceAiMinutes: raw.voice_ai_minutes,
  };
}

function normalizeSubscription(raw: SubscriptionRaw): TenantSubscription {
  return {
    currentTier: normalizeTier(raw.current_tier),
    trialEndsAt: raw.trial_ends_at,
    stripeCustomerId: raw.stripe_customer_id,
    usage: {
      currentUserCount: raw.usage?.current_user_count,
      currentSmsSegments: raw.usage?.current_sms_segments,
    },
    tierOverride: raw.tier_override,
    charterEligible: raw.charter_eligible,
    planSummary: normalizePlanSummary(raw.plan_summary),
    limits: normalizeLimits(raw.limits),
  };
}

/**
 * Extract a human-readable error message from an API error via the shared
 * getApiProblem normalizer (TEST-UPLIFT-1B — replaces the local parser).
 * Falls back to a generic message.
 */
function extractUpgradeError(err: unknown): string {
  const problem: ApiProblem = getApiProblem(err);
  return (
    problem.detail ?? "Upgrade failed. Please try again or contact support."
  );
}

export function useTenantSubscription(): UseTenantSubscriptionReturn {
  const { user } = useAuth();
  const tenantId = user?.tenantId ?? "";
  const qc = useQueryClient();

  const queryKey = ["tenant-subscription", tenantId] as const;

  const { data, isLoading, isError } = useQuery({
    queryKey,
    queryFn: async (): Promise<TenantSubscription> => {
      const res = await apiClient.get<SubscriptionRaw>(
        `/api/v1/tenants/${tenantId}/subscription`,
      );
      return normalizeSubscription(res.data);
    },
    enabled: Boolean(tenantId),
    staleTime: 60_000,
  });

  const mutation = useMutation({
    mutationFn: async (targetTierId: string) => {
      await apiClient.post(
        `/api/v1/tenants/${tenantId}/subscription/change-tier`,
        { target_tier_id: targetTierId },
      );
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey });
    },
  });

  // C-B12 — Charter to Teams upgrade (permanent forfeiture of Charter rate)
  const upgradeMutation = useMutation({
    mutationFn: async (billingInterval: BillingInterval) => {
      await apiClient.post(
        `/api/v1/tenants/${tenantId}/subscription/upgrade-from-charter`,
        { billing_interval: billingInterval },
      );
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey });
    },
  });

  return {
    subscription: data ?? null,
    isLoading,
    isError,
    changeTier: async (targetTierId) => {
      await mutation.mutateAsync(targetTierId);
    },
    isChangingTier: mutation.isPending,
    upgradeFromCharter: async (billingInterval) => {
      await upgradeMutation.mutateAsync(billingInterval);
    },
    isUpgradingFromCharter: upgradeMutation.isPending,
    upgradeError: upgradeMutation.isError
      ? extractUpgradeError(upgradeMutation.error)
      : null,
  };
}
