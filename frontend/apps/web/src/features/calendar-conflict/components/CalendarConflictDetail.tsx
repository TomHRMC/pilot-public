/**
 * CalendarConflictDetail — page-level shell for the conflict detail view
 *
 * Location: apps/web/src/features/calendar-conflict/components/CalendarConflictDetail.tsx
 *
 * Composes:
 *   - <IntegrationConflictResolver integration="calendar">
 *   - <StalenessDialog> from useResolveCalendarConflict
 *   - breadcrumb / back nav
 *   - URL reason banners (?reason=voice_staleness, ?reason=voice_deletion_redirect)
 *
 * Rule 7: Web page does NOT render VoiceConfirmTurn (mobile-only component).
 * Pattern ref: design doc batch-fe-b8-design.md §D.2, §E.1, §E.2, §E.5, §E.8
 */

"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  LoadingState,
  ErrorState,
  IntegrationConflictResolver,
} from "@pilot/ui";
import type { CalendarResolution } from "@pilot/ui";
import { useCalendarConflictDetail } from "../hooks/useCalendarConflictDetail";
import { useResolveCalendarConflict } from "../hooks/useResolveCalendarConflict";

interface CalendarConflictDetailProps {
  conflictId: string;
  /** URL reason param — drives contextual banners */
  reason?: string | null;
  /** Days until auto-expiry from tenant settings */
  autoExpireDays?: number | null;
}

export function CalendarConflictDetail({
  conflictId,
  reason,
  autoExpireDays,
}: CalendarConflictDetailProps) {
  const router = useRouter();

  const {
    data: conflict,
    isLoading,
    error,
  } = useCalendarConflictDetail(conflictId);

  const {
    mutate: resolveConflict,
    StalenessDialog,
    mutation: resolveMutation,
  } = useResolveCalendarConflict(conflictId);

  const isResolving = resolveMutation.status === "pending";

  const handleResolve = (resolution: string) => {
    if (!conflict) return;

    resolveConflict({
      conflictId,
      resolution: resolution as CalendarResolution,
      expected_pilot_modified_at: conflict.pilotModifiedAt,
      expected_external_modified_at: conflict.externalModifiedAt,
    });

    // On success, navigate back (handled by mutation onSuccess → query invalidation → page refetch)
    // The router.push is done after mutation completes
  };

  const handleResolveLater = () => {
    router.push("/settings/integrations/calendar#conflicts");
  };

  const [nowMs] = useState(() => Date.now());

  // Compute days until expiry if autoExpireDays is set
  let daysUntilExpiry: number | null = null;
  if (autoExpireDays != null && conflict) {
    const detectedMs = new Date(conflict.detectedAt).getTime();
    const expiresMs = detectedMs + autoExpireDays * 24 * 60 * 60 * 1000;
    daysUntilExpiry = Math.ceil((expiresMs - nowMs) / (24 * 60 * 60 * 1000));
  }

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <nav
        aria-label="Breadcrumb"
        className="flex items-center gap-2 text-caption text-neutral-600"
      >
        <Link
          href="/settings/integrations/calendar#conflicts"
          className="hover:text-neutral-900 focus:outline-none focus:ring-1 focus:ring-brand-600 rounded"
        >
          Calendar Sync
        </Link>
        <span aria-hidden="true">›</span>
        <span className="text-neutral-900">Conflict Detail</span>
      </nav>

      {/* Reason-based contextual banners */}
      {reason === "voice_staleness" && (
        <div
          className="flex items-start gap-3 rounded-md border border-alert-200 bg-alert-50 px-4 py-3"
          role="alert"
          data-testid="voice-staleness-banner"
        >
          <p className="text-caption text-alert-700">
            Your voice resolution was cancelled — the conflict changed. Review
            the updated diff below.
          </p>
        </div>
      )}

      {reason === "voice_deletion_redirect" && (
        <div
          className="flex items-start gap-3 rounded-md border border-brand-200 bg-brand-50 px-4 py-3"
          role="status"
          data-testid="voice-deletion-redirect-banner"
        >
          <p className="text-caption text-brand-700">
            Your voice session routed here — please choose how to handle this
            deletion.
          </p>
        </div>
      )}

      {/* Loading state */}
      {isLoading && (
        <LoadingState type="inline" testID="conflict-detail-loading" />
      )}

      {/* Error state */}
      {error && !isLoading && (
        <ErrorState type="network" testID="conflict-detail-error" />
      )}

      {/* Resolved conflict — read-only view */}
      {conflict?.resolution && (
        <div
          className="flex items-start gap-3 rounded-md border border-brand-200 bg-brand-50 px-4 py-3"
          role="status"
          data-testid="conflict-resolved-banner"
        >
          <p className="text-caption text-brand-700">
            This conflict was resolved on{" "}
            {conflict.resolvedAt
              ? new Date(conflict.resolvedAt).toLocaleDateString()
              : "—"}{" "}
            {conflict.resolvedByUserId
              ? `by user ${conflict.resolvedByUserId}`
              : ""}
            . Viewing the final state.
          </p>
        </div>
      )}

      {/* Main resolver */}
      {conflict && (
        <>
          <IntegrationConflictResolver
            integration="calendar"
            conflict={conflict}
            onResolve={handleResolve}
            isResolving={isResolving || !!conflict.resolution}
            onResolveLater={handleResolveLater}
            providerDisplayName={conflict.providerDisplayName}
            daysUntilExpiry={daysUntilExpiry}
            testID="calendar-conflict-resolver"
          />
          <StalenessDialog />
        </>
      )}
    </div>
  );
}
