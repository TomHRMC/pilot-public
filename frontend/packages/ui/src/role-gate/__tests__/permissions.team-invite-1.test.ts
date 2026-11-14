/**
 * TEAM-INVITE-1 Permission Tests
 *
 * Location: packages/ui/src/role-gate/__tests__/permissions.team-invite-1.test.ts
 *
 * Verifies the ADR-0010 RBAC reconciliation:
 *  - users.manage in owner set ONLY
 *  - users.manage NOT in technician/office_staff/accountant sets
 *  - accountant set contains the read-only keys (view family + reports)
 *  - accountant set contains NONE of the old operator manager keys
 *  - technician set deep-equals the old tech set (verbatim carryover)
 */

import { describe, it, expect } from "vitest";
import { ROLE_PERMISSION_MAP } from "../permissions";

describe("TEAM-INVITE-1 — users.manage permission", () => {
  it("owner has users.manage", () => {
    expect(ROLE_PERMISSION_MAP.owner.has("users.manage")).toBe(true);
  });

  it("technician does NOT have users.manage", () => {
    expect(ROLE_PERMISSION_MAP.technician.has("users.manage")).toBe(false);
  });

  it("office_staff does NOT have users.manage", () => {
    expect(ROLE_PERMISSION_MAP.office_staff.has("users.manage")).toBe(false);
  });

  it("accountant does NOT have users.manage", () => {
    expect(ROLE_PERMISSION_MAP.accountant.has("users.manage")).toBe(false);
  });
});

describe("TEAM-INVITE-1 — accountant read-only set (ADR-0010 replacement)", () => {
  it("accountant has customers.view", () => {
    expect(ROLE_PERMISSION_MAP.accountant.has("customers.view")).toBe(true);
  });

  it("accountant has quotes.view", () => {
    expect(ROLE_PERMISSION_MAP.accountant.has("quotes.view")).toBe(true);
  });

  it("accountant has invoices.view", () => {
    expect(ROLE_PERMISSION_MAP.accountant.has("invoices.view")).toBe(true);
  });

  it("accountant has jobs.view", () => {
    expect(ROLE_PERMISSION_MAP.accountant.has("jobs.view")).toBe(true);
  });

  it("accountant has reports.view", () => {
    expect(ROLE_PERMISSION_MAP.accountant.has("reports.view")).toBe(true);
  });

  it("accountant has catalog.view", () => {
    expect(ROLE_PERMISSION_MAP.accountant.has("catalog.view")).toBe(true);
  });

  // NONE of the old operator manager keys
  it("accountant does NOT have settings.manage", () => {
    expect(ROLE_PERMISSION_MAP.accountant.has("settings.manage")).toBe(false);
  });

  it("accountant does NOT have integrations.manage", () => {
    expect(ROLE_PERMISSION_MAP.accountant.has("integrations.manage")).toBe(
      false,
    );
  });

  it("accountant does NOT have settings.tenant.write", () => {
    expect(ROLE_PERMISSION_MAP.accountant.has("settings.tenant.write")).toBe(
      false,
    );
  });

  it("accountant does NOT have billing.view", () => {
    expect(ROLE_PERMISSION_MAP.accountant.has("billing.view")).toBe(false);
  });

  it("accountant does NOT have quotes.approve", () => {
    expect(ROLE_PERMISSION_MAP.accountant.has("quotes.approve")).toBe(false);
  });

  it("accountant does NOT have customers.delete", () => {
    expect(ROLE_PERMISSION_MAP.accountant.has("customers.delete")).toBe(false);
  });

  it("accountant does NOT have comms.send", () => {
    expect(ROLE_PERMISSION_MAP.accountant.has("comms.send")).toBe(false);
  });

  it("accountant does NOT have schedule.manage", () => {
    expect(ROLE_PERMISSION_MAP.accountant.has("schedule.manage")).toBe(false);
  });
});

describe("TEAM-INVITE-1 — technician set (PLP-FIX-7: mirrors prod grants)", () => {
  // PLP-FIX-7: technician no longer holds comms.send (prod grant set excludes it).
  it("technician does NOT have comms.send", () => {
    expect(ROLE_PERMISSION_MAP.technician.has("comms.send")).toBe(false);
  });

  it("technician has customers.view", () => {
    expect(ROLE_PERMISSION_MAP.technician.has("customers.view")).toBe(true);
  });

  it("technician has quote.submit_for_approval", () => {
    expect(
      ROLE_PERMISSION_MAP.technician.has("quote.submit_for_approval"),
    ).toBe(true);
  });

  it("technician has catalog.view", () => {
    expect(ROLE_PERMISSION_MAP.technician.has("catalog.view")).toBe(true);
  });

  // PLP-FIX-7: technician set updated to mirror prod grants.
  // Removed comms.send; added dashboard.manage + jobs.view.
  it("technician has exactly 9 permissions (PLP-FIX-7 + PLP-FIX-9 self-service codes)", () => {
    // PLP-FIX-9: 5 base + 4 self-service codes (mfa.enroll_self, account.session.*, help_chat.*)
    expect(ROLE_PERMISSION_MAP.technician.size).toBe(9);
  });
});
