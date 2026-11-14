/**
 * Redirects to unified notifications preferences page — UI-FIX-2C
 * Route: /settings/notifications/sms
 */
import { redirect } from "next/navigation";

export default function NotificationSmsPage() {
  redirect("/settings/notifications/preferences");
}
