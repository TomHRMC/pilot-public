/**
 * New Quote route — thin server component
 *
 * Location: apps/web/src/app/(authed)/quotes/new/page.tsx
 *
 * No "use client" — this is a server component.
 * All interactivity lives in QuoteCreatePage ("use client").
 */

import { QuoteCreatePage } from "@/features/quotes/components/QuoteCreatePage";

export const metadata = { title: "New Quote | Pilot" };

export default function NewQuotePage() {
  return <QuoteCreatePage />;
}
