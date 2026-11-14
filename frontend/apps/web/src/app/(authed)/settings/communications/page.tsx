/**
 * Communications Settings Index — FE-B14
 *
 * Redirects to /settings/communications/email-branding (default sub-page).
 */

import { redirect } from "next/navigation";

export default function CommunicationsPage() {
  redirect("/settings/communications/email-branding");
}
