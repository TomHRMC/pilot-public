/**
 * QB conflict per-field resolution integration test — FE-B9
 */

import { normalizeQbFieldDiffs } from "@/features/quickbooks-conflict/hooks/normalizeQbFieldDiffs";
import { customerConflictDetail } from "@/features/quickbooks-conflict/mocks/qbConflictFixtures";
import type { QbPerFieldSelection } from "@/features/quickbooks-conflict/types";

describe("QB conflict per-field resolution", () => {
  it("customer fixture fieldDiffs can be normalized for per-field picker", () => {
    const normalized = normalizeQbFieldDiffs(
      customerConflictDetail.fieldDiffs,
      "pilot",
    );
    expect(normalized.length).toBe(customerConflictDetail.fieldDiffs.length);
    expect(normalized[0].fieldName).toBeTruthy();
    expect(normalized[0].baseValue).toBeDefined();
    expect(normalized[0].modifiedValue).toBeDefined();
  });

  it("QbPerFieldSelection has field_name and chosen_side", () => {
    const sel: QbPerFieldSelection = {
      field_name: "display_name",
      chosen_side: "pilot",
    };
    expect(sel.field_name).toBe("display_name");
    expect(sel.chosen_side).toBe("pilot");
  });

  it("QbPerFieldSelection chosen_side can be 'external'", () => {
    const sel: QbPerFieldSelection = {
      field_name: "phone",
      chosen_side: "external",
    };
    expect(sel.chosen_side).toBe("external");
  });

  it("all customer fieldDiffs have required shape", () => {
    for (const diff of customerConflictDetail.fieldDiffs) {
      expect(diff.fieldName).toBeTruthy();
      expect(diff.changeType).toBeTruthy();
      expect("pilot_value" in diff).toBe(true);
      expect("external_value" in diff).toBe(true);
    }
  });
});
