/**
 * Payment Method — UI-FIX-2F
 *
 * Route: /settings/billing/payment-method
 *
 * Intentionally placed in (profile-pages) route group — NOT under
 * (authed)/settings/ — so this page inherits only the main (authed)/layout.tsx
 * (top nav) and skips the SettingsShell sidebar entirely. This matches the
 * "full-page" UX spec for pages reachable from the Profile dropdown.
 *
 * All logic lives in PaymentMethodSettingsPage.
 */

import { PaymentMethodSettingsPage } from "@/features/settings/components/PaymentMethodSettingsPage";

export default function PaymentMethodPage() {
  return <PaymentMethodSettingsPage />;
}
