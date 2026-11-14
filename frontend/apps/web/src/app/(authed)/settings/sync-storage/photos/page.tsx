/**
 * /settings/sync-storage/photos — Photos settings page
 *
 * Settings: E1 (photo_upload_wifi_only), E2 (photo_max_resolution_px) — both blur
 */

import React from "react";
import { PhotosPage } from "@/features/settings-sync-storage/components/PhotosPage";

export default function PhotosRoute() {
  return <PhotosPage />;
}
