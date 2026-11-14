"use client";

/**
 * SettingsGearIcon — header settings button
 *
 * Location: apps/web/src/components/SettingsGearIcon.tsx
 *
 * UI-FIX-2E: Cog6ToothIcon in header. Active when pathname starts with /settings.
 * Navigates to /settings on click.
 */

import { Cog6ToothIcon } from "@heroicons/react/24/outline";
import { usePathname, useRouter } from "next/navigation";

export function SettingsGearIcon() {
  const pathname = usePathname();
  const router = useRouter();
  const isActive = pathname.startsWith("/settings");

  return (
    <button
      type="button"
      onClick={() => router.push("/settings")}
      title="Settings"
      aria-label="Settings"
      aria-current={isActive ? "page" : undefined}
      className={`flex items-center justify-center w-9 h-9 rounded-md transition-colors duration-150 ${
        isActive
          ? "bg-brand-50 text-brand-600 hover:bg-brand-100 hover:text-brand-700"
          : "text-neutral-500 hover:bg-neutral-100 hover:text-neutral-700"
      }`}
    >
      <Cog6ToothIcon className="w-5 h-5" aria-hidden="true" />
    </button>
  );
}
