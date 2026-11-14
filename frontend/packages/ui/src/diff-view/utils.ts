/**
 * DiffView utilities
 *
 * Location: packages/ui/src/diff-view/utils.ts
 *
 * Exported from barrel for use by FE-B8 and FE-B9 to normalize server-side
 * §16.2 field_diffs payloads, and by QuoteLineItemTable to build diffs from
 * quote_pending_edit rows.
 */

import type { DiffField, DiffLineItem } from "./types";

// ─── Types for raw API payloads ───────────────────────────────────────────────

/** Raw §16.2 server-computed field diff entry */
export interface RawFieldDiff {
  field_name: string;
  pilot_value: unknown;
  external_value: unknown;
  base_value: unknown;
  pilot_change: "unchanged" | "modified" | "added" | "removed";
  external_change: "unchanged" | "modified" | "added" | "removed";
}

/** Raw quote_pending_edit row from the API */
export interface QuotePendingEditResponse {
  id: string;
  quote_id: string;
  affected_line_item_id: string | null;
  edit_type:
    | "field_edit"
    | "line_item_add"
    | "line_item_remove"
    | "price_override";
  field_name: string | null;
  old_value: string | null;
  new_value: string | null;
  created_at: string;
}

/** Raw quote_line row from the API */
export interface QuoteLineResponse {
  id: string;
  description: string;
  customer_visible: boolean;
  unit_price_cents: number;
  quantity: number;
  total_cents: number;
}

// ─── normalizeFieldDiffs ───────────────────────────────────────────────────────

/**
 * Normalizes a raw §16.2 server field_diffs array into DiffField[].
 * Used by FE-B8 and FE-B9 to map from API response to <DiffView> props.
 *
 * @param rawDiffs - Array of server-computed field diff entries
 * @param perspective - Which side is "modified": 'external' (default) means external_value
 *   is the proposed change; 'pilot' means pilot_value is the proposed change.
 */
export function normalizeFieldDiffs(
  rawDiffs: RawFieldDiff[],
  perspective: "pilot" | "external" = "external",
): DiffField[] {
  return rawDiffs.map((raw): DiffField => {
    const baseValue =
      perspective === "external"
        ? formatValue(raw.pilot_value)
        : formatValue(raw.base_value);

    const modifiedValue =
      perspective === "external"
        ? formatValue(raw.external_value)
        : formatValue(raw.pilot_value);

    const changeType =
      perspective === "external" ? raw.external_change : raw.pilot_change;

    return {
      fieldName: raw.field_name,
      label: fieldNameToLabel(raw.field_name),
      baseValue,
      modifiedValue,
      changeType,
    };
  });
}

// ─── buildQuoteLineDiff ────────────────────────────────────────────────────────

/**
 * Converts quote_pending_edit rows into DiffLineItem[] for <DiffView variant="quote-line">.
 * Used by QuoteLineItemTable to build the diff from the pending edits API response.
 *
 * All lines are included (not just changed ones) so unchanged lines provide context.
 */
