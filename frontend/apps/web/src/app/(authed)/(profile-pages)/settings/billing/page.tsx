/**
 * Billing & Subscription — BETA-B4 / STEP 4
 *
 * Route: /settings/billing
 *
 * Intentionally placed in (profile-pages) route group — NOT under
 * (authed)/settings/ — so this page inherits only the main (authed)/layout.tsx
 * (top nav) and skips the SettingsShell sidebar entirely. This matches the
 * "full-page" UX spec for pages reachable from the Profile dropdown.
 */

import { BillingSettingsPage } from "@/features/settings/components/BillingSettingsPage";

export default function SettingsBillingPage() {
  return <BillingSettingsPage />;
}
