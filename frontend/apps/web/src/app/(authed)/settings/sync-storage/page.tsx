/**
 * /settings/sync-storage — Sync & Storage group landing
 *
 * Redirects to the first sub-page.
 */

import { redirect } from "next/navigation";

export default function SyncStoragePage() {
  redirect("/settings/sync-storage/background-sync");
}
