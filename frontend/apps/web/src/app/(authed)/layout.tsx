"use client";

/**
 * Authenticated route group layout
 *
 * Location: apps/web/src/app/(authed)/layout.tsx
 *
 * Route segment config: force-dynamic prevents Next.js from attempting to
 * statically pre-render any authenticated page during `next build`. This is
 * correct — authed pages require a live auth session and cannot be generated
 * at build time. Without this, the SSR static generation worker throws:
 *   TypeError: (0 , c.useContext) is not a function
 * because the worker's isolated module context conflicts with the client-side
 * React context established by NotificationQueueProvider.
 *
 * All routes under (authed)/ require authentication.
 * Unauthenticated users are redirected to /login.
 *
 * FE-B2:
 *   - useSessionExpiry() hook wired here (subscribes to auth:session-expired events)
 *   - RequireAuth upgraded with onRedirect prop (uses router.replace from next/navigation)
 *
 * FE-B23:
 *   - Top header bar added with NotificationBell
 *   - NotificationDrawer rendered at layout level (global)
 *
 * UI-FIX-2E:
 *   - Header redesigned: logo left (links to /dashboard, switches on sidebar collapse)
 *     + Bell + Settings gear + Profile avatar right
 *   - AppSidebar now collapsible via useSidebarState (localStorage persistence)
 *
 * Note: NotificationQueueProvider + NotificationPortal are now in providers.tsx (root level)
 * so ALL routes (including public /login) can use useNotificationQueue(). No duplicate here.
 */

import Image from "next/image";
import Link from "next/link";
import { RequireAuth } from "@pilot/ui/auth";
import { useImpersonation } from "@pilot/shared-api";
import { useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { useSessionExpiry } from "@/hooks/useSessionExpiry";
import { useSidebarState } from "@/hooks/useSidebarState";
import { AppSidebar } from "@/components/AppSidebar";
import { ProfileDropdown } from "@/components/ProfileDropdown";
import { SettingsGearIcon } from "@/components/SettingsGearIcon";
import { SignupCompletionGuard } from "@/components/SignupCompletionGuard";
import { ImpersonationBanner } from "@/components/operator/ImpersonationBanner";
import { NotificationBell } from "@/features/notifications-center/components/NotificationBell";
import { NotificationDrawer } from "@/features/notifications-center/components/NotificationDrawer";

function SessionExpiryWatcher() {
  useSessionExpiry();
  return null;
}

export default function AuthedLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const { isSidebarCollapsed } = useSidebarState();
  const impersonation = useImpersonation();

  return (
    <>
      {/* Session expiry watcher — listens for auth:session-expired events */}
      <SessionExpiryWatcher />
      <RequireAuth
        redirectTo="/login"
        onRedirect={(path) => router.replace(path)}
      >
        <SignupCompletionGuard>
          <div className="flex flex-col h-full min-h-screen">
            {/* C-B15: Impersonation banner — first child, normal flow (shrink-0) */}
            {impersonation && <ImpersonationBanner />}

            {/* Top header bar — UI-FIX-2E redesign */}
            <header
              className="h-12 bg-white border-b border-neutral-200 flex items-center justify-between px-4 shrink-0 z-30"
              data-testid="app-header"
            >
              {/* Left: Logo — switches between full wordmark and icon mark */}
              <Link
                href="/dashboard"
                className="flex-shrink-0 hover:opacity-80 transition-opacity duration-150"
                aria-label="Go to dashboard"
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

              {/* Right: icon group — Bell + Settings gear + Profile avatar */}
              <div className="flex items-center gap-2">
                <NotificationBell />
                <SettingsGearIcon />
                <ProfileDropdown />
              </div>
            </header>

            {/* Sidebar + content */}
            <div className="flex flex-1 min-h-0">
              <AppSidebar />
              <div className="flex-1 min-w-0 overflow-auto">{children}</div>
            </div>
          </div>

          {/* Notification drawer — global, rendered outside content flow */}
          <NotificationDrawer />
        </SignupCompletionGuard>
      </RequireAuth>
    </>
  );
}
