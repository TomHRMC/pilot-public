/**
 * /quotes/[id]/approve — Deep-link to quote in review mode
 *
 * Location: apps/web/src/app/(authed)/quotes/[id]/approve/page.tsx
 * Resolves to same QuoteDetailPage — the review mode bar activates
 * automatically when status === pending_approval and role === owner.
 */

import { redirect } from "next/navigation";

interface ApproveRouteProps {
  params: Promise<{ id: string }>;
}

export default async function ApproveRedirectRoute({
  params,
}: ApproveRouteProps) {
  const { id } = await params;
  redirect(`/quotes/${id}`);
}
