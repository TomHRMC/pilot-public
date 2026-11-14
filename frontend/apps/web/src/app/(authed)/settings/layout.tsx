/**
 * Settings layout — FE-UI-NAV-S1
 *
 * Location: apps/web/src/app/(authed)/settings/layout.tsx
 *
 * FE-UI-NAV-S1: SettingsShell (second sidebar + SettingsSidebar) removed.
 * Settings sub-pages now render directly inside AuthedLayout.
 * SettingsBreadcrumb is rendered inline per sub-page for context navigation.
 *
 * Previous behavior (FE-B11): SettingsShell wrapped all routes with a
 * second sidebar (SettingsSidebar). This created a double-sidebar layout
 * consuming 480px of chrome at 1280px viewport.
 *
 * New behavior: content renders in a max-w-3xl container with breadcrumb.
 * The /settings route (SettingsIndexPage) has its own full-width layout.
 */

"use client";

import React from "react";
import { usePathname } from "next/navigation";
import { SettingsBreadcrumb } from "@/features/settings/components/SettingsBreadcrumb";

interface SettingsLayoutProps {
  children: React.ReactNode;
}

export default function SettingsLayout({ children }: SettingsLayoutProps) {
  const pathname = usePathname();

  // /settings index page has its own full-width layout (SettingsIndexPage)
  // Sub-pages get the breadcrumb + max-w-3xl container
  const isIndexPage = pathname === "/settings";

  if (isIndexPage) {
    return <>{children}</>;
  }

  return (
    <div className="flex-1 bg-neutral-50 overflow-y-auto">
      <div className="mx-auto max-w-3xl px-6 py-8 space-y-6">
        <SettingsBreadcrumb />
        {children}
      </div>
    </div>
  );
}
