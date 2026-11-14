/**
 * BETA-B4 Permission Additions — Unit Tests
 *
 * Location: packages/ui/src/role-gate/__tests__/permissions.beta-b4.test.ts
 *
 * Verifies that the three new BETA-B4 permission keys are correctly assigned
 * to owner and withheld from office_staff and technician.
 *
 * TEAM-INVITE-1 / ADR-0010: accountant set was REPLACED with the BE read-only
 * shape. Accountant no longer has integrations.manage, settings.tenant.write,
 * or billing.view — those are now owner-only (the old "operator" manager set
 * is gone).
 */

import { describe, it, expect } from "vitest";
import { ROLE_PERMISSION_MAP } from "../permissions";

describe("BETA-B4 permission additions", () => {
  it("owner has integrations.manage", () => {
    expect(ROLE_PERMISSION_MAP.owner.has("integrations.manage")).toBe(true);
  });

  it("office_staff does NOT have integrations.manage", () => {
    expect(ROLE_PERMISSION_MAP.office_staff.has("integrations.manage")).toBe(
      false,
    );
  });

  it("technician does NOT have integrations.manage", () => {
    expect(ROLE_PERMISSION_MAP.technician.has("integrations.manage")).toBe(
      false,
    );
  });

  it("owner has settings.tenant.write", () => {
    expect(ROLE_PERMISSION_MAP.owner.has("settings.tenant.write")).toBe(true);
  });

  it("office_staff does NOT have settings.tenant.write", () => {
    expect(ROLE_PERMISSION_MAP.office_staff.has("settings.tenant.write")).toBe(
      false,
    );
  });

  it("technician does NOT have settings.tenant.write", () => {
    expect(ROLE_PERMISSION_MAP.technician.has("settings.tenant.write")).toBe(
      false,
    );
  });

  it("owner has billing.view", () => {
    expect(ROLE_PERMISSION_MAP.owner.has("billing.view")).toBe(true);
  });

  it("office_staff does NOT have billing.view", () => {
    expect(ROLE_PERMISSION_MAP.office_staff.has("billing.view")).toBe(false);
  });

  it("technician does NOT have billing.view", () => {
    expect(ROLE_PERMISSION_MAP.technician.has("billing.view")).toBe(false);
  });

  // TEAM-INVITE-1 / ADR-0010: accountant is now read-only — does NOT have
  // the old operator manager permissions (integrations.manage, settings.tenant.write, billing.view)
  it("accountant does NOT have integrations.manage (read-only set)", () => {
    expect(ROLE_PERMISSION_MAP.accountant.has("integrations.manage")).toBe(
      false,
    );
  });

  it("accountant does NOT have settings.tenant.write (read-only set)", () => {
    expect(ROLE_PERMISSION_MAP.accountant.has("settings.tenant.write")).toBe(
      false,
    );
  });

  it("accountant does NOT have billing.view (read-only set)", () => {
    expect(ROLE_PERMISSION_MAP.accountant.has("billing.view")).toBe(false);
  });
});
