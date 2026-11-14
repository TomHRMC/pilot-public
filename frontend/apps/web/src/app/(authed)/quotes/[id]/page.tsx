/**
 * /quotes/[id] — Quote detail page (unified owner/tech view)
 *
 * Location: apps/web/src/app/(authed)/quotes/[id]/page.tsx
 */

import { QuoteDetailPage } from "@/features/quote-approval/QuoteDetailPage";

interface QuoteDetailRouteProps {
  params: Promise<{ id: string }>;
}

export default async function QuoteDetailRoute({
  params,
}: QuoteDetailRouteProps) {
  const { id } = await params;
  return <QuoteDetailPage quoteId={id} />;
}

export const metadata = {
  title: "Quote Detail | Pilot",
};