export function buildQuoteLineDiff(params: {
  allLines: QuoteLineResponse[];
  pendingEdits: QuotePendingEditResponse[];
}): DiffLineItem[] {
  const { allLines, pendingEdits } = params;

  // Group edits by affected_line_item_id
  const editsByLine = new Map<string, QuotePendingEditResponse[]>();
  const addedLines: QuotePendingEditResponse[] = [];

  for (const edit of pendingEdits) {
    if (edit.edit_type === "line_item_add") {
      addedLines.push(edit);
      continue;
    }
    if (edit.affected_line_item_id) {
      const existing = editsByLine.get(edit.affected_line_item_id) ?? [];
      existing.push(edit);
      editsByLine.set(edit.affected_line_item_id, existing);
    }
  }

  // Build DiffLineItem for each existing line
  const lineItems: DiffLineItem[] = allLines.map((line): DiffLineItem => {
    const lineEdits = editsByLine.get(line.id) ?? [];
    const isRemoved = lineEdits.some((e) => e.edit_type === "line_item_remove");
    const fieldEdits = lineEdits.filter(
      (e) => e.edit_type === "field_edit" || e.edit_type === "price_override",
    );

    const fields: DiffField[] = fieldEdits
      .filter((e) => e.field_name !== null)
      .map(
        (e): DiffField => ({
          fieldName: e.field_name!,
          label: fieldNameToLabel(e.field_name!),
          baseValue: e.old_value,
          modifiedValue: e.new_value,
          changeType: "modified",
          pendingEditId: e.id,
        }),
      );

    let lineChangeType: DiffLineItem["lineChangeType"] = "unchanged";
    if (isRemoved) lineChangeType = "removed";
    else if (fields.length > 0) lineChangeType = "modified";

    return {
      lineItemId: line.id,
      label: line.description,
      customerVisible: line.customer_visible,
      lineChangeType,
      fields,
    };
  });

  // Append added lines from pending edits
  for (const edit of addedLines) {
    lineItems.push({
      lineItemId: edit.id, // Use edit ID as placeholder line ID
      label: edit.new_value ?? "New line item",
      customerVisible: true,
      lineChangeType: "added",
      fields: [],
    });
  }

  return lineItems;
}

// ─── deriveChangeType ─────────────────────────────────────────────────────────

/**
 * Derives the change type from base/modified values when changeType is not explicit.
 */
export function deriveChangeType(
  baseValue: DiffField["baseValue"],
  modifiedValue: DiffField["modifiedValue"],
): "unchanged" | "modified" | "added" | "removed" {
  if (baseValue === null && modifiedValue !== null) return "added";
  if (modifiedValue === null && baseValue !== null) return "removed";
  if (baseValue === modifiedValue) return "unchanged";
  return "modified";
}

// ─── Internal helpers ─────────────────────────────────────────────────────────

function formatValue(value: unknown): string | number | boolean | null {
  if (value === null || value === undefined) return null;
  if (typeof value === "string") return value;
  if (typeof value === "number") return value;
  if (typeof value === "boolean") return value;
  return String(value);
}

/**
 * Converts snake_case field names to Title Case with domain overrides.
 */
/** Offline entity domain-specific field label overrides (FE-B7) */
const OFFLINE_ENTITY_FIELD_LABELS: Record<string, string> = {
  started_at: "Clock In",
  ended_at: "Clock Out",
  hours: "Hours",
  hours_remaining_estimate: "Estimated Hours Remaining",
  check_in_lat: "Check-In Latitude",
  check_in_lng: "Check-In Longitude",
  hourly_rate_cents: "Hourly Rate",
  cost_cents: "Amount",
  job_expense_category_code: "Category",
  is_billable: "Billable",
  incurred_at: "Date Incurred",
  to_status: "New Status",
  from_status: "Previous Status",
  changed_at: "Changed At",
  confirmed_at: "Confirmed At",
  check_type: "Check Type",
  gps_lat: "GPS Latitude",
  gps_lng: "GPS Longitude",
  total_amount_cents: "Total Amount",
  note_type: "Note Type",
  content: "Note Text",
  audio_path: "Audio File",
  captured_at: "Captured At",
  session_id: "Session ID",
  local_uri: "Local File",
  file_size_bytes: "File Size",
  mime_type: "File Type",
};

export function fieldNameToLabel(fieldName: string): string {
  const overrides: Record<string, string> = {
    unit_price_cents: "Unit Price",
    total_cents: "Total",
    quantity: "Quantity",
    description: "Description",
    customer_visible: "Customer Visible",
    scheduled_start_at: "Start Time",
    scheduled_end_at: "End Time",
    customer_name: "Customer",
    job_type: "Job Type",
    status: "Status",
    tax_rate: "Tax Rate",
    discount_cents: "Discount",
    labor_hours: "Labor Hours",
    labor_rate_cents: "Labor Rate",
    material_cost_cents: "Material Cost",
    markup_percent: "Markup %",
    // FE-B7: offline entity field labels
    ...OFFLINE_ENTITY_FIELD_LABELS,
  };

  if (fieldName in overrides) return overrides[fieldName]!;

  return fieldName
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}
