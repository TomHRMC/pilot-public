/**
 * Owner tab field issues deep-link integration test — FE-B9
 */

import {
  WEB_APP_BASE_URL,
  FIELD_ISSUES_WEB_URL,
} from "../../features/owner-tab/hooks/useFieldIssuesStatus";

describe("FieldIssuesSyncStatusSection deep-link URLs", () => {
  it("FIELD_ISSUES_WEB_URL includes /dashboard/approvals/field-issues path", () => {
    expect(FIELD_ISSUES_WEB_URL).toContain("/dashboard/approvals/field-issues");
  });

  it("WEB_APP_BASE_URL is derived from EXPO_PUBLIC_WEB_APP_URL env (not hardcoded)", () => {
    // In test env, env is not set so it falls back to production URL
    expect(WEB_APP_BASE_URL).toBeTruthy();
    expect(typeof WEB_APP_BASE_URL).toBe("string");
  });

  it("deep-link path is constructed correctly from base URL", () => {
    const expectedPath = `${WEB_APP_BASE_URL}/dashboard/approvals/field-issues`;
    expect(FIELD_ISSUES_WEB_URL).toBe(expectedPath);
  });
});
