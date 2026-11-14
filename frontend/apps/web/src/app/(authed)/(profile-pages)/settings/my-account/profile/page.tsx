/**
 * Profile Settings Page — FE-B12
 *
 * Route: /settings/my-account/profile
 *
 * Intentionally placed in (profile-pages) route group — NOT under
 * (authed)/settings/ — so this page inherits only the main (authed)/layout.tsx
 * (top nav) and skips the SettingsShell sidebar entirely. This matches the
 * "full-page" UX spec for pages reachable from the Profile dropdown.
 */
"use client";
import React from "react";
import { ProfileSettingsForm } from "@/features/account-settings/components/ProfileSettingsForm";
import { SettingsBreadcrumb } from "@/features/settings/components/SettingsBreadcrumb";

export default function ProfilePage() {
  return (
    <div className="mx-auto max-w-2xl px-6 py-8">
      <div className="mb-4">
        <SettingsBreadcrumb />
      </div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-neutral-900">Account</h1>
        <p className="mt-1 text-sm text-neutral-500">
          Manage your personal information. Fields save automatically on blur.
        </p>
      </div>
      <ProfileSettingsForm />
    </div>
  );
}
