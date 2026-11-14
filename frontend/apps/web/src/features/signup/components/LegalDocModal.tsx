/**
 * LegalDocModal — Inline modal for "Read full →" legal document links
 *
 * Location: apps/web/src/features/signup/components/LegalDocModal.tsx
 *
 * Dev: renders "Legal copy pending" placeholder.
 * Wizard does NOT navigate away when this modal opens.
 */

"use client";

import React, { useEffect, useRef } from "react";

type DocType = "tos" | "privacy" | "eula";

const DOC_TITLES: Record<DocType, string> = {
  tos: "Terms of Service",
  privacy: "Privacy Policy",
  eula: "End User License Agreement",
};

interface LegalDocModalProps {
  docType: DocType | null;
  onClose: () => void;
}

export function LegalDocModal({ docType, onClose }: LegalDocModalProps) {
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (docType) {
      closeButtonRef.current?.focus();
    }
  }, [docType]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  if (!docType) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={DOC_TITLES[docType]}
      data-testid="legal-doc-modal"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="bg-white rounded-2xl shadow-xl max-w-lg w-full max-h-[80vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-100">
          <h2 className="text-base font-semibold text-neutral-900">
            {DOC_TITLES[docType]}
          </h2>
          <button
            ref={closeButtonRef}
            type="button"
            onClick={onClose}
            aria-label="Close document"
            data-testid="legal-doc-modal-close"
            className="text-neutral-400 hover:text-neutral-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 rounded"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              viewBox="0 0 20 20"
              aria-hidden="true"
            >
              <path
                d="M4 4l12 12M16 4L4 16"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
              />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          <p
            className="text-sm text-neutral-500 italic"
            data-testid="legal-doc-placeholder"
          >
            Legal copy pending — content will be provided before production
            launch.
          </p>
          <p className="text-sm text-neutral-500 mt-2">
            Document type:{" "}
            <code className="text-xs bg-neutral-100 px-1 rounded">
              {docType}
            </code>
          </p>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-neutral-100">
          <button
            type="button"
            onClick={onClose}
            className="w-full py-2 px-4 rounded-lg text-sm font-semibold bg-brand-600 text-white hover:bg-brand-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
