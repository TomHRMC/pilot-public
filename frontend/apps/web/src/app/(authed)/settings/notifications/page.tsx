/**
 * /settings/notifications — index redirect — UI-FIX-2C
 *
 * Redirects to the unified notifications preferences page.
 */

import { redirect } from "next/navigation";

export default function NotificationsIndexPage() {
  redirect("/settings/notifications/preferences");
}
