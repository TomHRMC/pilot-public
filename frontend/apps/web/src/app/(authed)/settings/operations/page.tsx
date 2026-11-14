/**
 * /settings/operations — Operations group landing
 *
 * Redirects to the first sub-page.
 */

import { redirect } from "next/navigation";

export default function OperationsPage() {
  redirect("/settings/operations/margin-buckets");
}
