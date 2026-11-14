/**
 * Login page
 *
 * Location: apps/web/src/app/login/page.tsx
 *
 * FE-B2: Full login form implementation replacing FE-B0 placeholder.
 * Reads ?signedOut=true query param to show "You've been signed out" banner.
 * Reads ?passwordReset=true query param to show "Password updated" banner.
 */

"use client";

import React, { useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { LoginForm } from "@/features/login/components/LoginForm";
import { usePostLoginRedirect } from "@/hooks/usePostLoginRedirect";
import { useNotificationQueue } from "@pilot/ui/notification-banner";
import { useAuth } from "@pilot/ui/auth";
import type { PilotRole } from "@pilot/ui/auth";

const isMockMode = process.env.NEXT_PUBLIC_USE_MOCK_AUTH === "true";

export default function LoginPage() {
  const searchParams = useSearchParams();
  const { redirectForRole } = usePostLoginRedirect();
  const { addNotification } = useNotificationQueue();
  const { isAuthenticated, role } = useAuth();
  const router = useRouter();

  // Already logged in — send straight to dashboard instead of showing the form
  useEffect(() => {
    if (isAuthenticated) {
      router.replace("/dashboard");
      return;
    }
  }, [isAuthenticated, role, router]);

  useEffect(() => {
    if (searchParams.get("signedOut") === "true") {
      addNotification({
        id: "signed-out-banner",
        severity: "info",
        title: "You've been signed out.",
        dismissAfterMs: 6000,
      });
    }
    if (searchParams.get("passwordReset") === "true") {
      addNotification({
        id: "password-reset-success",
        severity: "success",
        title: "Password updated. Sign in with your new password.",
        dismissAfterMs: 6000,
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleSuccess(role: PilotRole) {
    redirectForRole(role);
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-6 bg-neutral-50">
      <div className="w-full max-w-md rounded-lg bg-white p-8 shadow-sm border border-neutral-200 flex flex-col gap-6">
        {/* Logo / wordmark area */}
        <div className="flex flex-col gap-1 text-center">
          <h1 className="text-h1 text-neutral-900">Pilot for Trades</h1>
          <p className="text-body text-neutral-600">Sign in to your account</p>
        </div>

        <LoginForm onSuccess={handleSuccess} mockMode={isMockMode} />
      </div>
    </main>
  );
}
