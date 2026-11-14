/**
 * /quotes/pending — Owner pending quotes approval inbox
 *
 * Location: apps/web/src/app/(authed)/quotes/pending/page.tsx
 * Gate: owner role (enforced in PendingQuotesInboxPage)
 */

import { PendingQuotesInboxPage } from "@/features/quote-approval/PendingQuotesInboxPage";

export default function PendingQuotesRoute() {
  return <PendingQuotesInboxPage />;
}

export const metadata = {
  title: "Pending Approval | Pilot",
};
