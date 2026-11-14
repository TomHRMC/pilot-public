/**
 * PLP-FIX-7 MSW Handlers — users/me/permissions
 *
 * Location: apps/web/src/mocks/handlers/userPermissionsHandlers.ts
 *
 * Mocks GET /api/v1/users/me/permissions with the seed-verified grant arrays
 * from design §A. These mirror the real tenant_user_role.permissions jsonb
 * rows so the FE server-authoritative gating path works correctly in tests.
 *
 * office_staff includes jobs.view (Part A's converge — fixtures lead the
 * planned rollout per design §C.1).
 */

import { http, HttpResponse } from "msw";

// ── Designed permission sets (design §A) ─────────────────────────────────────

const ROLE_PERMISSIONS: Record<string, string[]> = {
  owner: [
    "*",
    "users.manage",
    "users.view",
    "integrations.manage",
    "jobs.loto_confirm",
  ],
  office_staff: [
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
    // PLP-FIX-7 Part A converge — office_staff gains jobs.view
    "jobs.view",
    // PLP-FIX-9 (INV-D-5): office_staff gains comms vocabulary (BE gates are communications.*)
    "communications.view",
    "communications.send",
    // PLP-FIX-9 (INV-BUG-8): self-service codes for all non-owner roles (PRD §3.2)
    "mfa.enroll_self",
    "account.session.view_own",
    "account.session.revoke_own",
    "help_chat.delete_own_history",
  ],
  technician: [
    "dashboard.manage",
    "expenses.*",
    "jobs.update",
    "jobs.view",
    "mobile_sync.*",
    "nec.calculate",
    "schedule.view_own",
    "time_entries.*",
    "voice.*",
    "jobs.loto_confirm",
    // PLP-FIX-9 (INV-BUG-8): self-service codes for all non-owner roles (PRD §3.2)
    "mfa.enroll_self",
    "account.session.view_own",
    "account.session.revoke_own",
    "help_chat.delete_own_history",
  ],
  accountant: [
    "audit.view",
    "dashboard.manage",
    "reports.view",
    "*.view",
    "catalog.manage",
    // PLP-FIX-11 (INV-BUG-18, Tom-ruled 2026-09-06): mirrors the Part A seed
    // converge — accountant gains schedule.view_all (read-only board +
    // Technicians box). Fixtures lead the planned rollout per FIX-7 §C.1.
    // schedule.manage is NOT granted (write stays owner/office_staff).
    "schedule.view_all",
    // PLP-FIX-9 (INV-BUG-8): self-service codes for all non-owner roles (PRD §3.2)
    "mfa.enroll_self",
    "account.session.view_own",
    "account.session.revoke_own",
    "help_chat.delete_own_history",
  ],
};

// ── Handler ──────────────────────────────────────────────────────────────────

export const userPermissionsHandlers = [
  http.get("/api/v1/users/me/permissions", ({ request }) => {
    // Read the Authorization header to determine which mock user to return.
    // In test mode, the token is "tok" or "mock-token" — we default to owner.
    // Tests that need a specific role override this handler via server.use().
    const auth = request.headers.get("Authorization") ?? "";
    const token = auth.replace("Bearer ", "");

    // Default to owner for the standard mock token
    const roleCode = token.includes("office") ? "office_staff" : "owner";
    const permissions = ROLE_PERMISSIONS[roleCode] ?? ROLE_PERMISSIONS.owner;

    return HttpResponse.json({
      user_id: "mock-user-001",
      tenant_id: "mock-tenant-001",
      role_code: roleCode,
      role_name: roleCode
        .replace("_", " ")
        .replace(/\b\w/g, (c) => c.toUpperCase()),
      permissions,
    });
  }),
];
