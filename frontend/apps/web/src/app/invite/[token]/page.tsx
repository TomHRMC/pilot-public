/**
 * Public Invite Landing Route — /invite/[token]
 *
 * Location: apps/web/src/app/invite/[token]/page.tsx
 *
 * Thin server shell — static metadata only. All data fetching happens
 * in the "use client" InviteLandingPage component via bare fetch()
 * (sanctioned unauthenticated-surface exception, same as PublicQuotePage).
 *
 * No auth, no app sidebar, no auth chrome.
 */

import React from "react";
import type { Metadata } from "next";
import { InviteLandingPage } from "@/features/users/components/InviteLandingPage";

interface InvitePageProps {
  params: Promise<{ token: string }>;
}

export const metadata: Metadata = {
  title: "You're Invited — Pilot for Trades",
  description: "Accept your invitation to join a Pilot for Trades team.",
  robots: { index: false, follow: false },
};

export default async function InvitePage({ params }: InvitePageProps) {
  const { token } = await params;
  return <InviteLandingPage token={token} />;
}
