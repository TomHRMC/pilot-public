/**
 * InFlightSyncIndicator — Dispatch Integration Tests
 *
 * Location: apps/web/__tests__/batch_fe_b4/in-flight-indicator-dispatch.integration.test.tsx
 * Per batch-fe-b4-design.md §I.2
 * Target: 2 tests
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { InFlightSyncIndicator } from "@pilot/ui/sync-indicator";

function makeWrapper() {
  const queryClient = new QueryClient();
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

describe("InFlightSyncIndicator — Dispatch Integration", () => {
  it("shows 'In sync' when no pending mutations and SSE connected", () => {
    render(
      <InFlightSyncIndicator
        surface="dispatch"
        state="idle"
        pendingCount={0}
      />,
      { wrapper: makeWrapper() },
    );
    expect(screen.getByText("In sync")).toBeInTheDocument();
  });

  it("shows 'Sync error' when SSE disconnected", () => {
    render(
      <InFlightSyncIndicator
        surface="dispatch"
        state="error"
        pendingCount={0}
      />,
      { wrapper: makeWrapper() },
    );
    expect(screen.getByText("Sync error")).toBeInTheDocument();
  });
});
