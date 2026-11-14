/**
 * settingsWrapper.tsx — FE-B11 test utilities
 *
 * Shared wrapper factory for settings integration tests.
 * Includes QueryClientProvider + NotificationQueueProvider.
 */

import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NotificationQueueProvider } from "@pilot/ui";

export function createSettingsWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <NotificationQueueProvider>{children}</NotificationQueueProvider>
      </QueryClientProvider>
    );
  }

  return { wrapper: Wrapper, queryClient };
}
