/**
 * PLP-FIX-9 Permission Unit Tests
 *
 * Location: packages/ui/src/role-gate/__tests__/permissions.plp-fix-9.test.ts
 *
 * One assertion per role per new key:
 *   - office_staff has all 6 incl. communications.view/send, NOT communications.manage
 *   - technician/accountant have the 4 self-service codes
 *   - comms.send still present in the union (deprecated, unused by maps)
 */

import { describe, it, expect } from "vitest";
import { ROLE_PERMISSION_MAP, hasPermission } from "../permissions";

describe("PLP-FIX-9 — new permission keys", () => {
  describe("office_staff (INV-D-5 + INV-BUG-8)", () => {
    it("has communications.view", () => {
      expect(ROLE_PERMISSION_MAP.office_staff.has("communications.view")).toBe(
        true,
      );
    });
    it("has communications.send", () => {
      expect(ROLE_PERMISSION_MAP.office_staff.has("communications.send")).toBe(
        true,
      );
    });
    it("does NOT have communications.manage", () => {
      expect(
        ROLE_PERMISSION_MAP.office_staff.has("communications.manage" as never),
      ).toBe(false);
    });
    it("has mfa.enroll_self", () => {
      expect(ROLE_PERMISSION_MAP.office_staff.has("mfa.enroll_self")).toBe(
        true,
      );
    });
    it("has account.session.view_own", () => {
      expect(
        ROLE_PERMISSION_MAP.office_staff.has("account.session.view_own"),
      ).toBe(true);
    });
    it("has account.session.revoke_own", () => {
      expect(
        ROLE_PERMISSION_MAP.office_staff.has("account.session.revoke_own"),
      ).toBe(true);
    });
    it("has help_chat.delete_own_history", () => {
      expect(
        ROLE_PERMISSION_MAP.office_staff.has("help_chat.delete_own_history"),
      ).toBe(true);
    });
  });

  describe("technician (INV-BUG-8 self-service codes)", () => {
    it("has mfa.enroll_self", () => {
      expect(ROLE_PERMISSION_MAP.technician.has("mfa.enroll_self")).toBe(true);
    });
    it("has account.session.view_own", () => {
      expect(
        ROLE_PERMISSION_MAP.technician.has("account.session.view_own"),
      ).toBe(true);
    });
    it("has account.session.revoke_own", () => {
      expect(
        ROLE_PERMISSION_MAP.technician.has("account.session.revoke_own"),
      ).toBe(true);
    });
    it("has help_chat.delete_own_history", () => {
      expect(
        ROLE_PERMISSION_MAP.technician.has("help_chat.delete_own_history"),
      ).toBe(true);
    });
    it("does NOT have communications.view", () => {
      expect(ROLE_PERMISSION_MAP.technician.has("communications.view")).toBe(
        false,
      );
    });
    it("does NOT have communications.send", () => {
      expect(ROLE_PERMISSION_MAP.technician.has("communications.send")).toBe(
        false,
      );
    });
  });

  describe("accountant (INV-BUG-8 self-service codes)", () => {
    it("has mfa.enroll_self", () => {
      expect(ROLE_PERMISSION_MAP.accountant.has("mfa.enroll_self")).toBe(true);
    });
    it("has account.session.view_own", () => {
      expect(
        ROLE_PERMISSION_MAP.accountant.has("account.session.view_own"),
      ).toBe(true);
    });
    it("has account.session.revoke_own", () => {
      expect(
        ROLE_PERMISSION_MAP.accountant.has("account.session.revoke_own"),
      ).toBe(true);
    });
    it("has help_chat.delete_own_history", () => {
      expect(
        ROLE_PERMISSION_MAP.accountant.has("help_chat.delete_own_history"),
      ).toBe(true);
    });
    it("does NOT have communications.view", () => {
      expect(ROLE_PERMISSION_MAP.accountant.has("communications.view")).toBe(
        false,
      );
    });
  });

  describe("owner (all new keys present in static map)", () => {
    it("has communications.view", () => {
      expect(ROLE_PERMISSION_MAP.owner.has("communications.view")).toBe(true);
    });
    it("has communications.send", () => {
      expect(ROLE_PERMISSION_MAP.owner.has("communications.send")).toBe(true);
    });
    it("has mfa.enroll_self", () => {
      expect(ROLE_PERMISSION_MAP.owner.has("mfa.enroll_self")).toBe(true);
    });
    it("has help_chat.delete_own_history", () => {
      expect(
        ROLE_PERMISSION_MAP.owner.has("help_chat.delete_own_history"),
      ).toBe(true);
    });
  });

  describe("comms.send deprecation (additive-only rule)", () => {
    it("comms.send is still in the owner set (deprecated, not removed)", () => {
      expect(ROLE_PERMISSION_MAP.owner.has("comms.send")).toBe(true);
    });
    it("hasPermission matches communications.view for office_staff perms", () => {
      const officePerms = Array.from(
        ROLE_PERMISSION_MAP.office_staff,
      ) as string[];
      expect(hasPermission(officePerms, "communications.view")).toBe(true);
    });
    it("hasPermission does NOT match communications.view for technician perms", () => {
      const techPerms = Array.from(ROLE_PERMISSION_MAP.technician) as string[];
      expect(hasPermission(techPerms, "communications.view")).toBe(false);
    });
  });
});
