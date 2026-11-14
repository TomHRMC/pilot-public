/**
 * /settings/sync-storage/background-sync — Background Sync settings page
 *
 * Location: apps/web/src/app/(authed)/settings/sync-storage/background-sync/page.tsx
 *
 * Role gate: settings.tenant.write
 * Settings: C1 (background_sync_enabled — EffectiveSettingDisplay),
 *           C2 (background_sync_wifi_only), C3 (battery_floor_pct),
 *           C4 (sync_interval_minutes) — all SettingControl blur
 */

import React from "react";
import { BackgroundSyncPage } from "@/features/settings-sync-storage/components/BackgroundSyncPage";

export default function BackgroundSyncRoute() {
  return <BackgroundSyncPage />;
}
