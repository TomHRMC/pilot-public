/**
 * FieldIssueDetail — page shell for field issue resolution
 *
 * Location: apps/web/src/features/field-issues/components/FieldIssueDetail.tsx
 *
 * Established FE-B9. Full resolution flow:
 *   - modified_modified: IntegrationConflictResolver with DiffView variant="entity"
 *   - deleted_modified | modified_deleted: DeletionConflictView via IntegrationConflictResolver
 *   - per-field picker: expands on "Choose field by field →"
 *   - 409 server_changed: StalenessRefreshDialog
 *   - 409 auto_recovered: success banner + navigate to queue
 *   - 409 stale: info banner + navigate to queue
 *   - Voice deep-link ?reason=voice_deletion_redirect: NotificationBanner
 *
 * RULE 3: No VoiceConfirmTurn for QB. Field issues DO have voice confirm-as-turn.
 * RULE 4: Server-side diff is canonical.
 */

"use client";

import React, { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { IntegrationConflictResolver } from "@pilot/ui";
import type {
  PerFieldSelection,
  FieldIssueDetail as UiFieldIssueDetail,
} from "@pilot/ui";
import { useFieldIssueDetail } from "../hooks/useFieldIssueDetail";
import { useResolveFieldIssue } from "../hooks/useResolveFieldIssue";
import { EscalationContextHeader } from "./EscalationContextHeader";
import type { FieldIssueResolution } from "../types";

interface FieldIssueDetailProps {
  issueId: string;
  testID?: string;
}

type BannerState =
  | { type: "auto_recovered"; message: string }
  | { type: "stale"; message: string }
  | { type: "voice_deletion_redirect" }
  | { type: "voice_permission_redirect" }
  | null;

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

export function FieldIssueDetail({ issueId, testID }: FieldIssueDetailProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [perFieldSelections, setPerFieldSelections] = useState<
    PerFieldSelection[]
  >([]);
  const [banner, setBanner] = useState<BannerState>(null);

  // Handle voice deep-link reasons
  useEffect(() => {
    const reason = searchParams.get("reason");
    if (reason === "voice_deletion_redirect") {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setBanner({ type: "voice_deletion_redirect" });
    } else if (reason === "voice_permission_redirect") {
      setBanner({ type: "voice_permission_redirect" });
    }
  }, [searchParams]);

  const { data: issue, isLoading, isError } = useFieldIssueDetail(issueId);

  const { resolve, isResolving, StalenessDialog } = useResolveFieldIssue({
    issueId,
    onBannerOutcome: (outcome, message) => {
      setBanner({ type: outcome, message });
      // Navigate back to queue after a short delay
      setTimeout(() => {
        router.push("/dashboard/approvals/field-issues");
      }, 2500);
    },
  });

  const handleResolve = (resolution: string) => {
    if (!issue) return;
    resolve({
      resolution: resolution as FieldIssueResolution,
      expected_server_state_hash: issue.expectedServerStateHash,
      ...(resolution === "per_field" && perFieldSelections.length > 0
        ? {
            per_field_selections: perFieldSelections.map((s) => ({
              field_name: s.fieldName,
              chosen_side: s.chosenSide as "tech" | "server",
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

  if (isError || !issue) {
    return (
      <div
        className="rounded-md border border-fault-200 bg-fault-50 p-4 text-caption text-fault-700"
        role="alert"
      >
        Failed to load this field issue. It may have already been resolved.{" "}
        <button
          type="button"
          className="underline"
          onClick={() => router.push("/dashboard/approvals/field-issues")}
        >
          Back to queue
        </button>
      </div>
    );
  }

  // Build the resolver-compatible conflict object using ui FieldIssueDetail shape
  const conflictForResolver: UiFieldIssueDetail = {
    id: issue.id,
    conflictType: issue.conflictType,
    operationType: issue.operationType,
    techId: issue.techId,
    techName: issue.techName,
    explainerCopy: issue.explainerCopy,
    fieldDiffs: issue.fieldDiffs.map((d) => ({
      fieldName: d.fieldName,
      techValue: d.techValue,
      serverValue: d.serverValue,
      changeType: d.changeType,
    })),
    resolution: issue.resolution,
    resolvedAt: issue.resolvedAt,
    expectedServerStateHash: issue.expectedServerStateHash,
  };

  return (
    <div
      className="mx-auto max-w-4xl space-y-6 px-4 py-6"
      data-testid={testID ?? "field-issue-detail"}
    >
      {/* Back link */}
      <button
        type="button"
        onClick={() => router.push("/dashboard/approvals/field-issues")}
        className="flex items-center gap-1 text-caption text-neutral-600 hover:text-neutral-900"
        data-testid="back-to-queue"
      >
        ← Back to field issues
      </button>

      {/* Banner messages */}
      {banner?.type === "auto_recovered" && (
        <InlineBanner
          className="bg-margin-50 border-margin-200 text-margin-700"
          message={banner.message}
          testID="auto-recovered-banner"
        />
      )}
      {banner?.type === "stale" && (
        <InlineBanner
          className="bg-neutral-50 border-neutral-200 text-neutral-700"
          message={banner.message}
          testID="stale-banner"
        />
      )}
      {banner?.type === "voice_deletion_redirect" && (
        <InlineBanner
          className="bg-neutral-50 border-neutral-200 text-neutral-700"
          message="Your voice session routed here — please choose how to handle this deletion."
          testID="voice-deletion-redirect-banner"
        />
      )}
      {banner?.type === "voice_permission_redirect" && (
        <InlineBanner
          className="bg-alert-50 border-alert-200 text-alert-700"
          message="Voice resolution paused for this issue — review the captured data before deciding."
          testID="voice-permission-redirect-banner"
        />
      )}

      {/* Escalation context header */}
      <EscalationContextHeader issue={issue} testID="issue-context-header" />

      {/* Two-column diff + resolution actions */}
      <div className="rounded-md border border-neutral-200 bg-white p-6">
        <IntegrationConflictResolver<UiFieldIssueDetail>
          integration="quickbooks"
          conflict={conflictForResolver}
          onResolve={handleResolve}
          isResolving={isResolving}
          onResolveLater={() =>
            router.push("/dashboard/approvals/field-issues")
          }
          providerDisplayName="Server"
          masterDirection="pilot" // Tech is always left for field issues
          supportsPerFieldResolution={
            issue.conflictType === "modified_modified"
          }
          perFieldSelections={perFieldSelections}
          onPerFieldSelectionChange={setPerFieldSelections}
          testID="field-issue-resolver"
        />
      </div>

      {/* Staleness dialog (mounted by useStalenessRetry) */}
      <StalenessDialog />
    </div>
  );
}
