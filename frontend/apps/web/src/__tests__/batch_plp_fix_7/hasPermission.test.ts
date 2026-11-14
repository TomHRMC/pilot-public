/**
 * PLP-FIX-7 Unit Tests — hasPermission wildcard matcher
 *
 * Location: apps/web/src/__tests__/batch_plp_fix_7/hasPermission.test.ts
 *
 * Tests the hasPermission() utility covering:
 *   - `*` match-all
 *   - exact match
 *   - `resource.*` prefix expansion
 *   - miss cases
 */

import { describe, it, expect } from "vitest";
import { hasPermission } from "@pilot/ui/role-gate";

describe("PLP-FIX-7 — hasPermission wildcard matcher", () => {
  it("returns true when perms contains '*' (owner wildcard)", () => {
    expect(hasPermission(["*"], "anything.view")).toBe(true);
    expect(hasPermission(["*"], "users.manage")).toBe(true);
    expect(hasPermission(["*"], "some.unknown.key")).toBe(true);
  });

  it("returns true for exact match", () => {
    expect(hasPermission(["reports.view", "users.view"], "reports.view")).toBe(
      true,
    );
    expect(hasPermission(["reports.view", "users.view"], "users.view")).toBe(
      true,
    );
  });

  it("returns true for resource.* prefix expansion", () => {
    expect(hasPermission(["customers.*"], "customers.view")).toBe(true);
    expect(hasPermission(["customers.*"], "customers.create")).toBe(true);
    expect(hasPermission(["customers.*"], "customers.delete")).toBe(true);
    expect(hasPermission(["quotes.*"], "quotes.view")).toBe(true);
    expect(hasPermission(["invoices.*"], "invoices.create")).toBe(true);
  });

  it("returns false for non-matching key", () => {
    expect(hasPermission(["reports.view"], "users.manage")).toBe(false);
    expect(hasPermission(["customers.*"], "invoices.view")).toBe(false);
    expect(hasPermission(["quotes.view"], "quotes.create")).toBe(false);
  });

  it("returns false for empty perms array", () => {
    expect(hasPermission([], "reports.view")).toBe(false);
    expect(hasPermission([], "*")).toBe(false);
  });

  it("handles mixed wildcard + exact perms correctly", () => {
    const officeStaffPerms = [
      "addresses.*",
      "contacts.*",
      "customers.*",
      "invoices.create",
      "invoices.view",
      "quotes.*",
      "reports.view",
      "sites.*",
      "users.view",
      "schedule.manage",
      "schedule.view_all",
      "dashboard.manage",
      "jobs.view",
    ];
    expect(hasPermission(officeStaffPerms, "customers.view")).toBe(true);
    expect(hasPermission(officeStaffPerms, "customers.create")).toBe(true);
    expect(hasPermission(officeStaffPerms, "quotes.approve")).toBe(true);
    expect(hasPermission(officeStaffPerms, "invoices.create")).toBe(true);
    expect(hasPermission(officeStaffPerms, "dashboard.manage")).toBe(true);
    expect(hasPermission(officeStaffPerms, "jobs.view")).toBe(true);
    expect(hasPermission(officeStaffPerms, "comms.send")).toBe(false);
    expect(hasPermission(officeStaffPerms, "users.manage")).toBe(false);
    expect(hasPermission(officeStaffPerms, "catalog.manage")).toBe(false);
  });

  it("handles accountant *.view wildcard", () => {
    const accountantPerms = [
      "audit.view",
      "dashboard.manage",
      "reports.view",
      "*.view",
      "catalog.manage",
    ];
    expect(hasPermission(accountantPerms, "customers.view")).toBe(true);
    expect(hasPermission(accountantPerms, "quotes.view")).toBe(true);
    expect(hasPermission(accountantPerms, "invoices.view")).toBe(true);
    expect(hasPermission(accountantPerms, "jobs.view")).toBe(true);
    // *.view does NOT match non-view keys
    expect(hasPermission(accountantPerms, "customers.create")).toBe(false);
    expect(hasPermission(accountantPerms, "users.manage")).toBe(false);
  });
});
