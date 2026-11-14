/**
 * Redirects to unified notifications preferences page — UI-FIX-2C
 * Route: /settings/notifications/in-app
 */
import { redirect } from "next/navigation";

export default function NotificationInAppPage() {
  redirect("/settings/notifications/preferences");
}
