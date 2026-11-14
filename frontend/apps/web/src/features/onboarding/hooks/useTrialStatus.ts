/**
 * useTrialStatus — Reads trial state from auth context
 *
 * Location: apps/web/src/features/onboarding/hooks/useTrialStatus.ts
 *
 * Design doc Section D.4: reads tenant.trial_* from auth context.
 * Returns { isOnTrial, daysRemaining, isExpired, showSoftGate }.
 */

"use client";

interface TenantTrialFields {
  is_on_trial?: boolean;
  trial_ends_at?: string | null;
  trial_expired?: boolean;
}

/**
 * useTrialStatus
 *
 * @param tenant - Tenant object from auth context (GET /api/v1/auth/me response)
 */
export function useTrialStatus(tenant: TenantTrialFields | null | undefined) {
  // Not using useMemo — Date.now() is "impure" per React compiler.
  // trial_ends_at changes rarely; straightforward computation on each render.
  if (!tenant || !tenant.is_on_trial) {
    return {
      isOnTrial: false,
      daysRemaining: 0,
      isExpired: false,
      showSoftGate: false,
    };
  }

  const isExpired = tenant.trial_expired === true;

  let daysRemaining = 0;
  if (tenant.trial_ends_at) {
    const endMs = new Date(tenant.trial_ends_at).getTime();
    const nowMs = Date.now();
    const diffMs = endMs - nowMs;
    daysRemaining = Math.max(0, Math.ceil(diffMs / (1000 * 60 * 60 * 24)));
  }

  // Soft gate: show banner at 7d, 3d, 1d remaining
  const showSoftGate = !isExpired && daysRemaining <= 7;

  return {
    isOnTrial: true,
    daysRemaining,
    isExpired,
    showSoftGate,
  };
}
