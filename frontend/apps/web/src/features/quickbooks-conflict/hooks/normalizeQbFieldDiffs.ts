/**
 * normalizeQbFieldDiffs — maps QB BE field_diffs to DiffField[] for <DiffView>
 *
 * Location: apps/web/src/features/quickbooks-conflict/hooks/normalizeQbFieldDiffs.ts
 *
 * Established FE-B9. RULE 4 — server-side diff is canonical; never compute diffs client-side.
 * pilot_value → baseValue, external_value → modifiedValue.
 * When masterDirection='external': base=QB (left), modified=Pilot (right).
 * When masterDirection='pilot': base=Pilot (left), modified=QB (right).
 */

import type { DiffField } from "@pilot/ui";
import type { QbFieldDiff, QbMasterDirection } from "../types";

/**
 * Normalize QbFieldDiff[] from backend A49 payload → DiffField[] for DiffView.
 * pilot_value → baseValue, external_value → modifiedValue.
 *
 * @param fieldDiffs - Raw field diffs from backend
 * @param masterDirection - Column ordering: 'pilot' = Pilot on left, 'external' = QB on left
 */
export function normalizeQbFieldDiffs(
  fieldDiffs: QbFieldDiff[],
  masterDirection: QbMasterDirection = "pilot",
): DiffField[] {
  return fieldDiffs.map((d) => {
    const pilotStr =
      d.pilot_value !== undefined && d.pilot_value !== null
        ? String(d.pilot_value)
        : null;
    const externalStr =
      d.external_value !== undefined && d.external_value !== null
        ? String(d.external_value)
        : null;

    return {
      fieldName: d.fieldName,
      // masterDirection='external' (QB master): base=QB, modified=Pilot
      // masterDirection='pilot' (Pilot master): base=Pilot, modified=QB
      baseValue: masterDirection === "external" ? externalStr : pilotStr,
      modifiedValue: masterDirection === "external" ? pilotStr : externalStr,
      changeType: d.changeType,
    } satisfies DiffField;
  });
}
