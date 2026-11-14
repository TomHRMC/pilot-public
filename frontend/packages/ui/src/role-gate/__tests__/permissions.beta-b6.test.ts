/**
 * BETA-B6: permissions.ts unit tests
 *
 * Location: packages/ui/src/role-gate/__tests__/permissions.beta-b6.test.ts
 *
 * Verifies that reports.view is correctly assigned across roles.
 * `reports.view` already existed in permissions.ts prior to BETA-B6 —
 * these tests confirm the assignment is correct per PRD §3.5.
 *
 * Rule: technician does NOT have financial/reporting visibility.
 * Rule: owner, office_staff, accountant DO have reports.view.
 *
 * TEAM-INVITE-1 / ADR-0010: accountant set REPLACED with read-only shape.
 * Accountant HAS reports.view (read-only) but does NOT have settings.tenant.write.
 */

import { describe, it, expect } from "vitest";
import { ROLE_PERMISSION_MAP } from "../permissions";

describe("BETA-B6 — reports.view permission assignment", () => {
  it("technician does NOT have reports.view", () => {
    expect(ROLE_PERMISSION_MAP.technician.has("reports.view")).toBe(false);
  });

  it("owner has reports.view", () => {
    expect(ROLE_PERMISSION_MAP.owner.has("reports.view")).toBe(true);
  });

  it("office_staff has reports.view", () => {
    expect(ROLE_PERMISSION_MAP.office_staff.has("reports.view")).toBe(true);
  });

  it("accountant has reports.view (read-only set)", () => {
    expect(ROLE_PERMISSION_MAP.accountant.has("reports.view")).toBe(true);
  });

  it("technician does NOT have settings.tenant.write (Operations/Sync guard)", () => {
    expect(ROLE_PERMISSION_MAP.technician.has("settings.tenant.write")).toBe(
      false,
    );
  });

  it("office_staff does NOT have settings.tenant.write (Operations/Sync guard)", () => {
    expect(ROLE_PERMISSION_MAP.office_staff.has("settings.tenant.write")).toBe(
      false,
    );
  });

  it("owner has settings.tenant.write (Operations/Sync access)", () => {
    expect(ROLE_PERMISSION_MAP.owner.has("settings.tenant.write")).toBe(true);
  });

  it("accountant does NOT have settings.tenant.write (read-only set)", () => {
    expect(ROLE_PERMISSION_MAP.accountant.has("settings.tenant.write")).toBe(
      false,
    );
  });
});
