/**
 * Permissions Registry — single source of truth for RBAC
 *
 * Location: packages/ui/src/role-gate/permissions.ts
 *
 * All permission keys are defined here. Each batch extends this list
 * as new permissions are introduced. The ROLE_PERMISSION_MAP maps
 * each PilotRole to the set of permissions they hold.
 *
 * PLP-FIX-7: ROLE_PERMISSION_MAP is now the MOCK-MODE FALLBACK only.
 * The server-authoritative permission set (from GET /users/me/permissions)
 * is carried on PilotUser.permissions and checked via hasPermission().
 * The map is retained for mock-mode/test compatibility and as a defensive
 * fallback when user != null && permissions.length === 0.
 *
 * Design principle: hide-not-disable. Content is absent from DOM
 * for unauthorized roles — not merely visually hidden.
 */

import type { PilotRole } from "../auth/types";

/**
 * PLP-FIX-7: Wildcard permission matcher against the server-authoritative set.
 *
 * Contract:
 *   - `*` matches everything (owner's wildcard)
 *   - Exact match (e.g. `users.manage`)
 *   - `resource.*` prefix expansion (e.g. `customers.*` → `customers.view`,
 *     `customers.create`, etc.)
 *
 * @param perms - the server-set permission array from PilotUser.permissions
 * @param key   - the permission key to check (string — server may emit keys
 *                not in the PermissionKey union, e.g. `schedule.view_all`)
 */
export function hasPermission(perms: readonly string[], key: string): boolean {
  if (perms.includes("*")) return true;
  if (perms.includes(key)) return true;
  // Wildcard expansion — two patterns:
  // 1. resource.* → matches any key starting with "resource."
  //    (e.g. customers.* → customers.view, customers.create)
  // 2. *.suffix → matches any key ending with ".suffix"
  //    (e.g. *.view → customers.view, quotes.view, invoices.view)
  return perms.some((p) => {
    if (p.endsWith(".*")) {
      return key.startsWith(p.slice(0, -1));
    }
    if (p.startsWith("*.")) {
      return key.endsWith(p.slice(1));
    }
    return false;
  });
}

