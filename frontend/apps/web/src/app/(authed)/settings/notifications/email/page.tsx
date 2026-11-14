/**
 * Redirects to unified notifications preferences page — UI-FIX-2C
 * Route: /settings/notifications/email
 */
import { redirect } from "next/navigation";

export default function NotificationEmailPage() {
  redirect("/settings/notifications/preferences");
}
