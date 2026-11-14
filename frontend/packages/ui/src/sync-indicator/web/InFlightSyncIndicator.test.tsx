/**
 * InFlightSyncIndicator (web) — unit tests
 * Location: packages/ui/src/sync-indicator/web/InFlightSyncIndicator.test.tsx
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { InFlightSyncIndicator } from "./InFlightSyncIndicator";

describe("InFlightSyncIndicator (web)", () => {
  it("renders surface name in aria-label", () => {
    render(<InFlightSyncIndicator surface="dispatch" />);
    const el = screen.getByLabelText(/dispatch sync/i);
    expect(el).toBeTruthy();
  });

  it("state='idle' shows 'In sync' label (no lastSyncedAt — backward-compat)", () => {
    render(<InFlightSyncIndicator surface="quickbooks" state="idle" />);
    expect(screen.getByText("In sync")).toBeTruthy();
  });

  it("state='syncing' shows 'Syncing…' label", () => {
    render(<InFlightSyncIndicator surface="dispatch" state="syncing" />);
    expect(screen.getByText(/Syncing/)).toBeTruthy();
  });

  it("state='error' shows 'Sync error' label", () => {
    render(<InFlightSyncIndicator surface="calendar" state="error" />);
    expect(screen.getByText("Sync error")).toBeTruthy();
  });

  it("state='paused' shows 'Sync paused' label", () => {
    render(<InFlightSyncIndicator surface="quickbooks" state="paused" />);
    expect(screen.getByText("Sync paused")).toBeTruthy();
  });

  it("state='synced-pending' shows 'Synced · N pending' label (FE-B15 updated copy)", () => {
    render(
      <InFlightSyncIndicator
        surface="dispatch"
        state="synced-pending"
        pendingCount={3}
      />,
    );
    expect(screen.getByText("Synced · 3 pending")).toBeTruthy();
  });

  it("pendingCount=0 does not show badge", () => {
    render(<InFlightSyncIndicator surface="dispatch" pendingCount={0} />);
    expect(screen.queryByText("0")).toBeNull();
  });

  it("pendingCount=3 shows badge with '3'", () => {
    render(<InFlightSyncIndicator surface="dispatch" pendingCount={3} />);
    expect(screen.getByLabelText("3 pending")).toBeTruthy();
  });

  it("pendingCount=6 with default amberThreshold=5 shows badge", () => {
    render(
      <InFlightSyncIndicator
        surface="dispatch"
        pendingCount={6}
        state="synced-pending"
      />,
    );
    expect(screen.getByLabelText("6 pending")).toBeTruthy();
  });

  it("amberThreshold=10 with pendingCount=6: badge shows but dot class remains green", () => {
    const { container } = render(
      <InFlightSyncIndicator
        surface="dispatch"
        pendingCount={6}
        state="synced-pending"
        amberThreshold={10}
      />,
    );
    // Dot should have bg-margin-400 (green), not bg-alert-400 (amber)
    const dot = container.querySelector(".bg-margin-400");
    expect(dot).toBeTruthy();
  });

  it("renders 'Sync now' link when onManualSync provided and state=synced-pending", () => {
    const onManualSync = vi.fn();
    render(
      <InFlightSyncIndicator
        surface="quickbooks"
        state="synced-pending"
        onManualSync={onManualSync}
      />,
    );
    fireEvent.click(screen.getByText("Sync now"));
    expect(onManualSync).toHaveBeenCalledTimes(1);
  });

  it("does NOT render 'Sync now' for mobile-sync surface", () => {
    render(
      <InFlightSyncIndicator
        surface="mobile-sync"
        state="synced-pending"
        onManualSync={vi.fn()}
      />,
    );
    expect(screen.queryByText("Sync now")).toBeNull();
  });

  it("compact mode renders only dot and count, no state text", () => {
    render(
      <InFlightSyncIndicator surface="dispatch" pendingCount={3} compact />,
    );
    expect(screen.queryByText("In sync")).toBeNull();
    expect(screen.getByText("3")).toBeTruthy();
  });

  it("applies testID when provided", () => {
    const { container } = render(
      <InFlightSyncIndicator surface="dispatch" testID="sync-test" />,
    );
    expect(container.querySelector('[data-testid="sync-test"]')).toBeTruthy();
  });
});
