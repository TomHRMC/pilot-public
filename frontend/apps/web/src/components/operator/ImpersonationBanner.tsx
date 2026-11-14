"use client";

/**
 * ImpersonationBanner — persistent banner while impersonation is active
 *
 * Location: apps/web/src/components/operator/ImpersonationBanner.tsx
 *
 * C-B15 Part B: Normal-flow shrink-0 bar (NOT position: fixed). Mounted as
 * the first child of the outer flex column in both the operator layout and
 * the (authed) tenant layout. Color-independent (EyeIcon + text, WCAG 1.4.1).
 *
 * On exit → useImpersonationEnd → on settle (success or failure):
 *   clearImpersonation() → window.location.assign('/operator/cohort')
 * (deliberate full page reload — hard rule, design §G Q2/Q3).
 *
 * RULE 5: zero hex codes. RULE 15: WCAG 2.2 AA (role=status, aria-live, ≥24px targets).
 */

import { useImpersonation, clearImpersonation } from "@pilot/shared-api";
import {
  EyeIcon,
  ArrowRightOnRectangleIcon,
} from "@heroicons/react/24/outline";
import { useImpersonationEnd } from "@/features/operator/hooks/useImpersonationEnd";

export function ImpersonationBanner() {
  const session = useImpersonation();
  const endMutation = useImpersonationEnd();

  if (!session) return null;

  const handleExit = async () => {
    try {
      await endMutation.mutateAsync({ tenantId: session.tenantId });
    } catch {
      // Defensive — clear regardless of network result (spec §8.4)
      if (process.env.NODE_ENV !== "production") {
        console.warn(
          "[ImpersonationBanner] end mutation failed — clearing anyway",
        );
      }
    }
    // Always clear + reload on settle (success or failure)
    clearImpersonation();
    window.location.assign("/operator/cohort");
  };

  const isInFlight = endMutation.isPending;

  return (
    <div
      className="h-10 bg-alert-50 border-b border-alert-200 flex items-center justify-between px-4 shrink-0 z-40"
      data-testid="impersonation-banner"
    >
      {/* Left — viewing as */}
      <div
        className="inline-flex items-center gap-2 text-sm font-medium text-alert-800"
        role="status"
        aria-live="polite"
      >
        <EyeIcon className="w-4 h-4" aria-hidden="true" />
        <span>
          Viewing as:{" "}
          <span className="font-semibold">{session.tenantName}</span>
        </span>
      </div>

      {/* Right — exit button */}
      <button
        type="button"
        onClick={handleExit}
        disabled={isInFlight}
        aria-label="Exit impersonation and return to operator cohort"
        className="inline-flex items-center gap-1.5 text-sm font-medium text-alert-700 hover:text-alert-900 rounded-md px-2 py-1 focus-visible:ring-2 focus-visible:ring-alert-500 disabled:text-alert-400 disabled:cursor-not-allowed"
        data-testid="impersonation-exit-button"
      >
        <ArrowRightOnRectangleIcon className="w-4 h-4" aria-hidden="true" />
        {isInFlight ? "Exiting…" : "Exit"}
      </button>
    </div>
  );
}
