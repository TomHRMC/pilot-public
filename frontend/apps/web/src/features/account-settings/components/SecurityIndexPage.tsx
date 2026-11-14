/**
 * SecurityIndexPage — BETA-B4 / STEP 1
 *
 * Location: apps/web/src/features/account-settings/components/SecurityIndexPage.tsx
 *
 * Landing/index page for My Account > Security group.
 * Shows enrolled MFA method count and links to all security sub-pages.
 *
 * Route: /settings/my-account/security
 */

"use client";

import React from "react";
import Link from "next/link";
import { useMfaStatus } from "../hooks/useMfaStatus";

function SecurityNavCard({
  title,
  description,
  href,
}: {
  title: string;
  description: string;
  href: string;
}) {
  return (
    <Link
      href={href}
      className="flex items-center justify-between p-4 rounded-md border border-neutral-200 hover:border-brand-400 hover:bg-brand-50 transition-colors group"
    >
      <div>
        <p className="font-medium text-neutral-900 text-sm">{title}</p>
        <p className="text-xs text-neutral-500 mt-0.5">{description}</p>
      </div>
      <span
        className="text-neutral-400 group-hover:text-brand-600 text-lg"
        aria-hidden="true"
      >
        →
      </span>
    </Link>
  );
}

export function SecurityIndexPage() {
  const { data, isLoading, isError } = useMfaStatus();

  const mfaDescription = isLoading
    ? "Loading MFA status…"
    : isError
      ? "Could not load MFA status — click to manage"
      : `${data?.method_count ?? 0} method${(data?.method_count ?? 0) !== 1 ? "s" : ""} enrolled`;

  return (
    <div className="mx-auto p-6 max-w-2xl">
      <h1 className="text-2xl font-semibold text-neutral-900 mb-6">Security</h1>
      <div className="space-y-4">
        {/* MFA Card */}
        <SecurityNavCard
          title="Multi-Factor Authentication"
          description={mfaDescription}
          href="/settings/my-account/security/mfa"
        />

        {/* Active Sessions Card */}
        <SecurityNavCard
          title="Active Sessions"
          description="View and revoke active login sessions"
          href="/settings/my-account/sessions"
        />

        {/* Password Card */}
        <SecurityNavCard
          title="Password"
          description="Change your account password"
          href="/settings/my-account/password"
        />

        {/* Data Export Card */}
        <SecurityNavCard
          title="Data Export"
          description="Export a copy of your data"
          href="/settings/my-account/data-export"
        />
      </div>
    </div>
  );
}
