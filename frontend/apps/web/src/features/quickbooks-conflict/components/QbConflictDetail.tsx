/**
 * QbConflictDetail — page shell for QB conflict resolution
 *
 * Location: apps/web/src/features/quickbooks-conflict/components/QbConflictDetail.tsx
 *
 * Established FE-B9.
 *   - Invoice: masterDirection='external' → QB on left; InvoiceFinancialDeltaCallout via slot
 *   - Quote: masterDirection='pilot' → Pilot on left
 *   - Customer/Expense: masterDirection='pilot' (tenant override in FE-B11)
 *   - Per-field picker available (supportsPerFieldResolution=true)
 *   - 409 auto-recovery: success toast + navigate to queue
 *   - Voice attempt: NO VoiceConfirmTurn; ?reason=voice_qb_blocked → NotificationBanner only (RULE 3)
 *
 * RULE 3: ZERO VoiceConfirmTurn imports or usage.
 * RULE 4: Server-side diff is canonical — use normalizeQbFieldDiffs in IntegrationConflictResolver.
 */

"use client";

import React, { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  IntegrationConflictResolver,
  InvoiceFinancialDeltaCallout,
} from "@pilot/ui";
import type {
  PerFieldSelection,
  QbConflictDetail as UiQbConflictDetail,
} from "@pilot/ui";
import { useQbConflictDetail } from "../hooks/useQbConflictDetail";
import { useResolveQbConflict } from "../hooks/useResolveQbConflict";
import type { QbResolution } from "../types";

interface QbConflictDetailProps {
  conflictId: string;
  testID?: string;
}

function InlineBanner({
  className,
  message,
  testID,
}: {
  className: string;
  message: string;
  testID: string;
}) {
  return (
    <div
      className={`rounded-md border px-4 py-3 text-caption ${className}`}
      role="alert"
      data-testid={testID}
    >
      {message}
    </div>
  );
}

