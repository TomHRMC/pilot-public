/**
 * Settings Page — FE-UI-NAV-S1
 *
 * Route: /settings
 *
 * Thin server component — no "use client", no data fetching.
 * Renders SettingsIndexPage (3-section Stripe/Clio card grid).
 *
 * Design spec §17.5, §29.3 (Option 3 — Settings Index Page pattern)
 */
import { SettingsIndexPage } from "@/features/settings/components/SettingsIndexPage";

export default function SettingsPage() {
  return <SettingsIndexPage />;
}
