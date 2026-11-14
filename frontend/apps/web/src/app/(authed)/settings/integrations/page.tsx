/**
 * /settings/integrations — index redirect
 *
 * Redirects to the General integrations sub-page.
 */

import { redirect } from "next/navigation";

export default function IntegrationsIndexPage() {
  redirect("/settings/integrations/general");
}
