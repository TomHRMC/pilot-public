/**
 * InFlightSyncIndicator — Unit tests (FE-B15)
 *
 * Location: packages/ui/src/sync-indicator/InFlightSyncIndicator.test.tsx
 * Runner: Vitest + @testing-library/react
 *
 * Covers 24 critical tests from batch-fe-b15-design.md §G.1
 * Tests 12–16 (mobile dot/onResolve) are covered in InFlightSyncIndicator.mobile.test.tsx
 * Web-specific tests: 1–11, 17–20
 * Hook tests: 21–24 (in useInFlightSyncStatus.test.ts)
 */

import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { InFlightSyncIndicator } from "./web/InFlightSyncIndicator";

// ─── Tests 1–5: Dot class per state × pendingCount × amberThreshold ────────────

describe("InFlightSyncIndicator — web dot colors", () => {
  it("1. renders bg-margin-400 dot in idle state", () => {
    render(
      <InFlightSyncIndicator
        surface="dispatch"
        state="idle"
        pendingCount={0}
      />,
    );
    const dot = document.querySelector(".bg-margin-400");
    expect(dot).not.toBeNull();
  });

  it("2. renders bg-alert-400 animate-pulse dot in syncing state", () => {
    render(
      <InFlightSyncIndicator
        surface="quickbooks"
        state="syncing"
        pendingCount={3}
      />,
    );
    const dot = document.querySelector(".bg-alert-400.animate-pulse");
    expect(dot).not.toBeNull();
  });

  it("3. renders bg-fault-600 dot in error state", () => {
    render(
      <InFlightSyncIndicator
        surface="calendar"
        state="error"
        pendingCount={2}
      />,
    );
    const dot = document.querySelector(".bg-fault-600");
    expect(dot).not.toBeNull();
  });

  it("4. renders bg-neutral-400 dot in paused state", () => {
    render(
      <InFlightSyncIndicator
        surface="quickbooks"
        state="paused"
        pendingCount={1}
      />,
    );
    const dot = document.querySelector(".bg-neutral-400");
    expect(dot).not.toBeNull();
  });

  it("5. renders bg-alert-400 dot in synced-pending when count ≥ amberThreshold", () => {
    render(
      <InFlightSyncIndicator
        surface="quickbooks"
        state="synced-pending"
        pendingCount={5}
        amberThreshold={5}
      />,
    );
    const dot = document.querySelector(".bg-alert-400");
    expect(dot).not.toBeNull();
    // Should NOT have animate-pulse (not syncing)
    expect(dot?.classList.contains("animate-pulse")).toBe(false);
  });

  it("5b. renders bg-margin-400 dot in synced-pending when count < amberThreshold", () => {
    render(
      <InFlightSyncIndicator
        surface="quickbooks"
        state="synced-pending"
        pendingCount={2}
        amberThreshold={5}
      />,
    );
    const dot = document.querySelector(".bg-margin-400");
    expect(dot).not.toBeNull();
  });
});

// ─── Tests 6–7: onResolve wiring ──────────────────────────────────────────────

describe("InFlightSyncIndicator — onResolve", () => {
  it("6. calls onResolve when indicator is clicked in error state", () => {
    const handleResolve = vi.fn();
    render(
      <InFlightSyncIndicator
        surface="calendar"
        state="error"
        pendingCount={3}
        onResolve={handleResolve}
      />,
    );
    const clickable = document.querySelector('[role="button"]');
    expect(clickable).not.toBeNull();
    fireEvent.click(clickable!);
    expect(handleResolve).toHaveBeenCalledOnce();
  });

  it("7. calls onResolve when indicator is clicked in synced-pending state", () => {
    const handleResolve = vi.fn();
    render(
      <InFlightSyncIndicator
        surface="quickbooks"
        state="synced-pending"
        pendingCount={4}
        onResolve={handleResolve}
      />,
    );
    const clickable = document.querySelector('[role="button"]');
    expect(clickable).not.toBeNull();
    fireEvent.click(clickable!);
    expect(handleResolve).toHaveBeenCalledOnce();
  });

  it("6b. does NOT render clickable wrapper in idle state", () => {
    const handleResolve = vi.fn();
    render(
      <InFlightSyncIndicator
        surface="calendar"
        state="idle"
        pendingCount={0}
        onResolve={handleResolve}
      />,
    );
    const clickable = document.querySelector('[role="button"]');
    expect(clickable).toBeNull();
  });
});

