/**
 * IntegrationConflictResolver — bilateral integration conflict resolution UI
 *
 * Location: packages/ui/src/integration-conflict-resolver/IntegrationConflictResolver.tsx
 *
 * Established FE-B8 (calendar). Extended by FE-B9 (quickbooks + field issues).
 * Pattern ref: mvp-arch.md §16.10; design doc batch-fe-b8-design.md §A.1.1
 *
 * ⚠️ INTERFACE LOCKED after FE-B8 ships.
 * See IntegrationConflictResolverProps in ./types.ts for the full locked API.
 * FE-B9 adds optional backward-compatible props only.
 *
 * Layout branching:
 *   modified_modified → two-column DiffView layout + optional per-field picker
 *   deleted_modified | modified_deleted → DeletionConflictView (verb-button layout)
 *
 * masterDirection (FE-B9):
 *   'pilot' (default) → Pilot on left (FE-B8 calendar behavior — no change)
 *   'external' → external system on left (QB Invoice, QB is master)
 *
 * Tokens used (all from pilotPreset):
 *   bg-brand-600, hover:bg-brand-700 — primary button ("Use Tech's/Pilot's version")
 *   border-brand-600 text-brand-600 hover:bg-brand-50 — secondary button
 *   bg-fault-50, border-fault-200, text-fault-700 — destructive secondary
 *   bg-neutral-50, border-neutral-200 — card backgrounds
 *   text-neutral-900, text-neutral-600 — body text
 *   bg-brand-50 border-brand-200 — master column header tint (FE-B9)
 */

import React, { useState } from "react";
import { DiffView } from "../diff-view";
import type { DiffField } from "../diff-view/types";
import { ExpiryCountdownBadge } from "./ExpiryCountdownBadge";
import { DeletionConflictView } from "./DeletionConflictView";
import { ConflictTypeLabel } from "./ConflictTypeLabel";
import type {
  IntegrationConflictResolverProps,
  CalendarConflictDetail,
  CalendarApiFieldDiff,
  QbConflictDetail,
  QbFieldDiff,
  FieldIssueDetail,
  FieldIssueDiff,
  PerFieldSelection,
} from "./types";

// ─── Normalizers (server-side diff is canonical — RULE 4) ─────────────────────

/**
 * Normalize CalendarApiFieldDiff[] → DiffField[] for <DiffView variant="calendar-event">.
 */
function normalizeCalendarFieldDiffs(
  conflict: CalendarConflictDetail,
): DiffField[] {
  if (!conflict.fieldDiffs || conflict.fieldDiffs.length === 0) return [];

  return conflict.fieldDiffs.map((d: CalendarApiFieldDiff) => ({
    fieldName: d.fieldName,
    baseValue: d.pilotValue !== undefined ? String(d.pilotValue ?? "") : null,
    modifiedValue:
      d.externalValue !== undefined ? String(d.externalValue ?? "") : null,
    changeType:
      d.externalChange === "unchanged"
        ? "unchanged"
        : d.externalChange === "added"
          ? "added"
          : d.externalChange === "removed"
            ? "removed"
            : "modified",
  }));
}

/**
 * Normalize QbFieldDiff[] → DiffField[] for <DiffView variant="qb-entity">.
 * pilot_value → baseValue, external_value → modifiedValue (RULE 4 / design doc C.5).
 * When masterDirection='external', swap sides so QB is on the left (base).
 */
function normalizeQbFieldDiffsInternal(
  fieldDiffs: QbFieldDiff[],
  masterDirection: "pilot" | "external",
): DiffField[] {
  return fieldDiffs.map((d: QbFieldDiff) => {
    const pilotStr =
      d.pilot_value !== undefined ? String(d.pilot_value ?? "") : null;
    const externalStr =
      d.external_value !== undefined ? String(d.external_value ?? "") : null;

    return {
      fieldName: d.fieldName,
      // masterDirection='external' (QB master): base=QB, modified=Pilot
      // masterDirection='pilot' (Pilot master): base=Pilot, modified=QB
      baseValue: masterDirection === "external" ? externalStr : pilotStr,
      modifiedValue: masterDirection === "external" ? pilotStr : externalStr,
      changeType: d.changeType,
    };
  });
}

/**
 * Normalize FieldIssueDiff[] → DiffField[] for <DiffView variant="entity">.
 * techValue → baseValue (tech is always left — masterDirection='pilot' for field issues).
 */
function normalizeFieldIssueDiffs(fieldDiffs: FieldIssueDiff[]): DiffField[] {
  return fieldDiffs.map((d: FieldIssueDiff) => ({
    fieldName: d.fieldName,
    baseValue: d.techValue !== undefined ? String(d.techValue ?? "") : null,
    modifiedValue:
      d.serverValue !== undefined ? String(d.serverValue ?? "") : null,
    changeType: d.changeType,
  }));
}

