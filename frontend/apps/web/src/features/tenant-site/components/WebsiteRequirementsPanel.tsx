"use client";

/**
 * WebsiteRequirementsPanel — C-B16 strong TCR requirements warning
 *
 * Location: apps/web/src/features/tenant-site/components/WebsiteRequirementsPanel.tsx
 *
 * Shown wherever a self-managed URL is entered:
 *   1. Inside the Option 1 (Compliance Kit) card on Settings > Website
 *   2. Below the `website` field in the C-B9 10DLC profile form (§14)
 *
 * web spec §12: ShieldExclamationIcon, requirements list, PDF download link,
 * SelfHostEmailNotice (when requirements_emailed_at is non-null).
 * Design Decision #9: no resend button — one-time email by design.
 */

import React from "react";
import { DocumentArrowDownIcon, CheckIcon } from "@heroicons/react/24/outline";
import { ShieldExclamationIcon as ShieldExclamationIconSolid } from "@heroicons/react/24/solid";
import { SelfHostEmailNotice } from "./SelfHostEmailNotice";

interface WebsiteRequirementsPanelProps {
  /** ISO date string when the requirements email was sent (null = not sent) */
  requirementsEmailedAt?: string | null;
}

const REQUIREMENTS = [
  "A landing page with your business name and contact info visible",
  "A Privacy Policy page with SMS disclosure clauses (message types, frequency, message and data rates notice, STOP/HELP opt-out, no third-party mobile sharing)",
  "A Terms of Service page with SMS terms",
  "All pages accessible at a public URL (no login required)",
  "Pages that load on mobile devices",
];

export function WebsiteRequirementsPanel({
  requirementsEmailedAt,
}: WebsiteRequirementsPanelProps) {
  return (
    <div className="mt-4 flex items-start gap-3 rounded-lg border border-alert-200 bg-alert-50 p-4">
      <ShieldExclamationIconSolid
        className="h-6 w-6 shrink-0 text-alert-600"
        aria-hidden="true"
      />
      <div className="flex-1">
        <h4 className="text-sm font-semibold text-alert-700">
          TCR 10DLC Website Requirements
        </h4>
        <p className="mt-1 text-sm text-alert-700">
          To pass carrier vetting, your website must include:
        </p>
        <ul className="mt-2 space-y-1">
          {REQUIREMENTS.map((req, index) => (
            <li
              key={index}
              className="flex items-start gap-2 text-sm text-alert-700"
            >
              <CheckIcon
                className="mt-0.5 h-4 w-4 shrink-0 text-alert-600"
                aria-hidden="true"
              />
              <span>{req}</span>
            </li>
          ))}
        </ul>

        <div className="mt-3 flex flex-wrap items-center gap-4">
          <a
            href="/resources/tenant-website-requirements-v1.pdf"
            target="_blank"
            rel="noopener noreferrer"
            download
            className="inline-flex items-center gap-2 rounded py-1 text-sm font-medium text-brand-600 underline hover:text-brand-800 focus-visible:outline-2 focus-visible:outline-brand-400 focus-visible:outline-offset-2"
            data-testid="requirements-pdf-download"
          >
            <DocumentArrowDownIcon
              className="h-4 w-4 text-brand-600"
              aria-hidden="true"
            />
            Download Requirements Guide (PDF) →
          </a>
        </div>

        {requirementsEmailedAt && (
          <SelfHostEmailNotice requirementsEmailedAt={requirementsEmailedAt} />
        )}
      </div>
    </div>
  );
}
