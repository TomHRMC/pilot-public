/**
 * LegalPageBody — C-B16 public tenant-site legal page body
 *
 * Location: apps/web/src/features/tenant-site-public/LegalPageBody.tsx
 *
 * Renders body_paragraphs for Privacy/Terms pages. The payload is pre-escaped
 * plain text (Design Decision #2) — no markdown parser, no dangerouslySetInnerHTML.
 * Server component.
 *
 * mkt spec §6.2/§6.3: text-body-lg text-neutral-700 space-y-4, max-w-2xl.
 * Last-updated line uses text-neutral-500 (4.8:1 AA — mkt spec §14.2 approval).
 */

import React from "react";
import Link from "next/link";

interface LegalPageBodyProps {
  title: string;
  bodyParagraphs: string[];
  publishedAt?: string | null;
  displayName: string;
}

function formatLastUpdated(isoDate: string): string {
  try {
    const date = new Date(isoDate);
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  } catch {
    return isoDate;
  }
}

export function LegalPageBody({
  title,
  bodyParagraphs,
  publishedAt,
  displayName,
}: LegalPageBodyProps) {
  return (
    <main id="main-content" className="mx-auto max-w-2xl px-6 py-8">
      <h1 className="text-xl font-bold text-neutral-800">{title}</h1>

      {publishedAt && (
        <p className="mb-6 mt-2 text-caption text-neutral-500">
          Last updated:{" "}
          <time dateTime={publishedAt}>{formatLastUpdated(publishedAt)}</time>
        </p>
      )}

      <div className="space-y-4">
        {bodyParagraphs.map((paragraph, index) => (
          <p key={index} className="text-body-lg text-neutral-700">
            {paragraph}
          </p>
        ))}
      </div>

      <Link
        href="/"
        className="mt-8 inline-block py-1 text-body text-brand-600 underline hover:text-brand-800 focus-visible:outline-2 focus-visible:outline-brand-400 focus-visible:outline-offset-2 focus-visible:rounded-sm"
      >
        ← Back to {displayName}
      </Link>
    </main>
  );
}
