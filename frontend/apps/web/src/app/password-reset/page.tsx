/**
 * Password Reset page
 *
 * Location: apps/web/src/app/password-reset/page.tsx
 *
 * FE-B2: Single-page multi-step password reset flow.
 * Uses PasswordResetFlow component which manages step state internally.
 */

"use client";

import React from "react";
import Link from "next/link";
import { PasswordResetFlow } from "@/features/login/components/PasswordResetFlow";
import { NotificationQueueProvider } from "@pilot/ui/notification-banner";
import { NotificationPortal } from "@pilot/ui/notification-banner/web/NotificationPortal";

export default function PasswordResetPage() {
  return (
    <NotificationQueueProvider>
      <NotificationPortal />
      <main className="flex min-h-screen flex-col items-center justify-center p-6 bg-neutral-50">
        <div className="w-full max-w-md rounded-lg bg-white p-8 shadow-sm border border-neutral-200 flex flex-col gap-6">
          {/* Logo / wordmark area */}
          <div className="flex flex-col gap-1 text-center">
            <h1 className="text-h1 text-neutral-900">Reset password</h1>
          </div>

          <PasswordResetFlow onSuccess={() => undefined} />

          <div className="text-center">
            <Link
              href="/login"
              className="text-caption text-brand-600 hover:underline focus:outline-none"
            >
              ← Back to sign in
            </Link>
          </div>
        </div>
      </main>
    </NotificationQueueProvider>
  );
}
