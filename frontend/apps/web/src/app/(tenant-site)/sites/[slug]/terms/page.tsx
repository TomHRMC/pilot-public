/**
 * Tenant-site Terms of Service page — C-B16 public SSR
 *
 * Location: apps/web/src/app/(tenant-site)/sites/[slug]/terms/page.tsx
 *
 * Server component. Renders the terms of service from the published snapshot.
 * Contains the locked SMS terms + disclosure clauses.
 *
 * mkt spec §6.3: identical visual treatment to Privacy.
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
      title: `Terms of Service — ${site.display_name}`,
      description: `Terms of Service for ${site.display_name}, including SMS terms and conditions.`,
      robots: { index: true, follow: true },
    };
  } catch {
    return { title: "Page not found", robots: { index: false, follow: true } };
  }
}

export default async function TermsPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const site = await fetchTenantSite(slug);

  const termsPage = site.pages?.terms;
  if (!termsPage) {
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
        title={termsPage.title ?? "Terms of Service"}
        bodyParagraphs={termsPage.body_paragraphs}
        publishedAt={site.published_at}
        displayName={site.display_name}
      />
    </>
  );
}
