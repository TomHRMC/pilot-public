/**
 * /settings/operations/margin-buckets — Margin Buckets settings page
 *
 * Location: apps/web/src/app/(authed)/settings/operations/margin-buckets/page.tsx
 *
 * Role gate: settings.tenant.write
 * Settings: G1 (margin_bucket_boundaries — explicit save), G2 (low_margin_threshold_pct — blur)
 */

import React from "react";
import { MarginBucketsPage } from "@/features/settings-operations/components/MarginBucketsPage";

export default function MarginBucketsRoute() {
  return <MarginBucketsPage />;
}
