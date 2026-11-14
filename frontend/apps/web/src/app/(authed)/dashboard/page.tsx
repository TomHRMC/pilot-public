"use client";

/**
 * Dashboard page — web
 *
 * Location: apps/web/src/app/(authed)/dashboard/page.tsx
 *
 * Wires together:
 *  - TrialExpiryBanner (FE-B13) — shown when tenant is on trial ≤7 days
 *  - OnboardingChecklistWidget (FE-B13) — setup checklist; disappears when done/dismissed
 *  - RecentCustomerMessagesWidget (FE-B10) — last 10 inbound/outbound SMS threads
 *
 * Layout shell (sidebar + auth) is provided by (authed)/layout.tsx.
 */

import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import { useAuth, RoleGate } from "@pilot/ui";
import { useTrialStatus } from "@/features/onboarding/hooks/useTrialStatus";
import { useOnboardingChecklist } from "@/features/onboarding/hooks/useOnboardingChecklist";
import { TrialExpiryBanner } from "@/features/onboarding/components/TrialExpiryBanner";
import { OnboardingChecklistWidget } from "@/features/onboarding/components/OnboardingChecklistWidget";
import { RecentCustomerMessagesWidget } from "@/features/dashboard/components/RecentCustomerMessagesWidget";
import { ArSummaryWidget } from "@/features/dashboard/components/ArSummaryWidget";
import { AtRiskJobsWidget } from "@/features/dashboard/components/AtRiskJobsWidget";
import { PendingApprovalsWidget } from "@/features/dashboard/components/PendingApprovalsWidget";
import { CharterMemberBadge } from "@/features/dashboard/components/CharterMemberBadge";
import type { SignupStateResponse } from "@/features/signup/types";

export default function DashboardPage() {
  const router = useRouter();
  const { user } = useAuth();

  const tenantId = user?.tenantId ?? null;
  const tenant = user as
    | {
        tenant_id?: string;
        is_on_trial?: boolean;
        trial_ends_at?: string | null;
        trial_expired?: boolean;
      }
    | null
    | undefined;

  const trialStatus = useTrialStatus(tenant);
  const { data: checklistState } = useOnboardingChecklist(tenantId);

  // C-B5: Fetch charter fields (charter_member_number, free_period_ends_at,
  // requires_payment_method) from the signup state endpoint. These are not
  // in the /users/me/permissions response. The signup state endpoint returns
  // collected_data with these fields for step4_tier/step5_confirm/complete.
  const { data: signupState } = useQuery({
    queryKey: ["charter-signup-state", tenantId],
    queryFn: async () => {
      const res = await apiClient.get<SignupStateResponse>(
        `/api/v1/signup/${tenantId}/state`,
      );
      return res.data;
    },
    enabled: !!tenantId,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  const charterMemberNumber =
    signupState?.collected_data?.charter_member_number ?? null;
  const freePeriodEndsAt =
    signupState?.collected_data?.free_period_ends_at ?? null;
  const requiresPaymentMethod =
    signupState?.collected_data?.requires_payment_method ?? true;
  // Charter tier = requires_payment_method is false
  const tierName = requiresPaymentMethod === false ? "charter" : undefined;

  function handleUpgradeClick() {
    void router.push("/signup/plan");
  }

  return (
    <div className="flex flex-col h-full bg-neutral-50">
      {/* Trial expiry banner */}
      {trialStatus.showSoftGate && (
        <TrialExpiryBanner
          daysRemaining={trialStatus.daysRemaining}
          onUpgradeClick={handleUpgradeClick}
        />
      )}

      {/* Page header */}
      <header className="flex items-center justify-between px-6 py-4 bg-white border-b border-neutral-200">
        <div className="flex items-center gap-3">
          <h1 className="text-h1 text-neutral-900">Dashboard</h1>
          <RoleGate role="owner">
            {charterMemberNumber != null && (
              <CharterMemberBadge
                charterMemberNumber={charterMemberNumber}
                freePeriodEndsAt={freePeriodEndsAt}
              />
            )}
          </RoleGate>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 px-6 py-6 max-w-5xl w-full mx-auto space-y-6 overflow-auto">
        {/* Onboarding checklist — hidden once complete or dismissed */}
        {tenantId && checklistState && (
          <OnboardingChecklistWidget
            tenantId={tenantId}
            checklistState={checklistState}
            tierName={tierName}
          />
        )}

        {/* FE-B23: BI widgets — Pending Approvals + At-Risk Jobs (2-column row) */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <PendingApprovalsWidget className="w-full" />
          <AtRiskJobsWidget className="w-full" />
        </div>

        {/* Recent customer messages widget */}
        <RecentCustomerMessagesWidget className="w-full" />

        {/* AR aging widget — FE-B22 */}
        <ArSummaryWidget className="w-full" />
      </main>
    </div>
  );
}
