/**
 * SettingsShell — FE-B11
 *
 * Location: apps/web/src/features/settings/components/SettingsShell.tsx
 *
 * Top-level settings layout: left sidebar (11 group items + SettingsSidebarSearch),
 * right content area. Sidebar items are role-gated per IA framework Decision 8
 * (hide-not-disable).
 *
 * Breadcrumb is rendered above the content area.
 * Tokens: all from pilotPreset — zero hardcoded colors.
 */

import React from "react";
import type { CatalogEntry } from "@pilot/ui";
import { SettingsSidebar } from "./SettingsSidebar";
import { SettingsBreadcrumb } from "./SettingsBreadcrumb";

interface SettingsShellProps {
  children: React.ReactNode;
  catalog?: CatalogEntry[];
  testID?: string;
}

export function SettingsShell({
  children,
  catalog = [],
  testID,
}: SettingsShellProps) {
  return (
    <div
      className="flex h-full min-h-0 flex-1 bg-neutral-50"
      data-testid={testID ?? "settings-shell"}
    >
      {/* Left sidebar — second-level settings nav */}
      <aside className="hidden border-r border-neutral-200 bg-white lg:flex">
        <SettingsSidebar
          catalog={catalog}
          testID={testID ? `${testID}-sidebar` : "settings-sidebar"}
        />
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl px-6 py-8 space-y-6">
          <SettingsBreadcrumb />
          {children}
        </div>
      </main>
    </div>
  );
}
