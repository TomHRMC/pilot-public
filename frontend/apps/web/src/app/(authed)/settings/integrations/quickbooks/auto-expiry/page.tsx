/**
 * /settings/integrations/quickbooks/auto-expiry — QB Auto-Expiry & Sync settings page
 *
 * Location: apps/web/src/app/(authed)/settings/integrations/quickbooks/auto-expiry/page.tsx
 *
 * Role gate: integrations.manage
 * Settings: B1–B4 (save-on-group-complete QB pairs),
 *           B5–B6 (pre-warning/auto-expire timing, blur + cross-field validation),
 *           B7–B8 (sync direction preferences, blur)
 */

import React from "react";
import { QbAutoExpirySyncPage } from "@/features/settings/components/QbAutoExpirySyncPage";

export default function QbAutoExpiryRoute() {
  return <QbAutoExpirySyncPage />;
}
