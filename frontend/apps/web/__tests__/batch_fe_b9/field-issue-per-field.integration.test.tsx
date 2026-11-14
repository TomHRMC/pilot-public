/**
 * Field issue per-field resolution integration test — FE-B9
 */

import { timeEntryModifiedModifiedDetail } from "@/features/field-issues/mocks/fieldIssuesFixtures";
import type { PerFieldSelection } from "@pilot/ui";

describe("field issue per-field resolution", () => {
  it("modified_modified fixture has fieldDiffs for per-field picker", () => {
    expect(timeEntryModifiedModifiedDetail.fieldDiffs.length).toBeGreaterThan(
      0,
    );
  });

  it("PerFieldSelection type has fieldName and chosenSide", () => {
    const sel: PerFieldSelection = {
      fieldName: "duration_minutes",
      chosenSide: "tech",
    };
    expect(sel.fieldName).toBe("duration_minutes");
    expect(sel.chosenSide).toBe("tech");
  });

  it("per_field_selections array matches fieldDiffs count when fully selected", () => {
    const diffs = timeEntryModifiedModifiedDetail.fieldDiffs;
    const selections: PerFieldSelection[] = diffs.map((d) => ({
      fieldName: d.fieldName,
      chosenSide: "tech",
    }));
    expect(selections.length).toBe(diffs.length);
  });
});
