"use client";

/**
 * Operator layout shell — wraps all /operator/* routes
 *
 * Location: apps/web/src/app/operator/layout.tsx
 *
 * C-B15 Part B: Client layout with platform-user guard. The existing
 * /operator/cohort page inherits this layout automatically.
 *
 * Structure (spec §2.1):
 *   RequireAuth → platform guard (useAuthMe) →
 *     banner slot → header (logo + Operator badge + TenantSelector + logout) →
 *     sidebar + content area
 *
 * RULE 5: zero hex codes. RULE 15: WCAG 2.2 AA.
 * RULE 35: client component (uses hooks, apiClient, useAuthMe).
 */

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { RequireAuth, useAuth } from "@pilot/ui/auth";
import { LoadingState, ErrorState } from "@pilot/ui/states";
import { useImpersonation } from "@pilot/shared-api";
import { ArrowRightOnRectangleIcon } from "@heroicons/react/24/outline";
import { useSidebarState } from "@/hooks/useSidebarState";
import { useAuthMe, AUTH_ME_QUERY_KEY } from "@/features/auth/hooks/useAuthMe";
import { OperatorSidebar } from "@/components/operator/OperatorSidebar";
import { TenantSelector } from "@/components/operator/TenantSelector";
import { ImpersonationBanner } from "@/components/operator/ImpersonationBanner";

export default function OperatorLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { isSidebarCollapsed } = useSidebarState();
  const { signOut } = useAuth();
  const { data: authMeData, isPending, isError } = useAuthMe();
  const impersonation = useImpersonation();

  // Platform-user guard (spec §2.2)
  if (isPending) {
    return (
      <div className="flex items-center justify-center h-screen bg-neutral-50">
        <LoadingState type="inline" label="Verifying access…" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex items-center justify-center h-screen bg-neutral-50">
        <ErrorState
          type="server"
          title="Could not verify access"
          description="Check your connection and try again."
          onRetry={() =>
            queryClient.invalidateQueries({ queryKey: AUTH_ME_QUERY_KEY })
          }
        />
      </div>
    );
  }

  // Tenant users are redirected to /dashboard
  if (authMeData?.user_type === "tenant") {
    router.replace("/dashboard");
    return null;
  }

  // If user_type is not "platform", redirect as a safety net
  if (authMeData && authMeData.user_type !== "platform") {
    router.replace("/dashboard");
    return null;
  }

  const platformRoleCode = authMeData?.platform_role_code ?? "";

  const handleSignOut = async () => {
    await signOut();
    router.replace("/login");
  };

  return (
    <RequireAuth
      redirectTo="/login"
      onRedirect={(path) => router.replace(path)}
    >
      <div className="flex flex-col h-full min-h-screen">
        {/* Impersonation banner (first child — normal flow, shrink-0) */}
        {impersonation && <ImpersonationBanner />}

        {/* Header */}
        <header
          className="h-12 bg-white border-b border-neutral-200 flex items-center justify-between px-4 shrink-0 z-30"
          data-testid="operator-header"
        >
          {/* Left — logo + Operator badge */}
          <div className="flex items-center gap-3">
            <Link
              href="/operator/cohort"
              className="flex-shrink-0 hover:opacity-80 transition-opacity duration-150"
              aria-label="Pilot operator home"
            >
              <div
                className="overflow-hidden transition-[width] duration-200 ease-in-out"
                style={{ width: isSidebarCollapsed ? "2rem" : "7.5rem" }}
              >
                {isSidebarCollapsed ? (
                  <Image
                    src="/brand/logo-icon.jpg"
                    alt="Pilot for Trades"
                    width={32}
                    height={32}
                    priority
                    className="block"
                  />
                ) : (
                  <Image
                    src="/brand/logo-primary.jpg"
                    alt="Pilot for Trades"
                    width={120}
                    height={32}
                    priority
                    className="block"
                  />
                )}
              </div>
            </Link>
            <span className="inline-flex items-center bg-neutral-100 text-neutral-600 rounded px-1.5 py-0.5 text-caption font-medium">
              Operator
            </span>
          </div>

          {/* Right — tenant selector + logout */}
          <div className="flex items-center gap-3">
            <TenantSelector platformRoleCode={platformRoleCode} />
            <button
              type="button"
              onClick={handleSignOut}
              aria-label="Sign out"
              title="Sign out"
              className="p-2.5 rounded-md text-neutral-500 hover:bg-neutral-100 hover:text-neutral-700 focus-visible:ring-2 focus-visible:ring-brand-500"
              data-testid="operator-logout-button"
            >
              <ArrowRightOnRectangleIcon
                className="w-5 h-5"
                aria-hidden="true"
              />
            </button>
          </div>
        </header>

        {/* Sidebar + content */}
        <div className="flex flex-1 min-h-0">
          <OperatorSidebar />
          <div className="flex-1 min-w-0 overflow-auto bg-neutral-50">
            {children}
          </div>
        </div>
      </div>
    </RequireAuth>
  );
}
