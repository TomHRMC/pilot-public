/**
 * BETA-B3 Permission additions test
 *
 * Verifies that the three new view permission keys added in BETA-B3 are
 * correctly assigned per the RBAC spec in Design Doc §C.2.
 *
 * PRD §3.5: technician role excludes financial admin permissions.
 * PRD §3.3: technician role includes customer view for field context.
 *
 * TEAM-INVITE-1 / ADR-0010: accountant (formerly operator) retains the
 * read-only view permissions (customers.view, quotes.view, invoices.view).
 */

import { ROLE_PERMISSION_MAP } from "../permissions";

describe("BETA-B3 permission additions", () => {
  it("technician role has customers.view", () => {
    expect(ROLE_PERMISSION_MAP.technician).toContain("customers.view");
  });

  it("technician role does NOT have quotes.view", () => {
    expect(ROLE_PERMISSION_MAP.technician).not.toContain("quotes.view");
  });

  it("technician role does NOT have invoices.view", () => {
    expect(ROLE_PERMISSION_MAP.technician).not.toContain("invoices.view");
  });

  it("owner has all three view permissions", () => {
    expect(ROLE_PERMISSION_MAP.owner).toContain("customers.view");
    expect(ROLE_PERMISSION_MAP.owner).toContain("quotes.view");
    expect(ROLE_PERMISSION_MAP.owner).toContain("invoices.view");
  });

  it("office_staff has all three view permissions", () => {
    expect(ROLE_PERMISSION_MAP.office_staff).toContain("customers.view");
    expect(ROLE_PERMISSION_MAP.office_staff).toContain("quotes.view");
    expect(ROLE_PERMISSION_MAP.office_staff).toContain("invoices.view");
  });

  it("accountant has all three view permissions (read-only set)", () => {
    expect(ROLE_PERMISSION_MAP.accountant).toContain("customers.view");
    expect(ROLE_PERMISSION_MAP.accountant).toContain("quotes.view");
    expect(ROLE_PERMISSION_MAP.accountant).toContain("invoices.view");
  });
});
