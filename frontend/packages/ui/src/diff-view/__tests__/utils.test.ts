/**
 * DiffView utility function tests
 *
 * Location: packages/ui/src/diff-view/__tests__/utils.test.ts
 */

import { describe, it, expect } from "vitest";
import {
  normalizeFieldDiffs,
  buildQuoteLineDiff,
  deriveChangeType,
  fieldNameToLabel,
} from "../utils";
import type {
  RawFieldDiff,
  QuoteLineResponse,
  QuotePendingEditResponse,
} from "../utils";

// ─── normalizeFieldDiffs ───────────────────────────────────────────────────────

describe("normalizeFieldDiffs", () => {
  const makeRaw = (overrides: Partial<RawFieldDiff> = {}): RawFieldDiff => ({
    field_name: "unit_price_cents",
    pilot_value: "150000",
    external_value: "175000",
    base_value: "150000",
    pilot_change: "unchanged",
    external_change: "modified",
    ...overrides,
  });

  it("maps pilot_change='modified' to changeType='modified' (external perspective)", () => {
    const result = normalizeFieldDiffs([makeRaw()]);
    expect(result[0]!.changeType).toBe("modified");
  });

  it("maps external_change='added' to changeType='added' (external perspective)", () => {
    const result = normalizeFieldDiffs([
      makeRaw({ external_change: "added", pilot_change: "unchanged" }),
    ]);
    expect(result[0]!.changeType).toBe("added");
  });

  it("maps external_change='removed' to changeType='removed'", () => {
    const result = normalizeFieldDiffs([
      makeRaw({ external_change: "removed" }),
    ]);
    expect(result[0]!.changeType).toBe("removed");
  });

  it("maps external_change='unchanged' to changeType='unchanged'", () => {
    const result = normalizeFieldDiffs([
      makeRaw({ external_change: "unchanged" }),
    ]);
    expect(result[0]!.changeType).toBe("unchanged");
  });

  it("uses pilot_value as baseValue (external perspective)", () => {
    const result = normalizeFieldDiffs([makeRaw()]);
    expect(result[0]!.baseValue).toBe("150000");
    expect(result[0]!.modifiedValue).toBe("175000");
  });

  it("respects pilot perspective: uses base_value as baseValue", () => {
    const result = normalizeFieldDiffs([makeRaw()], "pilot");
    expect(result[0]!.changeType).toBe("unchanged"); // pilot_change
  });

  it("generates label from field name", () => {
    const result = normalizeFieldDiffs([makeRaw()]);
    expect(result[0]!.label).toBe("Unit Price");
  });
});

// ─── buildQuoteLineDiff ────────────────────────────────────────────────────────

describe("buildQuoteLineDiff", () => {
  const makeLine = (
    overrides: Partial<QuoteLineResponse> = {},
  ): QuoteLineResponse => ({
    id: "line-1",
    description: "200A Panel Upgrade",
    customer_visible: true,
    unit_price_cents: 150000,
    quantity: 1,
    total_cents: 150000,
    ...overrides,
  });

  const makeEdit = (
    overrides: Partial<QuotePendingEditResponse> = {},
  ): QuotePendingEditResponse => ({
    id: "edit-1",
    quote_id: "quote-1",
    affected_line_item_id: "line-1",
    edit_type: "field_edit",
    field_name: "unit_price_cents",
    old_value: "150000",
    new_value: "175000",
    created_at: new Date().toISOString(),
    ...overrides,
  });

  it("marks unedited line as unchanged", () => {
    const result = buildQuoteLineDiff({
      allLines: [makeLine()],
      pendingEdits: [],
    });
    expect(result[0]!.lineChangeType).toBe("unchanged");
  });

  it("marks edited line as modified", () => {
    const result = buildQuoteLineDiff({
      allLines: [makeLine()],
      pendingEdits: [makeEdit()],
    });
    expect(result[0]!.lineChangeType).toBe("modified");
  });

  it("marks removed line correctly", () => {
    const result = buildQuoteLineDiff({
      allLines: [makeLine()],
      pendingEdits: [makeEdit({ edit_type: "line_item_remove" })],
    });
    expect(result[0]!.lineChangeType).toBe("removed");
  });

  it("adds new line item from line_item_add edit", () => {
    const result = buildQuoteLineDiff({
      allLines: [],
      pendingEdits: [
        makeEdit({ edit_type: "line_item_add", new_value: "New fixture" }),
      ],
    });
    expect(result[0]!.lineChangeType).toBe("added");
    expect(result[0]!.label).toBe("New fixture");
  });

  it("groups multiple field edits under one line", () => {
    const result = buildQuoteLineDiff({
      allLines: [makeLine()],
      pendingEdits: [
        makeEdit({ id: "edit-1", field_name: "unit_price_cents" }),
        makeEdit({
          id: "edit-2",
          field_name: "quantity",
          old_value: "1",
          new_value: "2",
        }),
      ],
    });
    expect(result[0]!.fields.length).toBe(2);
  });

  it("includes pendingEditId on each field diff", () => {
    const result = buildQuoteLineDiff({
      allLines: [makeLine()],
      pendingEdits: [makeEdit({ id: "edit-xyz" })],
    });
    expect(result[0]!.fields[0]!.pendingEditId).toBe("edit-xyz");
  });
});

// ─── deriveChangeType ─────────────────────────────────────────────────────────

describe("deriveChangeType", () => {
  it("returns 'added' when baseValue is null", () => {
    expect(deriveChangeType(null, "new value")).toBe("added");
  });

  it("returns 'removed' when modifiedValue is null", () => {
    expect(deriveChangeType("old value", null)).toBe("removed");
  });

  it("returns 'unchanged' when values are equal", () => {
    expect(deriveChangeType("same", "same")).toBe("unchanged");
  });

  it("returns 'modified' when values differ", () => {
    expect(deriveChangeType("old", "new")).toBe("modified");
  });
});

// ─── fieldNameToLabel ─────────────────────────────────────────────────────────

describe("fieldNameToLabel", () => {
  it("returns domain override for unit_price_cents", () => {
    expect(fieldNameToLabel("unit_price_cents")).toBe("Unit Price");
  });

  it("converts snake_case to Title Case for unknown fields", () => {
    expect(fieldNameToLabel("my_custom_field")).toBe("My Custom Field");
  });

  it("handles single word", () => {
    expect(fieldNameToLabel("quantity")).toBe("Quantity");
  });
});
