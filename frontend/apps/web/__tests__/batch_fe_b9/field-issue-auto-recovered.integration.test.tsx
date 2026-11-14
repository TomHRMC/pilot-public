/**
 * Field issue auto-recovered 409 integration test — FE-B9
 * 409 auto_recovered → success banner; no StalenessRefreshDialog
 */

import { fieldIssue409AutoRecovered } from "@/features/field-issues/mocks/fieldIssuesFixtures";

describe("field issue 409 auto_recovered", () => {
  it("auto_recovered 409 body has correct shape", () => {
    expect(fieldIssue409AutoRecovered.staleness_type).toBe("auto_recovered");
    expect(fieldIssue409AutoRecovered.message).toContain("auto-recovered");
  });

  it("auto_recovered message mentions tech name (Jake)", () => {
    expect(fieldIssue409AutoRecovered.message).toContain("Jake");
  });

  it("auto_recovered message does NOT have refreshed_issue", () => {
    expect(fieldIssue409AutoRecovered).not.toHaveProperty("refreshed_issue");
  });
});
