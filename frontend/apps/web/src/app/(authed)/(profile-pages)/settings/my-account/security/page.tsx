/**
 * My Account > Security Index Page — BETA-B4 / STEP 1
 *
 * Route: /settings/my-account/security
 *
 * Intentionally placed in (profile-pages) route group — NOT under
 * (authed)/settings/ — so this page inherits only the main (authed)/layout.tsx
 * (top nav) and skips the SettingsShell sidebar entirely. This matches the
 * "full-page" UX spec for pages reachable from the Profile dropdown.
 *
 * Thin route file — delegates to SecurityIndexPage feature component.
 */

"use client";

import React from "react";
import { SecurityIndexPage } from "@/features/account-settings/components/SecurityIndexPage";
import { SettingsBreadcrumb } from "@/features/settings/components/SettingsBreadcrumb";

export default function MyAccountSecurityIndexPage() {
  return (
    <>
      {/* Breadcrumb strip — SecurityIndexPage supplies its own p-6 max-w-2xl */}
      <div className="max-w-2xl px-6 pt-6">
        <SettingsBreadcrumb />
      </div>
      <SecurityIndexPage />
    </>
  );
}