// ─── Type guards ──────────────────────────────────────────────────────────────

function isCalendarConflict(
  conflict: CalendarConflictDetail | QbConflictDetail | FieldIssueDetail,
): conflict is CalendarConflictDetail {
  const diffs = (conflict as CalendarConflictDetail).fieldDiffs;
  if (!Array.isArray(diffs) || diffs.length === 0) return false;
  const firstDiff = diffs[0] as unknown as
    | Record<string, unknown>
    | null
    | undefined;
  return (
    typeof firstDiff === "object" &&
    firstDiff !== null &&
    firstDiff !== undefined &&
    "pilotChange" in firstDiff
  );
}

function isQbConflict(
  conflict: CalendarConflictDetail | QbConflictDetail | FieldIssueDetail,
): conflict is QbConflictDetail {
  return (
    "entityType" in conflict &&
    "masterDirection" in conflict &&
    !("techId" in conflict)
  );
}

// ─── Per-field picker sub-component ───────────────────────────────────────────

interface PerFieldPickerProps {
  fieldDiffs: DiffField[];
  selections: PerFieldSelection[];
  onSelectionChange: (selections: PerFieldSelection[]) => void;
  leftLabel: string;
  rightLabel: string;
}

function PerFieldPicker({
  fieldDiffs,
  selections,
  onSelectionChange,
  leftLabel,
  rightLabel,
}: PerFieldPickerProps) {
  const getSelection = (fieldName: string): PerFieldSelection | undefined =>
    selections.find((s) => s.fieldName === fieldName);

  const handleChange = (
    fieldName: string,
    side: PerFieldSelection["chosenSide"],
  ) => {
    const updated = [
      ...selections.filter((s) => s.fieldName !== fieldName),
      { fieldName, chosenSide: side },
    ];
    onSelectionChange(updated);
  };

  return (
    <div className="space-y-2" data-testid="per-field-picker">
      <p className="text-caption text-neutral-600">
        Choose which version to keep for each field:
      </p>
      {fieldDiffs.map((field) => {
        const sel = getSelection(field.fieldName);
        return (
          <div
            key={field.fieldName}
            className="flex flex-col gap-1 rounded-md border border-neutral-200 bg-white px-4 py-3"
            data-testid={`per-field-row-${field.fieldName}`}
          >
            <p className="text-caption font-medium text-neutral-900">
              {field.fieldName}
            </p>
            <div className="flex gap-4">
              {/* Left side radio (Pilot or Tech) */}
              <label className="flex cursor-pointer items-center gap-2 text-caption">
                <input
                  type="radio"
                  name={`field-${field.fieldName}`}
                  value="left"
                  checked={
                    sel?.chosenSide === "pilot" || sel?.chosenSide === "tech"
                  }
                  onChange={() =>
                    handleChange(
                      field.fieldName,
                      leftLabel === "Tech" ? "tech" : "pilot",
                    )
                  }
                  data-testid={`radio-left-${field.fieldName}`}
                />
                <span className="text-neutral-900">{leftLabel}:</span>
                <span className="text-neutral-600">
                  {field.baseValue ?? "(empty)"}
                </span>
              </label>
              {/* Right side radio (External or Server) */}
              <label className="flex cursor-pointer items-center gap-2 text-caption">
                <input
                  type="radio"
                  name={`field-${field.fieldName}`}
                  value="right"
                  checked={
                    sel?.chosenSide === "server" ||
                    sel?.chosenSide === "external"
                  }
                  onChange={() =>
                    handleChange(
                      field.fieldName,
                      rightLabel === "Server" ? "server" : "external",
                    )
                  }
                  data-testid={`radio-right-${field.fieldName}`}
                />
                <span className="text-neutral-900">{rightLabel}:</span>
                <span className="text-neutral-600">
                  {field.modifiedValue ?? "(empty)"}
                </span>
              </label>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export function IntegrationConflictResolver<
  T extends CalendarConflictDetail | QbConflictDetail | FieldIssueDetail =
    CalendarConflictDetail,
>({
  integration,
  conflict,
  onResolve,
  isResolving,
  onResolveLater,
  providerDisplayName,
  renderDomainSpecificFields,
  daysUntilExpiry,
  testID,
  // FE-B9 additive props (all optional — default to FE-B8 behavior when absent)
  masterDirection = "pilot",
  supportsPerFieldResolution = false,
  perFieldSelections = [],
  onPerFieldSelectionChange,
}: IntegrationConflictResolverProps<T>) {
  const [isPerFieldPickerOpen, setIsPerFieldPickerOpen] = useState(false);

  // Derive the provider display name (from prop > conflict field > default)
  const resolvedProviderName =
    providerDisplayName ??
    (isCalendarConflict(conflict)
      ? (conflict.providerDisplayName ?? "Google Calendar")
      : integration === "quickbooks"
        ? "QuickBooks"
        : "External Provider");

  // Column labels depend on masterDirection and integration type
  const leftLabel =
    masterDirection === "external" ? resolvedProviderName : "Pilot";
  const rightLabel =
    masterDirection === "external" ? "Pilot" : resolvedProviderName;

  // Determine the primary action button labels based on direction and integration
  const acceptPilotLabel =
    masterDirection === "external"
      ? `Use ${resolvedProviderName} version`
      : integration === "quickbooks"
        ? "Use Pilot version"
        : "Use Pilot version";

  const acceptExternalLabel =
    masterDirection === "external"
      ? "Use Pilot version"
      : `Use ${resolvedProviderName} version`;

  const conflictType = conflict.conflictType;

  // Banner for auto-expiry pre-warning
  const showExpiryBanner =
    daysUntilExpiry !== null &&
    daysUntilExpiry !== undefined &&
    daysUntilExpiry <= 7;
  const expiryIsUrgent =
    daysUntilExpiry !== null &&
    daysUntilExpiry !== undefined &&
    daysUntilExpiry <= 3;

  // Normalized diffs for DiffView
  let normalizedDiffs: DiffField[] = [];
  let diffVariant: "calendar-event" | "qb-entity" | "entity" = "calendar-event";

  if (isCalendarConflict(conflict)) {
    normalizedDiffs = normalizeCalendarFieldDiffs(conflict);
    diffVariant = "calendar-event";
  } else if (isQbConflict(conflict)) {
    normalizedDiffs = normalizeQbFieldDiffsInternal(
      (conflict as QbConflictDetail).fieldDiffs ?? [],
      masterDirection,
    );
    diffVariant = "qb-entity";
  } else {
    // FieldIssueDetail — tech always left (masterDirection='pilot' for field issues)
    normalizedDiffs = normalizeFieldIssueDiffs(
      (conflict as unknown as FieldIssueDetail).fieldDiffs ?? [],
    );
    diffVariant = "entity";
  }

  // Per-field picker only available for modified_modified and not deletion types
  const canUsePerFieldPicker =
    supportsPerFieldResolution && conflictType === "modified_modified";

  const allFieldsSelected =
    perFieldSelections.length === normalizedDiffs.length &&
    normalizedDiffs.every((f) =>
      perFieldSelections.some((s) => s.fieldName === f.fieldName),
    );

  return (
    <div
      data-testid={testID ?? "integration-conflict-resolver"}
      className="space-y-4"
    >
      {/* Header: conflict type + expiry badge */}
      <div className="flex flex-wrap items-center gap-3">
        <ConflictTypeLabel conflictType={conflictType} />
        {daysUntilExpiry !== null && daysUntilExpiry !== undefined && (
          <ExpiryCountdownBadge daysUntilExpiry={daysUntilExpiry} />
        )}
      </div>

      {/* Expiry warning banner (when within 7-day window) */}
      {showExpiryBanner &&
        daysUntilExpiry !== null &&
        daysUntilExpiry !== undefined && (
          <div
            className={`rounded-md border px-4 py-3 text-caption ${
              expiryIsUrgent
                ? "border-fault-200 bg-fault-50 text-fault-700"
                : "border-alert-200 bg-alert-50 text-alert-700"
            }`}
            role="alert"
            data-testid="expiry-warning-banner"
          >
            {expiryIsUrgent
              ? `Urgent: conflict auto-resolves in ${daysUntilExpiry} day${daysUntilExpiry === 1 ? "" : "s"}`
              : `This conflict will auto-resolve to Pilot's version in ${daysUntilExpiry} days if not resolved.`}
          </div>
        )}

      {/* Layout branching */}
      {conflictType === "modified_modified" ? (
        // Two-column diff layout
        <div className="space-y-4">
          {/* Column header strip — master column tinted (FE-B9) */}
          {masterDirection === "external" && (
            <div className="flex" data-testid="master-direction-header">
              <div className="flex-1 rounded-t-md bg-brand-50 border-b border-brand-200 px-4 py-2">
                <span className="text-caption font-medium text-brand-700">
                  {leftLabel} (master)
                </span>
              </div>
              <div className="flex-1 px-4 py-2">
                <span className="text-caption font-medium text-neutral-600">
                  {rightLabel}
                </span>
              </div>
            </div>
          )}

          {normalizedDiffs.length > 0 ? (
            <DiffView
              variant={diffVariant}
              fieldDiffs={normalizedDiffs}
              entityLabel={
                isCalendarConflict(conflict)
                  ? (conflict.jobTitle ?? "Job")
                  : isQbConflict(conflict)
                    ? ((conflict as QbConflictDetail).entityDisplayName ??
                      "Entity")
                    : "Field Capture"
              }
              sideLabels={{
                base: leftLabel,
                modified: rightLabel,
              }}
              testID="conflict-diff-view"
            />
          ) : (
            <div className="rounded-md border border-neutral-200 bg-neutral-50 p-4">
              <p className="text-body text-neutral-600">
                No field-level diff available.
              </p>
            </div>
          )}

          {/* Domain-specific fields slot (FE-B9 injects QB InvoiceFinancialDeltaCallout here) */}
          {renderDomainSpecificFields && (
            <div data-testid="domain-specific-fields">
              {renderDomainSpecificFields(conflict)}
            </div>
          )}

          {/* Per-field picker (FE-B9 — disabled for FE-B8 calendar usage by default) */}
          {canUsePerFieldPicker && (
            <div className="border-t border-neutral-200 pt-4">
              {!isPerFieldPickerOpen ? (
                <button
                  type="button"
                  onClick={() => setIsPerFieldPickerOpen(true)}
                  className="text-caption text-brand-600 hover:text-brand-700 underline"
                  data-testid="per-field-picker-toggle"
                >
                  Choose field by field →
                </button>
              ) : (
                <div className="space-y-3" data-testid="per-field-picker-open">
                  <PerFieldPicker
                    fieldDiffs={normalizedDiffs}
                    selections={perFieldSelections}
                    onSelectionChange={onPerFieldSelectionChange ?? (() => {})}
                    leftLabel={leftLabel}
                    rightLabel={rightLabel}
                  />
                  <button
                    type="button"
                    disabled={isResolving || !allFieldsSelected}
                    onClick={() => onResolve("per_field")}
                    className="w-full rounded-md bg-brand-600 px-4 py-2 text-body font-medium text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
                    data-testid="commit-field-selections-btn"
                  >
                    Commit field selections
                  </button>
                  <button
                    type="button"
                    onClick={() => setIsPerFieldPickerOpen(false)}
                    className="w-full text-caption text-neutral-600 hover:text-neutral-900"
                    data-testid="cancel-per-field-btn"
                  >
                    Cancel field-by-field
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Action buttons — modified_modified */}
          {!isPerFieldPickerOpen && (
            <div className="flex flex-col gap-3 border-t border-neutral-200 pt-4 sm:flex-row">
              {/* Primary: Use Pilot/Tech version → accept_local */}
              <button
                type="button"
                disabled={isResolving}
                onClick={() => onResolve("accept_local")}
                className="flex flex-1 items-center justify-center rounded-md bg-brand-600 px-4 py-2 text-body font-medium text-white hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-600 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                aria-busy={isResolving}
                data-testid="resolve-accept-local-btn"
              >
                {isResolving ? (
                  <span className="flex items-center gap-2">
                    <svg
                      className="h-4 w-4 animate-spin"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                      aria-hidden="true"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                      />
                    </svg>
                    Resolving…
                  </span>
                ) : (
                  acceptPilotLabel
                )}
              </button>

              {/* Secondary: Use external/server version → accept_remote */}
              <button
                type="button"
                disabled={isResolving}
                onClick={() => onResolve("accept_remote")}
                className="flex flex-1 items-center justify-center rounded-md border border-brand-600 bg-white px-4 py-2 text-body font-medium text-brand-600 hover:bg-brand-50 focus:outline-none focus:ring-2 focus:ring-brand-600 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                aria-busy={isResolving}
                data-testid="resolve-accept-remote-btn"
              >
                {acceptExternalLabel}
              </button>

              {/* Escape hatch */}
              <button
                type="button"
                disabled={isResolving}
                onClick={onResolveLater}
                className="flex items-center justify-center px-4 py-2 text-caption text-neutral-600 hover:text-neutral-900 disabled:cursor-not-allowed disabled:opacity-50"
                data-testid="resolve-later-btn"
              >
                Resolve later
              </button>
            </div>
          )}
        </div>
      ) : (
        // Deletion conflict layout (deleted_modified | modified_deleted)
        <DeletionConflictView
          conflictType={conflictType as "deleted_modified" | "modified_deleted"}
          jobTitle={
            isCalendarConflict(conflict) ? (conflict.jobTitle ?? null) : null
          }
          onResolve={onResolve}
          isResolving={isResolving}
          onResolveLater={onResolveLater}
          testID="deletion-conflict-view"
        />
      )}
    </div>
  );
}
