/**
 * Settings > Website page — C-B16
 *
 * Route: /settings/website
 *
 * Thin server component (RULE 9) — no "use client", no data fetching.
 * Renders TenantSiteSettingsForm which owns all logic.
 *
 * Design spec: batch-c-b16-web-ui-design-spec.md §1.1
 */

import { RoleGate } from "@pilot/ui";
import { TenantSiteSettingsForm } from "@/features/tenant-site/components/TenantSiteSettingsForm";

export const metadata = {
  title: "Website — Pilot",
};

export default function WebsiteSettingsPage() {
  return (
    <RoleGate permission="settings.manage">
      <TenantSiteSettingsForm />
    </RoleGate>
  );
}