export function QbConflictDetail({
  conflictId,
  testID,
}: QbConflictDetailProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [perFieldSelections, setPerFieldSelections] = useState<
    PerFieldSelection[]
  >([]);
  const [autoRecoveredMessage, setAutoRecoveredMessage] = useState<
    string | null
  >(null);
  const [voiceBlockedBanner, setVoiceBlockedBanner] = useState(false);

  // Voice attempt deep-link: ?reason=voice_qb_blocked → NotificationBanner only (RULE 3)
  useEffect(() => {
    if (searchParams.get("reason") === "voice_qb_blocked") {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setVoiceBlockedBanner(true);
    }
  }, [searchParams]);

  const {
    data: conflict,
    isLoading,
    isError,
  } = useQbConflictDetail(conflictId);

  const { resolve, isResolving, StalenessDialog } = useResolveQbConflict({
    conflictId,
    onAutoRecovered: (message) => {
      setAutoRecoveredMessage(message);
      setTimeout(() => {
        router.push("/settings/integrations/quickbooks/conflicts");
      }, 2500);
    },
  });

  const handleResolve = (resolution: string) => {
    if (!conflict) return;
    resolve({
      resolution: resolution as QbResolution,
      expected_pilot_modified_at: conflict.pilotModifiedAt,
      expected_external_modified_at: conflict.externalModifiedAt,
      ...(resolution === "per_field" && perFieldSelections.length > 0
        ? {
            per_field_selections: perFieldSelections.map((s) => ({
              field_name: s.fieldName,
              chosen_side: s.chosenSide as "pilot" | "external",
            })),
          }
        : {}),
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-neutral-300 border-t-brand-600" />
      </div>
    );
  }

  if (isError || !conflict) {
    return (
      <div
        className="rounded-md border border-fault-200 bg-fault-50 p-4 text-caption text-fault-700"
        role="alert"
      >
        Failed to load this conflict. It may have already been resolved.{" "}
        <button
          type="button"
          className="underline"
          onClick={() =>
            router.push("/settings/integrations/quickbooks/conflicts")
          }
        >
          Back to conflicts
        </button>
      </div>
    );
  }

  // Build resolver-compatible QB conflict object
  const conflictForResolver: UiQbConflictDetail = {
    id: conflict.id,
    conflictType: conflict.conflictType,
    entityType: conflict.entityType,
    entityId: conflict.entityId,
    entityDisplayName: conflict.entityDisplayName,
    masterDirection: conflict.masterDirection,
    pilotModifiedAt: conflict.pilotModifiedAt,
    externalModifiedAt: conflict.externalModifiedAt,
    pilotModifiedByUserId: conflict.pilotModifiedByUserId,
    pilotModifiedByName: conflict.pilotModifiedByName,
    fieldDiffs: conflict.fieldDiffs,
    financialDeltaCents: conflict.financialDeltaCents,
    pilotAmountCents: conflict.pilotAmountCents,
    qbAmountCents: conflict.qbAmountCents,
    arImpactDescription: conflict.arImpactDescription,
    taxPeriodWarning: conflict.taxPeriodWarning,
    qbTransactionUrl: conflict.qbTransactionUrl,
    resolution: conflict.resolution,
    resolvedAt: conflict.resolvedAt,
    autoResolvedStale: conflict.autoResolvedStale,
  };

  return (
    <div
      className="mx-auto max-w-4xl space-y-6 px-4 py-6"
      data-testid={testID ?? "qb-conflict-detail"}
    >
      {/* Back link */}
      <button
        type="button"
        onClick={() =>
          router.push("/settings/integrations/quickbooks/conflicts")
        }
        className="flex items-center gap-1 text-caption text-neutral-600 hover:text-neutral-900"
        data-testid="back-to-qb-conflicts"
      >
        ← Back to QuickBooks conflicts
      </button>

      {/* Voice blocked banner — no VoiceConfirmTurn rendered (RULE 3) */}
      {voiceBlockedBanner && (
        <InlineBanner
          className="bg-neutral-50 border-neutral-200 text-neutral-700"
          message="QuickBooks conflicts need the diff view to be safe — resolve using the options below."
          testID="voice-qb-blocked-banner"
        />
      )}

      {/* Auto-recovery banner */}
      {autoRecoveredMessage && (
        <InlineBanner
          className="bg-margin-50 border-margin-200 text-margin-700"
          message={autoRecoveredMessage}
          testID="auto-recovery-banner"
        />
      )}

      {/* Conflict header */}
      <div className="rounded-md border border-neutral-200 bg-white p-6">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-h2 font-medium text-neutral-900">
              {conflict.entityDisplayName}
            </h2>
            <p className="mt-1 text-caption text-neutral-600">
              {conflict.entityType.charAt(0).toUpperCase() +
                conflict.entityType.slice(1)}{" "}
              conflict
              {conflict.pilotModifiedByName &&
                ` · Modified by ${conflict.pilotModifiedByName}`}
            </p>
          </div>
          {conflict.masterDirection === "external" && (
            <span className="rounded-full bg-brand-100 px-3 py-1 text-caption font-medium text-brand-700">
              QuickBooks is master
            </span>
          )}
        </div>
      </div>

      {/* Two-column diff + resolution */}
      <div className="rounded-md border border-neutral-200 bg-white p-6">
        <IntegrationConflictResolver<UiQbConflictDetail>
          integration="quickbooks"
          conflict={conflictForResolver}
          onResolve={handleResolve}
          isResolving={isResolving}
          onResolveLater={() =>
            router.push("/settings/integrations/quickbooks/conflicts")
          }
          providerDisplayName="QuickBooks"
          masterDirection={conflict.masterDirection}
          supportsPerFieldResolution={
            conflict.conflictType === "modified_modified"
          }
          perFieldSelections={perFieldSelections}
          onPerFieldSelectionChange={setPerFieldSelections}
          renderDomainSpecificFields={
            conflict.entityType === "invoice" &&
            conflict.pilotAmountCents !== null &&
            conflict.qbAmountCents !== null &&
            conflict.financialDeltaCents !== null
              ? () => (
                  <InvoiceFinancialDeltaCallout
                    pilotAmountCents={conflict.pilotAmountCents!}
                    qbAmountCents={conflict.qbAmountCents!}
                    financialDeltaCents={conflict.financialDeltaCents!}
                    arImpactDescription={conflict.arImpactDescription ?? ""}
                    taxPeriodWarning={conflict.taxPeriodWarning}
                    qbTransactionUrl={conflict.qbTransactionUrl}
                    testID="invoice-financial-delta-callout"
                  />
                )
              : undefined
          }
          testID="qb-conflict-resolver"
        />
      </div>

      {/* Staleness dialog */}
      <StalenessDialog />
    </div>
  );
}
