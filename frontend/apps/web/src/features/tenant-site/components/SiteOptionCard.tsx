"use client";

/**
 * SiteOptionCard — C-B16 selectable option card
 *
 * Location: apps/web/src/features/tenant-site/components/SiteOptionCard.tsx
 *
 * Radio-group semantics. Three options: Compliance Kit, Hosted Compliance
 * Site, Starter Site (deferred — disabled card per Design Decision #4).
 *
 * web spec §6.3: radio indicator, title, description, status badge, body.
 * WCAG 2.4.11/20.6: role="radiogroup", role="radio", aria-checked, arrow keys.
 */

import React from "react";
import { CheckCircleIcon as CheckCircleIconSolid } from "@heroicons/react/24/solid";

export type SiteOptionKind =
  | "compliance_kit"
  | "hosted_compliance"
  | "starter_site";

interface SiteOptionCardProps {
  kind: SiteOptionKind;
  title: string;
  description: string;
  selected: boolean;
  disabled?: boolean;
  statusBadge?: { text: string; className: string };
  onSelect: (kind: SiteOptionKind) => void;
  children?: React.ReactNode;
}

/** Unselected radio indicator — a hollow circle (Heroicons has no outline CircleIcon) */
function HollowCircleIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="9" />
    </svg>
  );
}

export function SiteOptionCard({
  kind,
  title,
  description,
  selected,
  disabled = false,
  statusBadge,
  onSelect,
  children,
}: SiteOptionCardProps) {
  if (disabled) {
    // Option 3 — disabled card (Design Decision #4)
    return (
      <div
        className="min-h-36 cursor-not-allowed rounded-xl border border-neutral-200 bg-neutral-50 p-6 opacity-75"
        aria-disabled="true"
        tabIndex={-1}
        data-testid={`site-option-card-${kind}`}
      >
        <div className="flex items-start gap-3">
          <HollowCircleIcon className="h-6 w-6 shrink-0 text-neutral-300" />
          <div className="flex-1">
            <div className="flex items-center justify-between">
              <h3 className="text-h3 font-medium text-neutral-900">{title}</h3>
              {statusBadge && (
                <span
                  className={`rounded px-2 py-0.5 text-caption font-medium ${statusBadge.className}`}
                >
                  {statusBadge.text}
                </span>
              )}
            </div>
            <p className="mt-1 text-body text-neutral-600">{description}</p>
            {children}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      role="radio"
      aria-checked={selected}
      aria-label={title}
      tabIndex={0}
      onClick={() => onSelect(kind)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect(kind);
        }
      }}
      className={`min-h-36 cursor-pointer rounded-xl border p-6 shadow-sm transition-colors duration-150 focus-visible:outline-2 focus-visible:outline-brand-500 focus-visible:outline-offset-2 ${
        selected
          ? "border-brand-500 bg-brand-50 ring-2 ring-brand-500"
          : "border-neutral-200 bg-white hover:border-neutral-300"
      }`}
      data-testid={`site-option-card-${kind}`}
    >
      <div className="flex items-start gap-3">
        {selected ? (
          <CheckCircleIconSolid
            className="h-6 w-6 shrink-0 text-brand-600"
            aria-hidden="true"
          />
        ) : (
          <HollowCircleIcon className="h-6 w-6 shrink-0 text-neutral-400" />
        )}
        <div className="flex-1">
          <div className="flex items-center justify-between">
            <h3 className="text-h3 font-medium text-neutral-900">{title}</h3>
            {statusBadge && (
              <span
                className={`rounded px-2 py-0.5 text-caption font-medium ${statusBadge.className}`}
              >
                {statusBadge.text}
              </span>
            )}
          </div>
          <p className="mt-1 text-body text-neutral-600">{description}</p>
          {children}
        </div>
      </div>
    </div>
  );
}
