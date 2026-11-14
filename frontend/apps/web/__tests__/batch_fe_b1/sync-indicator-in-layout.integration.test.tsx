/**
 * InFlightSyncIndicator — integration tests in web layout
 * Location: apps/web/__tests__/batch_fe_b1/sync-indicator-in-layout.integration.test.tsx
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import { InFlightSyncIndicator } from "@pilot/ui/sync-indicator";
import type { SyncSurface } from "@pilot/ui/sync-indicator";

function HeaderSlot({ children }: { children: React.ReactNode }) {
  return (
    <header
      data-testid="header"
      style={{ display: "flex", alignItems: "center", gap: 8 }}
    >
      {children}
    </header>
  );
}

const ALL_SURFACES: SyncSurface[] = [
  "dispatch",
  "mobile-sync",
  "calendar",
  "quickbooks",
];

describe("InFlightSyncIndicator — integration in web layout", () => {
  it("renders in a header nav slot without layout breakage", () => {
    render(
      <HeaderSlot>
        <InFlightSyncIndicator surface="dispatch" compact />
      </HeaderSlot>,
    );
    expect(screen.getByTestId("header")).toBeTruthy();
    expect(screen.getByTestId("sync-indicator-dispatch")).toBeTruthy();
  });

  it.each(ALL_SURFACES)("surface '%s' renders without crashing", (surface) => {
    render(<InFlightSyncIndicator surface={surface} />);
    expect(screen.getByTestId(`sync-indicator-${surface}`)).toBeTruthy();
  });

  it("state='syncing' shows expected label", () => {
    render(<InFlightSyncIndicator surface="dispatch" state="syncing" />);
    expect(screen.getByText(/Syncing/)).toBeTruthy();
  });

  it("compact mode fits in constrained header slot without text overflow", () => {
    const { container } = render(
      <HeaderSlot>
        <InFlightSyncIndicator surface="quickbooks" compact pendingCount={5} />
      </HeaderSlot>,
    );
    const indicator = container.querySelector(
      '[data-testid="sync-indicator-quickbooks"]',
    );
    expect(indicator).toBeTruthy();
    // In compact mode there should be no state label text
    expect(screen.queryByText("In sync")).toBeNull();
  });
});
