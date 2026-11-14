/**
 * DiffView — track-changes diff renderer (web)
 *
 * Location: packages/ui/src/diff-view/web/DiffView.tsx
 *
 * Cross-platform component — this is the web implementation.
 * Mobile implementation lives in packages/ui/src/diff-view/mobile/DiffView.tsx.
 * Shared types in packages/ui/src/diff-view/types.ts.
 *
 * Consumed by:
 *   FE-B5: <DiffView variant="quote-line"> — owner approval diff
 *   FE-B7: <DiffView variant="entity"> — mobile offline sync conflict
 *   FE-B8: <DiffView variant="calendar-event"> — Pilot vs external calendar
 *   FE-B9: <DiffView variant="qb-entity"> — Pilot vs QuickBooks
 *
 * ⚠️ Props interface LOCKED after FE-B5. See types.ts.
 */

import React, { useState } from "react";
import type { DiffViewProps } from "../types";
import { DiffField } from "./DiffField";
import { DiffLineItemRow } from "./DiffLineItem";
import { DiffChangesToggle } from "./DiffChangesToggle";

export function DiffView(props: DiffViewProps) {
  // Quote-line variant uses showToggle; others always show
  const initialShowChanges =
    props.variant === "quote-line" ? (props.defaultShowChanges ?? true) : true;
  const [showChanges, setShowChanges] = useState(initialShowChanges);

  if (props.variant === "quote-line") {
    const changedLines = props.lineItems.filter(
      (li) => li.lineChangeType !== "unchanged",
    );
    const changesCount = changedLines.length;

    if (changesCount === 0) {
      return (
        <p className="text-body text-neutral-400 italic py-2">
          No changes to display.
        </p>
      );
    }

    return (
      <div
        data-testid={props.testID ?? "diff-view"}
        aria-label="Quote line item changes"
        aria-live="polite"
      >
        {props.showToggle && (
          <DiffChangesToggle
            showChanges={showChanges}
            onToggle={() => setShowChanges((v) => !v)}
            changesCount={changesCount}
          />
        )}

        {(!props.showToggle || showChanges) && (
          <div
            id="diff-view-content"
            role="list"
            aria-label="Changed line items"
          >
            {props.lineItems.map((lineItem) => (
              <DiffLineItemRow
                key={lineItem.lineItemId}
                lineItem={lineItem}
                onRevertField={props.onRevertField}
              />
            ))}
          </div>
        )}
      </div>
    );
  }

  if (props.variant === "calendar-event" || props.variant === "qb-entity") {
    const defaultSideLabels = {
      "calendar-event": { base: "Pilot", modified: "Google Calendar" },
      "qb-entity": { base: "Pilot", modified: "QuickBooks" },
    };
    const sideLabels = props.sideLabels ?? defaultSideLabels[props.variant];
    const changedFields = props.fieldDiffs.filter(
      (f) => (f.changeType ?? "modified") !== "unchanged",
    );

    return (
      <div
        data-testid={props.testID ?? "diff-view"}
        aria-label={`Changes for ${props.entityLabel}`}
      >
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-body-lg font-medium text-neutral-900">
            {props.entityLabel}
          </h4>
          <div className="flex items-center gap-3 text-caption text-neutral-400">
            <span>{sideLabels.base}</span>
            <span aria-hidden="true">→</span>
            <span>{sideLabels.modified}</span>
          </div>
        </div>

        {changedFields.length === 0 ? (
          <p className="text-body text-neutral-400 italic py-2">
            No differences detected.
          </p>
        ) : (
          <div
            role="list"
            aria-label={`Field differences for ${props.entityLabel}`}
          >
            {props.fieldDiffs.map((field) => (
              <DiffField
                key={field.fieldName}
                field={field}
                showSideLabels
                baseLabel={sideLabels.base}
                modifiedLabel={sideLabels.modified}
              />
            ))}
          </div>
        )}
      </div>
    );
  }

  // variant === "entity"
  const changedFields = props.fieldDiffs.filter(
    (f) => (f.changeType ?? "modified") !== "unchanged",
  );

  return (
    <div
      data-testid={props.testID ?? "diff-view"}
      aria-label={`Changes for ${props.entityLabel}`}
    >
      <h4 className="text-body-lg font-medium text-neutral-900 mb-3">
        {props.entityLabel}
      </h4>

      {changedFields.length === 0 ? (
        <p className="text-body text-neutral-400 italic py-2">
          No differences detected.
        </p>
      ) : (
        <div
          role="list"
          aria-label={`Field differences for ${props.entityLabel}`}
        >
          {props.fieldDiffs.map((field) => (
            <DiffField key={field.fieldName} field={field} />
          ))}
        </div>
      )}
    </div>
  );
}