export type PermissionKey =
  | "quotes.approve"
  | "quotes.reject"
  | "quotes.kickback"
  | "dispatch.move"
  | "dispatch.assign"
  | "customers.delete"
  | "settings.manage"
  | "reports.view"
  // DEPRECATED (PLP-FIX-9): phantom key — no backend gate; use communications.view/send. Kept per additive-only rule.
  | "comms.send"
  | "invoices.approve"
  // BETA-B3 additions — view permission keys for list/index surfaces
  | "customers.view" // CRM list — all authenticated roles including technician (PRD §3.3)
  | "quotes.view" // Financial surface — owner, office_staff, accountant only; NOT technician (PRD §3.5)
  | "invoices.view" // Financial surface — owner, office_staff, accountant only; NOT technician (PRD §3.5)
  // BETA-B4 additions — settings, integrations, billing access
  | "integrations.manage" // Integrations settings — owner, accountant only
  | "settings.tenant.write" // Tenant-level settings write — owner, accountant only
  | "billing.view" // Subscription/billing view — owner, accountant only
  // FE-B18 additions — customer + site CRUD
  | "customers.create" // Create new customers — owner, office_staff, accountant
  | "customers.edit" // Edit existing customers — owner, office_staff, accountant
  | "sites.create" // Create new sites — owner, office_staff, accountant
  | "sites.edit" // Edit existing sites — owner, office_staff, accountant
  // FE-B19 additions — quote builder
  | "quotes.create" // Create new quotes — owner, office_staff, accountant
  | "quotes.edit" // Edit/send/convert quotes — owner, office_staff, accountant
  | "quote.submit_for_approval" // Technician: submit own quote for owner approval — technician only
  // FE-B20 additions — catalog management
  | "catalog.view" // View catalog (pricebook, labor rates, markups, supplier items) — all auth roles
  | "catalog.manage" // Create/edit pricebook items, set labor rates/markups — owner, accountant only
  // FE-B21 additions — jobs module
  | "jobs.edit" // Add time entries, expenses, change orders — owner, office_staff, accountant
  | "invoices.create" // Create invoices from completed jobs — owner, office_staff, accountant
  | "invoices.update" // BILLING-B1: Edit/activate payment schedules + invoice edits — owner only (ADR-0010)
  // FE-B26 additions — job creation
  | "jobs.create" // Create new jobs — owner, office_staff, accountant
  // FE-B31 additions — recurring jobs
  | "jobs.view" // View jobs list + recurring rules — owner, office_staff, accountant
  // UI-FIX-2B additions — multi-tech assignment
  | "schedule.manage" // Assign/remove technicians on jobs — owner, office_staff, accountant
  // TEAM-INVITE-1 additions — team invite management
  | "users.manage" // Invite/resend/revoke team invites + assign roles — owner only (ADR-0010)
  // PLP-FIX-7 additions — server-authoritative nav gating keys
  | "dashboard.manage" // Dashboard access — owner, office_staff, technician, accountant
  | "users.view" // View team members — owner, office_staff (read-only affordances gated users.manage)
  // PLP-FIX-9 additions — comms vocabulary reconciliation (INV-D-5) + self-service codes (INV-BUG-8)
  | "communications.view" // Comms read surfaces (nav, tab, widget) — office_staff (INV-D-5)
  | "communications.send" // Comms send affordances — office_staff (INV-D-5)
  | "mfa.enroll_self" // Self-service MFA enrollment — all non-owner roles (INV-BUG-8; PRD §3.2)
  | "account.session.view_own" // View own session history — all non-owner roles (INV-BUG-8)
  | "account.session.revoke_own" // Revoke own sessions — all non-owner roles (INV-BUG-8)
  | "help_chat.delete_own_history"; // Delete own help chat history — all non-owner roles (INV-BUG-8)
// Extended by each batch as new permissions are introduced
// NOTE: communications.manage is intentionally NOT in this union — thread lifecycle admin
// stays owner-only (design §G.1). Do not add it without a Tom ruling.

