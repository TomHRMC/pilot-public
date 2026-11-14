"use client";

/**
 * SitePreviewPanel — C-B16 §16.7 preview-before-publish
 *
 * Location: apps/web/src/features/tenant-site/components/SitePreviewPanel.tsx
 *
 * Server-data-driven preview of the snapshot payload (NOT an iframe).
 * Tabbed: Landing / Privacy Policy / Terms of Service.
 * Renders the same visual treatment as the public site.
 *
 * web spec §9: tab bar, preview content, preview note.
 * WCAG 2.4.3: role="tablist"/"tab"/"tabpanel", arrow keys.
 */

import React, { useState } from "react";
import {
  PhoneIcon,
  EnvelopeIcon,
  MapPinIcon,
  InformationCircleIcon,
} from "@heroicons/react/24/outline";

interface PreviewPage {
  heading?: string | null;
  title?: string | null;
  body_paragraphs: string[];
  contact_lines?: string[] | null;
}

interface SitePreviewPanelProps {
  displayName: string;
  tagline?: string | null;
  publicPhone?: string | null;
  publicEmail?: string | null;
  publicCity?: string | null;
  publicState?: string | null;
  slug: string;
  pages: {
    landing?: PreviewPage | null;
    privacy?: PreviewPage | null;
    terms?: PreviewPage | null;
  };
}

type TabKey = "landing" | "privacy" | "terms";

export function SitePreviewPanel({
  displayName,
  tagline,
  publicPhone,
  publicEmail,
  publicCity,
  publicState,
  slug,
  pages,
}: SitePreviewPanelProps) {
  const [activeTab, setActiveTab] = useState<TabKey>("landing");
  const domain = process.env.NEXT_PUBLIC_TENANT_SITES_DOMAIN ?? "localhost";

  const tabs: { key: TabKey; label: string }[] = [
    { key: "landing", label: "Landing" },
    { key: "privacy", label: "Privacy Policy" },
    { key: "terms", label: "Terms of Service" },
  ];

  const cityState = [publicCity, publicState].filter(Boolean).join(", ");

  return (
    <div
      className="rounded-xl border border-neutral-200 bg-white shadow-sm"
      data-testid="site-preview-panel"
    >
      {/* Tab bar */}
      <div
        role="tablist"
        aria-label="Preview pages"
        className="flex border-b border-neutral-200"
      >
        {tabs.map((tab) => (
          <button
            key={tab.key}
            role="tab"
            aria-selected={activeTab === tab.key}
            tabIndex={activeTab === tab.key ? 0 : -1}
            onClick={() => setActiveTab(tab.key)}
            onKeyDown={(e) => {
              if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
                e.preventDefault();
              }
            }}
            className={`border-b-2 px-4 py-2 text-sm font-medium focus-visible:outline-2 focus-visible:outline-brand-500 focus-visible:outline-inset ${
              activeTab === tab.key
                ? "border-brand-600 text-brand-700"
                : "border-transparent text-neutral-500 hover:text-neutral-700"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Preview content */}
      <div
        role="tabpanel"
        aria-labelledby={`tab-${activeTab}`}
        className="max-h-96 overflow-y-auto p-6"
      >
        {activeTab === "landing" && (
          <div>
            <div
              className="h-1.5 w-full rounded-t bg-brand-600"
              aria-hidden="true"
            />
            <h2 className="text-2xl font-bold text-neutral-800">
              {displayName}
            </h2>
            {tagline && (
              <p className="mt-1 text-body-lg text-neutral-600">{tagline}</p>
            )}

            {/* Contact line */}
            <div className="mt-4 space-y-1 text-body text-neutral-700">
              {publicPhone && (
                <div className="flex items-center gap-2">
                  <PhoneIcon
                    className="h-4 w-4 text-neutral-400"
                    aria-hidden="true"
                  />
                  <span>{publicPhone}</span>
                </div>
              )}
              {publicEmail && (
                <div className="flex items-center gap-2">
                  <EnvelopeIcon
                    className="h-4 w-4 text-neutral-400"
                    aria-hidden="true"
                  />
                  <span>{publicEmail}</span>
                </div>
              )}
              {cityState && (
                <div className="flex items-center gap-2">
                  <MapPinIcon
                    className="h-4 w-4 text-neutral-400"
                    aria-hidden="true"
                  />
                  <span className="text-neutral-600">{cityState}</span>
                </div>
              )}
            </div>

            <hr className="my-6 border-t border-neutral-200" />

            <h3 className="mb-4 text-h2 font-medium text-neutral-800">
              About this business
            </h3>
            <div className="space-y-4">
              {(pages.landing?.body_paragraphs ?? []).map((p, i) => (
                <p key={i} className="text-body-lg text-neutral-700">
                  {p}
                </p>
              ))}
            </div>

            <div className="mt-6 border-t border-neutral-200 pt-4">
              <p className="text-body text-brand-600 underline">
                Privacy Policy · Terms of Service
              </p>
            </div>
          </div>
        )}

        {activeTab === "privacy" && (
          <div>
            <h2 className="text-xl font-bold text-neutral-800">
              {pages.privacy?.title ?? "Privacy Policy"}
            </h2>
            <div className="mt-4 space-y-4">
              {(pages.privacy?.body_paragraphs ?? []).map((p, i) => (
                <p key={i} className="text-body-lg text-neutral-700">
                  {p}
                </p>
              ))}
            </div>
          </div>
        )}

        {activeTab === "terms" && (
          <div>
            <h2 className="text-xl font-bold text-neutral-800">
              {pages.terms?.title ?? "Terms of Service"}
            </h2>
            <div className="mt-4 space-y-4">
              {(pages.terms?.body_paragraphs ?? []).map((p, i) => (
                <p key={i} className="text-body-lg text-neutral-700">
                  {p}
                </p>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Preview note */}
      <div className="m-4 flex items-start gap-2 rounded-md border border-neutral-200 bg-neutral-50 p-3">
        <InformationCircleIcon
          className="h-4 w-4 shrink-0 text-neutral-400"
          aria-hidden="true"
        />
        <p className="text-xs text-neutral-600">
          This is a preview of what will go public when you publish. The URL
          will be https://{slug}.{domain}
        </p>
      </div>
    </div>
  );
}
