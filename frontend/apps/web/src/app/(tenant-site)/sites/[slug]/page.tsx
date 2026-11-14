/**
 * Tenant-site landing page — C-B16 public SSR
 *
 * Location: apps/web/src/app/(tenant-site)/sites/[slug]/page.tsx
 *
 * Server component. Fetches the published snapshot and renders the business-
 * identity landing page (About/Contact evidence for TCR vetting).
 *
 * mkt spec §5: accent bar, business name H1 (text-2xl font-bold), tagline,
 * contact line, "About this business" H2, body_paragraphs, legal links.
 * Design Decision #2: body_paragraphs are pre-escaped plain text.
 */

import React from "react";
import type { Metadata } from "next";
import { fetchTenantSite } from "@/lib/tenant-sites";
import { TenantSiteHeader } from "@/features/tenant-site-public/TenantSiteHeader";
import { LegalLinks } from "@/features/tenant-site-public/LegalLinks";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  try {
    const site = await fetchTenantSite(slug);
    const title =
      `${site.display_name} — ${site.public_city ?? ""}, ${site.public_state ?? ""}`.replace(
        " — , ",
        " — ",
      );
    const description =
      `${site.display_name} — ${site.tagline ?? `Electrical contractor in ${site.public_city ?? ""}, ${site.public_state ?? ""}`.trim()}. Contact: ${site.public_phone ?? site.public_email ?? ""}.`.trim();
    const domain = process.env.NEXT_PUBLIC_TENANT_SITES_DOMAIN ?? "localhost";
    return {
      title,
      description,
      robots: { index: true, follow: true },
      alternates: {
        canonical: `https://${slug}.${domain}/`,
      },
    };
  } catch {
    return { title: "Page not found", robots: { index: false, follow: true } };
  }
}

export default async function TenantSiteLandingPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const site = await fetchTenantSite(slug);

  const landingPage = site.pages?.landing;
  const bodyParagraphs = landingPage?.body_paragraphs ?? [];

  return (
    <>
      <TenantSiteHeader
        displayName={site.display_name}
        tagline={site.tagline}
        publicPhone={site.public_phone}
        publicEmail={site.public_email}
        publicCity={site.public_city}
        publicState={site.public_state}
        publicAddressLine1={site.public_address_line1}
        publicPostalCode={site.public_postal_code}
        showFullAddress={false}
        variant="landing"
      />

      <main
        id="main-content"
        className="mx-auto max-w-2xl border-t border-neutral-200 px-6 py-8"
      >
        <h2 className="mb-4 text-h2 font-medium text-neutral-800">
          About this business
        </h2>

        <div className="space-y-4">
          {bodyParagraphs.map((paragraph, index) => (
            <p key={index} className="text-body-lg text-neutral-700">
              {paragraph}
            </p>
          ))}
        </div>

        <LegalLinks />
      </main>
    </>
  );
}
