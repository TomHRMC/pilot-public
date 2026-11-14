/**
 * Tenant Security & MFA Policy — BETA-B4 / STEP 2
 *
 * Route: /settings/security
 * Thin route file — delegates to TenantSecurityPage feature component.
 */

import { TenantSecurityPage } from "@/features/settings/components/TenantSecurityPage";

export default function SettingsSecurityPage() {
  return <TenantSecurityPage />;
}
