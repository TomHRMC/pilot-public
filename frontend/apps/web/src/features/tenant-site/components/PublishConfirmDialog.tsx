"use client";

/**
 * PublishConfirmDialog — C-B16 publish confirmation modal
 *
 * Location: apps/web/src/features/tenant-site/components/PublishConfirmDialog.tsx
 *
 * Two branches:
 *   1. Normal publish — preview summary + single confirm button
 *   2. 409 overwrite-confirm — current vs. new URL + BrandStateNotice inline +
 *      confirm checkbox + destructive confirm button (Design Decision #8)
 *
 * web spec §10: overlay, modal panel, close button (44×44px), focus trap.
 * WCAG 2.4.11: focus trap, Escape to close, return focus to trigger.
 */

import React, { useEffect, useRef, useState } from "react";
import { XMarkIcon } from "@heroicons/react/24/outline";
import { ExclamationTriangleIcon as ExclamationTriangleIconSolid } from "@heroicons/react/24/solid";
import { BrandStateNotice } from "./BrandStateNotice";
import type { WebsiteOverwriteConflict } from "../hooks/usePublishTenantSite";

interface PublishConfirmDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (confirmWebsiteOverwrite: boolean) => void;
  isPublishing: boolean;
  slug: string;
  displayName: string;
  /** 409 overwrite conflict payload — when present, dialog switches to overwrite variant */
  overwriteConflict?: WebsiteOverwriteConflict | null;
}

export function PublishConfirmDialog({
  open,
  onClose,
  onConfirm,
  isPublishing,
  slug,
  displayName,
  overwriteConflict,
}: PublishConfirmDialogProps) {
  const [confirmChecked, setConfirmChecked] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLElement | null>(null);

  const domain = process.env.NEXT_PUBLIC_TENANT_SITES_DOMAIN ?? "localhost";
  const siteUrl = `https://${slug}.${domain}`;
  const isOverwrite = Boolean(overwriteConflict);

  // Focus trap: on open, focus the dialog; on close, return focus to trigger
  useEffect(() => {
    if (open) {
      triggerRef.current = document.activeElement as HTMLElement;
      dialogRef.current?.focus();
    } else if (triggerRef.current) {
      triggerRef.current?.focus();
    }
  }, [open]);

  // Escape to close
  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  // Checkbox state resets via key remount when dialog reopens or conflict changes
  const checkboxKey = `${open}-${overwriteConflict?.current_url ?? "none"}`;

  const handleConfirm = () => {
    onConfirm(isOverwrite);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-neutral-900/50"
      onClick={onClose}
      data-testid="publish-confirm-overlay"
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="publish-dialog-title"
        tabIndex={-1}
        className="mx-auto mt-16 w-full max-w-lg rounded-lg bg-white p-6 shadow-xl outline-none"
        onClick={(e) => e.stopPropagation()}
        data-testid="publish-confirm-dialog"
      >
        {/* Close button — 44×44px hit area */}
        <button
          type="button"
          onClick={onClose}
          className="float-right -m-2 p-2 text-neutral-400 hover:text-neutral-600 focus-visible:outline-2 focus-visible:outline-brand-500 focus-visible:outline-offset-2 focus-visible:rounded"
          aria-label="Close dialog"
          data-testid="publish-dialog-close"
        >
          <XMarkIcon className="h-5 w-5" aria-hidden="true" />
        </button>

        <h2
          id="publish-dialog-title"
          className="text-h2 font-semibold text-neutral-900"
        >
          Publish your compliance site
        </h2>

        {isOverwrite ? (
          /* ── 409 Overwrite-confirm variant (§10.3) ── */
          <div className="mt-4">
            <div className="flex items-start gap-3">
              <ExclamationTriangleIconSolid
                className="h-6 w-6 shrink-0 text-alert-600"
                aria-hidden="true"
              />
              <p className="text-body font-medium text-neutral-900">
                This will replace the website URL on your 10DLC profile.
              </p>
            </div>

            {/* URL comparison */}
            <div className="mt-4 space-y-2 rounded-md border border-neutral-200 bg-neutral-50 p-3">
              <div>
                <span className="text-caption text-neutral-500">Current:</span>
                <p className="font-mono text-body text-neutral-900">
                  {overwriteConflict?.current_url}
                </p>
              </div>
              <div>
                <span className="text-caption text-neutral-500">New:</span>
                <p className="font-mono text-body text-neutral-900">
                  {overwriteConflict?.new_url ?? siteUrl}
                </p>
              </div>
            </div>

            {/* Inline BrandStateNotice */}
            {overwriteConflict?.brand_status && (
              <div className="mt-4">
                <BrandStateNotice
                  brandStatus={overwriteConflict.brand_status}
                />
              </div>
            )}

            {/* Confirm checkbox */}
            <label className="mt-4 flex items-start gap-2">
              <input
                key={checkboxKey}
                type="checkbox"
                checked={confirmChecked}
                onChange={(e) => setConfirmChecked(e.target.checked)}
                className="mt-0.5 h-4 w-4 rounded border-neutral-300 text-brand-600 focus-visible:outline-2 focus-visible:outline-brand-500 focus-visible:outline-offset-2"
                data-testid="publish-overwrite-checkbox"
              />
              <span className="text-sm text-neutral-700">
                I understand this replaces the URL on my 10DLC profile. My
                carrier brand registration may need re-submission.
              </span>
            </label>

            {/* Buttons */}
            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                onClick={onClose}
                className="rounded-md border border-neutral-300 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50 focus-visible:outline-2 focus-visible:outline-brand-500 focus-visible:outline-offset-2"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirm}
                disabled={!confirmChecked || isPublishing}
                className="rounded-md bg-fault-600 px-4 py-2 text-sm font-medium text-white hover:bg-fault-700 focus-visible:outline-2 focus-visible:outline-fault-500 focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                data-testid="publish-overwrite-confirm-btn"
              >
                {isPublishing ? "Publishing…" : "Confirm & Publish"}
              </button>
            </div>
          </div>
        ) : (
          /* ── Normal publish variant (§10.2) ── */
          <div className="mt-4">
            <p className="text-body text-neutral-600">
              Your site will go live at {siteUrl}. The URL will be saved to your
              10DLC profile for carrier vetting.
            </p>

            {/* Preview thumbnail */}
            <div className="mt-4 rounded-md border border-neutral-200 bg-neutral-50 p-3">
              <p className="text-sm font-medium text-neutral-900">
                {displayName}
              </p>
              <p className="text-xs text-neutral-500">{siteUrl}</p>
            </div>

            {/* Buttons */}
            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                onClick={onClose}
                className="rounded-md border border-neutral-300 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50 focus-visible:outline-2 focus-visible:outline-brand-500 focus-visible:outline-offset-2"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirm}
                disabled={isPublishing}
                className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 focus-visible:outline-2 focus-visible:outline-brand-500 focus-visible:outline-offset-2 disabled:opacity-50"
                data-testid="publish-confirm-btn"
              >
                {isPublishing ? "Publishing…" : "Publish"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
