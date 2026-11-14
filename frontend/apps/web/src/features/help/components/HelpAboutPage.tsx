/**
 * HelpAboutPage — FE-B16
 *
 * Location: apps/web/src/features/help/components/HelpAboutPage.tsx
 *
 * /settings/help-and-about combined page.
 * - Top section: Help CTAs (open chat, history, send feedback)
 * - Bottom section: About (version, legal links, support email)
 *
 * RULE: Version from env var (NEXT_PUBLIC_APP_VERSION), not hardcoded.
 */

"use client";

import React, { useState } from "react";
import { useHelpPanel } from "../store/helpPanelStore";

interface LegalDocModalProps {
  title: string;
  content: string;
  onClose: () => void;
}

function LegalDocModal({ title, content, onClose }: LegalDocModalProps) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40 p-4"
      data-testid="legal-doc-modal"
    >
      <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between px-5 py-4 border-b border-neutral-200">
          <h2 className="text-sm font-semibold text-neutral-800">{title}</h2>
          <button
            type="button"
            aria-label="Close"
            onClick={onClose}
            className="p-1.5 text-neutral-400 hover:text-neutral-600 rounded-md transition-colors"
          >
            ✕
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-5 py-4">
          <pre className="whitespace-pre-wrap font-sans text-sm text-neutral-700 leading-relaxed">
            {content}
          </pre>
        </div>
      </div>
    </div>
  );
}

const APP_VERSION = process.env.NEXT_PUBLIC_APP_VERSION ?? "dev";
const SUPPORT_EMAIL =
  process.env.NEXT_PUBLIC_SUPPORT_EMAIL ?? "support@pilotfortrades.com";
const MARKETING_SITE =
  process.env.NEXT_PUBLIC_MARKETING_URL ?? "https://pilotfortrades.com";

const LEGAL_DOCS = [
  { id: "terms", label: "Terms of Service", path: "/legal/terms-of-service" },
  { id: "privacy", label: "Privacy Policy", path: "/legal/privacy-policy" },
  {
    id: "eula",
    label: "End-User License Agreement (EULA)",
    path: "/legal/eula",
  },
] as const;

export function HelpAboutPage() {
  const { setView, open } = useHelpPanel();
  const [legalModal, setLegalModal] = useState<{
    title: string;
    content: string;
  } | null>(null);

  const handleOpenLegal = async (label: string, path: string) => {
    // For MVP: render local legal markdown. In Phase 2, fetch from S3.
    try {
      const res = await fetch(path);
      if (res.ok) {
        const text = await res.text();
        setLegalModal({ title: label, content: text });
      }
    } catch {
      setLegalModal({
        title: label,
        content: "Document temporarily unavailable.",
      });
    }
  };

  return (
    <div className="max-w-xl space-y-8" data-testid="help-about-page">
      {/* ── Help section ─────────────────────────────────────────────── */}
      <section>
        <h2 className="text-sm font-semibold text-neutral-800 mb-4">
          Help & support
        </h2>
        <div className="space-y-3">
          <button
            type="button"
            onClick={() => open()}
            className="flex items-center gap-3 w-full p-3 rounded-lg border border-neutral-200 hover:bg-neutral-50 transition-colors text-left"
            data-testid="help-about-open-chat"
          >
            <span className="text-2xl">💬</span>
            <div>
              <p className="text-sm font-medium text-neutral-800">
                Chat with our AI assistant
              </p>
              <p className="text-xs text-neutral-500 mt-0.5">
                Get answers to your questions instantly
              </p>
            </div>
          </button>

          <button
            type="button"
            onClick={() => {
              open();
              setView("history");
            }}
            className="flex items-center gap-3 w-full p-3 rounded-lg border border-neutral-200 hover:bg-neutral-50 transition-colors text-left"
            data-testid="help-about-open-history"
          >
            <span className="text-2xl">🕐</span>
            <div>
              <p className="text-sm font-medium text-neutral-800">
                Browse past conversations
              </p>
              <p className="text-xs text-neutral-500 mt-0.5">
                Review your previous help sessions
              </p>
            </div>
          </button>

          <a
            href="/settings/help-and-about/feedback"
            className="flex items-center gap-3 w-full p-3 rounded-lg border border-neutral-200 hover:bg-neutral-50 transition-colors"
            data-testid="help-about-feedback-link"
          >
            <span className="text-2xl">📝</span>
            <div>
              <p className="text-sm font-medium text-neutral-800">
                Send feedback
              </p>
              <p className="text-xs text-neutral-500 mt-0.5">
                Report a bug, request a feature, or share a thought
              </p>
            </div>
          </a>
        </div>
      </section>

      {/* ── About section ────────────────────────────────────────────── */}
      <section>
        <h2 className="text-sm font-semibold text-neutral-800 mb-4">
          About Pilot
        </h2>

        {/* Version info */}
        <div
          className="bg-neutral-50 rounded-lg p-4 mb-4 space-y-1"
          data-testid="about-version-block"
        >
          <p className="text-xs text-neutral-500">
            App version:{" "}
            <span
              className="text-neutral-500 text-sm font-mono"
              data-testid="about-app-version"
            >
              {APP_VERSION}
            </span>
          </p>
          <p className="text-xs text-neutral-400">
            Pilot for Trades © {new Date().getFullYear()}
          </p>
        </div>

        {/* Legal links */}
        <div className="space-y-1 mb-4">
          {LEGAL_DOCS.map((doc) => (
            <button
              key={doc.id}
              type="button"
              onClick={() => handleOpenLegal(doc.label, doc.path)}
              className="block w-full text-left text-sm text-brand-600 hover:text-brand-700 underline py-1"
              data-testid={`legal-link-${doc.id}`}
            >
              {doc.label}
            </button>
          ))}
        </div>

        {/* Support email */}
        <div className="space-y-2">
          <a
            href={`mailto:${SUPPORT_EMAIL}`}
            className="block text-sm text-brand-600 hover:text-brand-700 underline"
            data-testid="about-support-email"
          >
            {SUPPORT_EMAIL}
          </a>
          <a
            href={MARKETING_SITE}
            target="_blank"
            rel="noopener noreferrer"
            className="block text-sm text-brand-600 hover:text-brand-700 underline"
            data-testid="about-marketing-link"
          >
            pilotfortrades.com
          </a>
        </div>

        {/* Anonymization transparency */}
        <p
          className="text-xs text-neutral-400 mt-6 leading-relaxed"
          data-testid="about-anon-statement"
        >
          Pilot uses help conversations to improve our help content. Personal
          information is removed from conversations before they are used for any
          analysis or improvement purposes.
        </p>
      </section>

      {/* Legal modal */}
      {legalModal && (
        <LegalDocModal
          title={legalModal.title}
          content={legalModal.content}
          onClose={() => setLegalModal(null)}
        />
      )}
    </div>
  );
}
