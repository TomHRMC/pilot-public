/**
 * /settings/my-account — index redirect
 *
 * No content lives at this level. Redirect immediately to the Profile
 * sub-page, which is the canonical landing point for "My Account".
 */

import { redirect } from "next/navigation";

export default function MyAccountIndexPage() {
  redirect("/settings/my-account/profile");
}
