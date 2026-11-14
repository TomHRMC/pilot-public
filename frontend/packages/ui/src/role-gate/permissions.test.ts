/**
 * permissions.ts unit tests
 *
 * Location: packages/ui/src/role-gate/permissions.test.ts
 *
 * Updated in BETA-B3: added customers.view, quotes.view, invoices.view to ALL_PERMISSIONS.
 * Technician role now has 2 permissions: comms.send + customers.view (field context per PRD §3.3).
 * Technician role does NOT have quotes.view or invoices.view (financial exclusion per PRD §3.5).
 *
 * TEAM-INVITE-1 / ADR-0010: role keys renamed tech→technician, operator→accountant.
 */

import { describe, it, expect } from "vitest";
import { ROLE_PERMISSION_MAP } from "./permissions";
import type { PermissionKey } from "./permissions";

const ALL_PERMISSIONS: PermissionKey[] = [
  "quotes.approve",
  "quotes.reject",
  "quotes.kickback",
  "dispatch.move",
  "dispatch.assign",
  "customers.delete",
  "settings.manage",
  "reports.view",
  "comms.send",
  "invoices.approve",
  // BETA-B3 additions
  "customers.view",
  "quotes.view",
  "invoices.view",
];

describe("ROLE_PERMISSION_MAP", () => {
  it("owner has all permissions", () => {
    for (const perm of ALL_PERMISSIONS) {
      expect(ROLE_PERMISSION_MAP.owner.has(perm)).toBe(true);
    }
  });

  // PLP-FIX-7: technician set updated to mirror prod grants.
  // Removed comms.send; added dashboard.manage + jobs.view.
  it("technician has customers.view, quote.submit_for_approval, catalog.view, dashboard.manage, and jobs.view (PLP-FIX-7)", () => {
    expect(ROLE_PERMISSION_MAP.technician.has("comms.send")).toBe(false);
    expect(ROLE_PERMISSION_MAP.technician.has("customers.view")).toBe(true);
    expect(
      ROLE_PERMISSION_MAP.technician.has("quote.submit_for_approval"),
    ).toBe(true);
    expect(ROLE_PERMISSION_MAP.technician.has("catalog.view")).toBe(true);
    expect(ROLE_PERMISSION_MAP.technician.has("dashboard.manage")).toBe(true);
    expect(ROLE_PERMISSION_MAP.technician.has("jobs.view")).toBe(true);
    // PLP-FIX-9: technician now has 9 permissions (5 + 4 self-service codes per INV-BUG-8)
    expect(ROLE_PERMISSION_MAP.technician.size).toBe(9);
  });

  it("technician does NOT have financial view permissions (PRD §3.5)", () => {
    expect(ROLE_PERMISSION_MAP.technician.has("quotes.view")).toBe(false);
    expect(ROLE_PERMISSION_MAP.technician.has("invoices.view")).toBe(false);
  });

  it("office_staff does not have settings.manage", () => {
    expect(ROLE_PERMISSION_MAP.office_staff.has("settings.manage")).toBe(false);
  });
});