// ─── Test 8: onManualSync renders "Sync now" only in synced-pending ────────────

describe("InFlightSyncIndicator — onManualSync", () => {
  it("8. Sync now button rendered in synced-pending state when onManualSync provided", () => {
    const handleManualSync = vi.fn();
    render(
      <InFlightSyncIndicator
        surface="quickbooks"
        state="synced-pending"
        pendingCount={3}
        onManualSync={handleManualSync}
      />,
    );
    const btn = screen.getByRole("button", { name: "Sync now" });
    expect(btn).toBeTruthy();
    fireEvent.click(btn);
    expect(handleManualSync).toHaveBeenCalledOnce();
  });

  it("8b. Sync now NOT rendered in idle state", () => {
    render(
      <InFlightSyncIndicator
        surface="quickbooks"
        state="idle"
        pendingCount={0}
        onManualSync={vi.fn()}
      />,
    );
    expect(screen.queryByRole("button", { name: "Sync now" })).toBeNull();
  });
});

// ─── Test 9: manualTriggerSupported=false hides Sync now ──────────────────────

describe("InFlightSyncIndicator — manualTriggerSupported", () => {
  it("9. Sync now not rendered when manualTriggerSupported=false", () => {
    render(
      <InFlightSyncIndicator
        surface="quickbooks"
        state="synced-pending"
        pendingCount={3}
        onManualSync={vi.fn()}
        manualTriggerSupported={false}
      />,
    );
    expect(screen.queryByRole("button", { name: "Sync now" })).toBeNull();
  });
});

// ─── Test 10: pendingCount badge ──────────────────────────────────────────────

describe("InFlightSyncIndicator — pending count badge", () => {
  it("10. badge shows pendingCount when > 0", () => {
    render(
      <InFlightSyncIndicator
        surface="quickbooks"
        state="synced-pending"
        pendingCount={7}
      />,
    );
    expect(screen.getByLabelText("7 pending")).toBeTruthy();
    expect(screen.getByText("7")).toBeTruthy();
  });

  it("10b. badge hidden when pendingCount=0", () => {
    render(
      <InFlightSyncIndicator
        surface="quickbooks"
        state="idle"
        pendingCount={0}
      />,
    );
    expect(screen.queryByLabelText(/pending/)).toBeNull();
  });
});

// ─── Test 11: compact mode ────────────────────────────────────────────────────

describe("InFlightSyncIndicator — compact mode", () => {
  it("11. compact mode renders dot + count only, no label text", () => {
    render(
      <InFlightSyncIndicator
        surface="dispatch"
        state="syncing"
        pendingCount={3}
        compact
      />,
    );
    // dot is present
    const dot = document.querySelector("span[aria-hidden]");
    expect(dot).not.toBeNull();
    // count is present
    expect(screen.getByText("3")).toBeTruthy();
    // No label text (stateLabel)
    expect(screen.queryByText(/Syncing/)).toBeNull();
  });
});

// ─── Test 17: hover detail tooltip ────────────────────────────────────────────

describe("InFlightSyncIndicator — hover detail tooltip", () => {
  it("17. tooltip shows pendingItems on hover", async () => {
    const items = [
      { type: "conflict", label: "Conflict #abc123 — calendar conflict" },
      { type: "conflict", label: "Conflict #def456 — calendar conflict" },
    ];
    render(
      <InFlightSyncIndicator
        surface="calendar"
        state="synced-pending"
        pendingCount={2}
        pendingItems={items}
      />,
    );
    const container = screen.getByTestId("sync-indicator-calendar");
    fireEvent.mouseEnter(container);
    expect(
      screen.getByText("Conflict #abc123 — calendar conflict"),
    ).toBeTruthy();
    expect(
      screen.getByText("Conflict #def456 — calendar conflict"),
    ).toBeTruthy();
  });

  it("18. tooltip shows '+N more' when pendingCount > shown items", () => {
    const items = [
      { type: "conflict", label: "Item 1" },
      { type: "conflict", label: "Item 2" },
      { type: "conflict", label: "Item 3" },
      { type: "conflict", label: "Item 4" },
      { type: "conflict", label: "Item 5" },
    ];
    render(
      <InFlightSyncIndicator
        surface="calendar"
        state="synced-pending"
        pendingCount={8} // 8 total, 5 shown → "+3 more"
        pendingItems={items}
      />,
    );
    const container = screen.getByTestId("sync-indicator-calendar");
    fireEvent.mouseEnter(container);
    expect(screen.getByText("+3 more")).toBeTruthy();
  });

  it("17b. tooltip hidden when no pendingItems", () => {
    render(
      <InFlightSyncIndicator
        surface="calendar"
        state="synced-pending"
        pendingCount={3}
        pendingItems={[]}
      />,
    );
    const container = screen.getByTestId("sync-indicator-calendar");
    fireEvent.mouseEnter(container);
    expect(document.querySelector('[role="tooltip"]')).toBeNull();
  });
});