export const ROLE_PERMISSION_MAP: Record<PilotRole, Set<PermissionKey>> = {
  owner: new Set<PermissionKey>([
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
    // BETA-B3
    "customers.view",
    "quotes.view",
    "invoices.view",
    // BETA-B4
    "integrations.manage",
    "settings.tenant.write",
    "billing.view",
    // FE-B18
    "customers.create",
    "customers.edit",
    "sites.create",
    "sites.edit",
    // FE-B19
    "quotes.create",
    "quotes.edit",
    // FE-B20
    "catalog.view",
    "catalog.manage",
    // FE-B21
    "jobs.edit",
    "invoices.create",
    // BILLING-B1 — owner only (ADR-0010); office_staff is read-mostly for invoices
    "invoices.update",
    // FE-B26
    "jobs.create",
    // FE-B31
    "jobs.view",
    // UI-FIX-2B
    "schedule.manage",
    // PLP-FIX-11: schedule.view_all mirrored for owner (prod grant via *;
    // static map needs explicit key for mock-mode fallback / nav gate).
    "schedule.view_all" as PermissionKey,
    // TEAM-INVITE-1 — owner only (ADR-0010; mirrors BE require_permission("users.manage"))
    "users.manage",
    // PLP-FIX-7 — server-authoritative nav gating (mirrors prod grants)
    "dashboard.manage",
    "users.view",
    // PLP-FIX-9 (INV-D-5): owner gains comms vocabulary (BE gates are communications.*)
    "communications.view",
    "communications.send",
    // PLP-FIX-9 (INV-BUG-8): self-service codes (owner has all via wildcard in prod,
    // but the static map needs explicit keys for test/mock-mode fallback)
    "mfa.enroll_self",
    "account.session.view_own",
    "account.session.revoke_own",
    "help_chat.delete_own_history",
  ]),
  office_staff: new Set<PermissionKey>([
    "quotes.approve",
    "quotes.reject",
    "dispatch.assign",
    "customers.delete",
    "invoices.approve",
    "reports.view",
    // BETA-B3
    "customers.view",
    "quotes.view",
    "invoices.view",
    // FE-B18
    "customers.create",
    "customers.edit",
    "sites.create",
    "sites.edit",
    // FE-B19
    "quotes.create",
    "quotes.edit",
    // FE-B20 — office_staff can view catalog but NOT manage (no pricing authority)
    "catalog.view",
    // FE-B21
    "jobs.edit",
    "invoices.create",
    // FE-B31
    "jobs.view",
    // UI-FIX-2B
    "schedule.manage",
    // PLP-FIX-11: schedule.view_all mirrored for office_staff (prod grant;
    // already in MSW fixture). Needed so the Schedule nav gate (view_all)
    // passes for office_staff in mock-mode fallback.
    "schedule.view_all" as PermissionKey,
    // PLP-FIX-7 — server-authoritative nav gating (mirrors prod grants)
    "dashboard.manage",
    "users.view",
    // PLP-FIX-9 (INV-D-5): office_staff gains comms vocabulary (BE gates are communications.*)
    "communications.view",
    "communications.send",
    // PLP-FIX-9 (INV-BUG-8): self-service codes for all non-owner roles (PRD §3.2)
    "mfa.enroll_self",
    "account.session.view_own",
    "account.session.revoke_own",
    "help_chat.delete_own_history",
    // NOTE: comms.send (phantom key) removed — prod office_staff does NOT hold it.
    // The FE map now mirrors the server truth; comms nav uses communications.view.
  ]),
  technician: new Set<PermissionKey>([
    // PLP-FIX-7: comms.send removed — prod technician does NOT hold it.
    // BETA-B3 — technician gets customers.view (field context) but NOT quotes.view/invoices.view (financial)
    "customers.view",
    // FE-B18 — technician cannot create/edit customers or sites
    // FE-B19 — technician can submit their own quotes for approval but NOT create/edit/send
    "quote.submit_for_approval",
    // FE-B20 — technician can view catalog (price lookup) but NOT manage it
    "catalog.view",
    // PLP-FIX-7 — server-authoritative nav gating (mirrors prod grants)
    "dashboard.manage",
    "jobs.view",
    // PLP-FIX-9 (INV-BUG-8): self-service codes for all non-owner roles (PRD §3.2)
    "mfa.enroll_self",
    "account.session.view_own",
    "account.session.revoke_own",
    "help_chat.delete_own_history",
  ]),
  // TEAM-INVITE-1 / ADR-0010: accountant set REPLACED with the BE read-only shape.
  // The old "operator" manager set is gone — accountant is now read-only books & reports.
  // Cross-checked against the BE tenant_user_role accountant row (design §A table).
  accountant: new Set<PermissionKey>([
    "customers.view",
    "quotes.view",
    "invoices.view",
    "jobs.view",
    "reports.view",
    "catalog.view",
    // PLP-FIX-7 — server-authoritative nav gating (mirrors prod grants)
    "dashboard.manage",
    // PLP-FIX-11 (INV-BUG-18, Tom-ruled 2026-09-06): mock-mode fallback parity
    // with the seed grant — accountant gains schedule.view_all (read-only board
    // + Technicians box). schedule.manage is NOT granted (write stays
    // owner/office_staff). Local cast: schedule.view_all is not in the
    // PermissionKey union (server may emit keys outside it); do NOT add it to
    // the union — the static map is mock-mode fallback only.
    "schedule.view_all" as PermissionKey,
    // PLP-FIX-9 (INV-BUG-8): self-service codes for all non-owner roles (PRD §3.2)
    "mfa.enroll_self",
    "account.session.view_own",
    "account.session.revoke_own",
    "help_chat.delete_own_history",
  ]),
};
