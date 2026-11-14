"use client";

/**
 * RootProviders — web app root provider composition
 *
 * Location: apps/web/src/app/providers.tsx
 *
 * Composes:
 *   - <NotificationQueueProvider> — must be at root so ALL routes (including /login)
 *     can call useNotificationQueue()
 *   - <AuthProvider> — Cognito/mock auth context
 *   - <QueryClientProvider> — TanStack Query client
 *   - <NotificationPortal> — renders notification stack above all content
 *   - MSW worker init (env-gated via NEXT_PUBLIC_USE_MSW_MOCKS)
 *   - ReactQueryDevtools (dev only)
 *
 * Usage: imported by apps/web/src/app/layout.tsx
 *
 * FE-B2: NotificationQueueProvider moved to root (was only in (authed)/layout.tsx)
 * so that public routes like /login can use useNotificationQueue().
 */

// Import amplify-config FIRST — calls Amplify.configure() at module-evaluation
// time, before AuthProvider mounts and calls fetchAuthSession. Must be first.
import "../lib/amplify-config";
import React, { useEffect, useRef, type ReactNode } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { AuthProvider } from "@pilot/ui/auth";
import { createQueryClient } from "@pilot/shared-api";
import type { PilotUser } from "@pilot/ui/auth";
import { NotificationQueueProvider } from "@pilot/ui/notification-banner";
import { NotificationPortal } from "@pilot/ui/notification-banner/web/NotificationPortal";

// Create a stable QueryClient instance (module-level to survive React StrictMode)
const queryClient = createQueryClient();

interface RootProvidersProps {
  children: ReactNode;
}

// Mock user from env — only active when NEXT_PUBLIC_USE_MOCK_AUTH=true
function getMockUser():
  | Pick<PilotUser, "role" | "email" | "displayName">
  | undefined {
  if (process.env.NEXT_PUBLIC_USE_MOCK_AUTH !== "true") return undefined;
  return {
    role:
      (process.env.NEXT_PUBLIC_MOCK_USER_ROLE as PilotUser["role"]) ?? "owner",
    email: "mockuser@pilot-dev.example.com",
    displayName: "Mock User",
  };
}

export function RootProviders({ children }: RootProvidersProps) {
  const mswStarted = useRef(false);

  useEffect(() => {
    // Start MSW browser worker in dev mode when env var is set
    if (
      process.env.NEXT_PUBLIC_USE_MSW_MOCKS === "true" &&
      !mswStarted.current
    ) {
      mswStarted.current = true;
      import("../mocks/browser").then(({ worker }) => {
        worker.start({ onUnhandledRequest: "bypass" }).catch(console.error);
      });
    }
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <NotificationQueueProvider>
        {/* Portal renders notification stack above all content on every route */}
        <NotificationPortal />
        <AuthProvider mockUser={getMockUser()}>{children}</AuthProvider>
      </NotificationQueueProvider>
      {process.env.NODE_ENV === "development" && (
        <ReactQueryDevtools initialIsOpen={false} />
      )}
    </QueryClientProvider>
  );
}
