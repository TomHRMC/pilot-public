/**
 * Tenant-site Privacy Policy page — C-B16 public SSR
 *
 * Location: apps/web/src/app/(tenant-site)/sites/[slug]/privacy/page.tsx
 *
 * Server component. Renders the privacy policy from the published snapshot.
 * Contains the locked SMS disclosure clauses (message types, cadence, rates,
 * STOP/HELP, no-third-party-sharing).
 *
 * mkt spec §6.2: H1 = page title, last-updated line, body_paragraphs.
 * Design Decision #2: pre-escaped plain text — no markdown, no HTML injection.
 */

import React from "react";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { fetchTenantSite } from "@/lib/tenant-sites";
import { TenantSiteHeader } from "@/features/tenant-site-public/TenantSiteHeader";
import { LegalPageBody } from "@/features/tenant-site-public/LegalPageBody";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  try {
    const site = await fetchTenantSite(slug);
    return {
      title: `Privacy Policy — ${site.display_name}`,
      description: `Privacy Policy for ${site.display_name}, including SMS communications disclosure.`,
      robots: { index: true, follow: true },
    };
  } catch {
    return { title: "Page not found", robots: { index: false, follow: true } };
  }
}

export default async function PrivacyPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const site = await fetchTenantSite(slug);

  const privacyPage = site.pages?.privacy;
  if (!privacyPage) {
    notFound();
  }

  return (
    <>
      <TenantSiteHeader
        displayName={site.display_name}
        publicPhone={site.public_phone}
        publicCity={site.public_city}
        publicState={site.public_state}
        variant="legal"
      />
      <LegalPageBody
        title={privacyPage.title ?? "Privacy Policy"}
        bodyParagraphs={privacyPage.body_paragraphs}
        publishedAt={site.published_at}
        displayName={site.display_name}
      />
    </>
  );
}
