/**
 * normalizeQbFieldDiffs unit tests — FE-B9
 *
 * Critical: validates RULE 4 compliance — pilot_value → baseValue, external_value → modifiedValue
 */

import { normalizeQbFieldDiffs } from "./normalizeQbFieldDiffs";
import type { QbFieldDiff } from "../types";

const fieldDiffs: QbFieldDiff[] = [
  {
    fieldName: "amount_cents",
    pilot_value: 285000,
    external_value: 322500,
    changeType: "modified",
  },
  {
    fieldName: "due_date",
    pilot_value: "2026-06-15",
    external_value: "2026-06-30",
    changeType: "modified",
  },
  {
    fieldName: "notes",
    pilot_value: null,
    external_value: null,
    changeType: "unchanged",
  },
];

describe("normalizeQbFieldDiffs", () => {
  describe("masterDirection='pilot' (default)", () => {
    it("maps pilot_value → baseValue", () => {
      const result = normalizeQbFieldDiffs(fieldDiffs, "pilot");
      expect(result[0].baseValue).toBe("285000");
    });

    it("maps external_value → modifiedValue", () => {
      const result = normalizeQbFieldDiffs(fieldDiffs, "pilot");
      expect(result[0].modifiedValue).toBe("322500");
    });

    it("preserves fieldName", () => {
      const result = normalizeQbFieldDiffs(fieldDiffs, "pilot");
      expect(result[0].fieldName).toBe("amount_cents");
    });

    it("preserves changeType", () => {
      const result = normalizeQbFieldDiffs(fieldDiffs, "pilot");
      expect(result[0].changeType).toBe("modified");
      expect(result[2].changeType).toBe("unchanged");
    });

    it("handles null values as null (not 'null' string)", () => {
      const result = normalizeQbFieldDiffs(fieldDiffs, "pilot");
      expect(result[2].baseValue).toBeNull();
      expect(result[2].modifiedValue).toBeNull();
    });
  });

  describe("masterDirection='external' (QB is master — swaps sides)", () => {
    it("maps external_value → baseValue when QB is master", () => {
      const result = normalizeQbFieldDiffs(fieldDiffs, "external");
      expect(result[0].baseValue).toBe("322500"); // QB on left
    });

    it("maps pilot_value → modifiedValue when QB is master", () => {
      const result = normalizeQbFieldDiffs(fieldDiffs, "external");
      expect(result[0].modifiedValue).toBe("285000"); // Pilot on right
    });
  });

  it("returns empty array for empty input", () => {
    expect(normalizeQbFieldDiffs([], "pilot")).toEqual([]);
  });

  it("defaults to pilot direction when not specified", () => {
    const withPilot = normalizeQbFieldDiffs(fieldDiffs, "pilot");
    const withDefault = normalizeQbFieldDiffs(fieldDiffs);
    expect(withPilot).toEqual(withDefault);
  });

  it("stringifies non-string values", () => {
    const numericDiff: QbFieldDiff[] = [
      {
        fieldName: "amount",
        pilot_value: 12345,
        external_value: 67890,
        changeType: "modified",
      },
    ];
    const result = normalizeQbFieldDiffs(numericDiff, "pilot");
    expect(result[0].baseValue).toBe("12345");
    expect(result[0].modifiedValue).toBe("67890");
  });
});
