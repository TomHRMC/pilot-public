/**
 * Signup wizard layout — pre-auth shell
 *
 * Location: apps/web/src/app/signup/layout.tsx
 *
 * RULE 3: Lives OUTSIDE (authed) route group. No JWT guard here.
 * Renders: Pilot logo, step progress bar, no nav sidebar.
 */

import React from "react";
import Link from "next/link";

export const metadata = {
  title: "Create your Pilot account",
  description: "Get started with Pilot for Trades — free 14-day trial.",
};

export default function SignupLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-neutral-50 flex flex-col">
      {/* Header: logo only */}
      <header className="w-full px-6 py-4 flex items-center justify-center border-b border-neutral-100 bg-white">
        <Link
          href="/"
          aria-label="Pilot for Trades home"
          className="flex items-center gap-2 text-lg font-bold text-brand-600"
        >
          {/* Pilot wordmark / logo placeholder */}
          <svg
            className="w-6 h-6"
            viewBox="0 0 24 24"
            fill="none"
            aria-hidden="true"
          >
            <path
              d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          Pilot
        </Link>
      </header>

      {/* Main content */}
      <main className="flex-1 flex flex-col items-center justify-start px-4 py-8 sm:py-12">
        <div className="w-full max-w-lg">{children}</div>
      </main>

      {/* Footer: minimal legal links */}
      <footer className="w-full px-6 py-4 text-center text-xs text-neutral-400 border-t border-neutral-100">
        <span>© {new Date().getFullYear()} Pilot for Trades</span>
        <span className="mx-2">·</span>
        <a
          href="/privacy"
          className="hover:text-neutral-600 focus:outline-none focus-visible:underline"
        >
          Privacy
        </a>
        <span className="mx-2">·</span>
        <a
          href="/terms"
          className="hover:text-neutral-600 focus:outline-none focus-visible:underline"
        >
          Terms
        </a>
      </footer>
    </div>
  );
}
