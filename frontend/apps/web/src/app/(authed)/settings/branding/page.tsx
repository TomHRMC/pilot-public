/**
 * Branding Redirect — BETA-B4 / STEP 10
 *
 * Route: /settings/branding
 * Server-side redirect to the full email branding page (FE-B14).
 * No "use client" — redirect() is a server-side Next.js function.
 */

import { redirect } from "next/navigation";

export default function BrandingPage() {
  redirect("/settings/communications/email-branding");
}
