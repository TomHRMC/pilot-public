/**
 * Tenant Notification Defaults Route — FE-UI-NAV-S1
 *
 * Route: /settings/notifications/tenant-defaults
 *
 * Owner-only page for setting tenant-level notification defaults.
 * Non-owner roles: RoleGate hides the content (hide-not-disable RBAC).
 *
 * Design spec §29.4 — standalone page, no tab strip.
 * Accessible via Settings Index → Workspace → Notifications card.
 *
 * MUST be "use client" — RoleGate calls useAuth() → useContext() which is
 * illegal in React Server Components. Without this directive Next.js renders
 * this as an RSC, producing:
 *   TypeError: useContext is not a function
 */

"use client";

import { RoleGate } from "@pilot/ui/role-gate";
import { TenantNotificationDefaultsPage } from "@/features/settings/components/TenantNotificationDefaultsPage";

export default function TenantNotificationDefaultsRoute() {
  return (
    <RoleGate permission="settings.tenant.write">
      <TenantNotificationDefaultsPage />
    </RoleGate>
  );
}