// ─── Test 19: lastSyncedAt display in idle and synced-pending ─────────────────

describe("InFlightSyncIndicator — lastSyncedAt display", () => {
  it("19. lastSyncedAt shown in both idle and synced-pending states", () => {
    const lastSync = new Date("2026-05-27T14:32:18Z");

    const { rerender } = render(
      <InFlightSyncIndicator
        surface="calendar"
        state="idle"
        pendingCount={0}
        lastSyncedAt={lastSync}
      />,
    );
    // timestamp is shown in idle
    expect(screen.getByText(lastSync.toLocaleTimeString())).toBeTruthy();

    rerender(
      <InFlightSyncIndicator
        surface="calendar"
        state="synced-pending"
        pendingCount={2}
        lastSyncedAt={lastSync}
      />,
    );
    // timestamp also shown in synced-pending
    expect(screen.getByText(lastSync.toLocaleTimeString())).toBeTruthy();
  });
});

// ─── Test 20: state label copy ────────────────────────────────────────────────

describe("InFlightSyncIndicator — state label copy", () => {
  it("20a. idle with lastSyncedAt shows 'Synced · last Xs ago'", () => {
    const recent = new Date(Date.now() - 12_000); // 12 seconds ago
    render(
      <InFlightSyncIndicator
        surface="calendar"
        state="idle"
        pendingCount={0}
        lastSyncedAt={recent}
      />,
    );
    expect(screen.getByText(/Synced · last/)).toBeTruthy();
  });

  it("20b. synced-pending shows 'Synced · N pending'", () => {
    render(
      <InFlightSyncIndicator
        surface="quickbooks"
        state="synced-pending"
        pendingCount={3}
      />,
    );
    expect(screen.getByText(/Synced · 3 pending/)).toBeTruthy();
  });

  it("20c. syncing shows 'Syncing N changes…'", () => {
    render(
      <InFlightSyncIndicator
        surface="quickbooks"
        state="syncing"
        pendingCount={4}
      />,
    );
    expect(screen.getByText("Syncing 4 changes…")).toBeTruthy();
  });

  it("20d. error shows 'Sync error · N pending'", () => {
    render(
      <InFlightSyncIndicator
        surface="calendar"
        state="error"
        pendingCount={2}
      />,
    );
    expect(screen.getByText("Sync error · 2 pending")).toBeTruthy();
  });

  it("20e. paused shows 'Paused · N queued'", () => {
    render(
      <InFlightSyncIndicator
        surface="quickbooks"
        state="paused"
        pendingCount={5}
      />,
    );
    expect(screen.getByText("Paused · 5 queued")).toBeTruthy();
  });
});

// ─── Test 24: SyncSurface type accepts "background-sync" ──────────────────────

describe("InFlightSyncIndicator — SyncSurface union", () => {
  it("24. background-sync surface renders without TypeScript error", () => {
    // This is primarily a compile-time test; render confirms no runtime error
    const { container } = render(
      <InFlightSyncIndicator
        surface="background-sync"
        state="idle"
        pendingCount={0}
      />,
    );
    expect(container.firstChild).not.toBeNull();
  });

  it("24b. all five SyncSurface values render without error", () => {
    const surfaces = [
      "dispatch",
      "mobile-sync",
      "calendar",
      "quickbooks",
      "background-sync",
    ] as const;
    surfaces.forEach((surface) => {
      expect(() =>
        render(
          <InFlightSyncIndicator
            key={surface}
            surface={surface}
            state="idle"
            pendingCount={0}
          />,
        ),
      ).not.toThrow();
    });
  });
});
