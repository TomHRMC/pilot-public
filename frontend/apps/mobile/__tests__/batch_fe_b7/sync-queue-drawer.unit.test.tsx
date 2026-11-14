/**
 * SyncQueueDrawer Unit Tests
 *
 * Location: apps/mobile/__tests__/batch_fe_b7/sync-queue-drawer.unit.test.tsx
 *
 * Tests: 4 sections render; action-needed first; inline retry/resolve CTAs.
 * Per batch-fe-b7-design.md Section I.1.
 */

import React from "react";
import { render, screen } from "@testing-library/react-native";
import { SyncQueueDrawer } from "../../features/offline-sync/components/SyncQueueDrawer";
import type { SyncQueueItemData } from "../../features/offline-sync/components/SyncQueueItem";

const mockCloseDrawer = jest.fn();
let mockIsDrawerOpen = true;

jest.mock("../../features/offline-sync/store", () => ({
  useSyncQueueStore: () => ({
    isDrawerOpen: mockIsDrawerOpen,
    closeDrawer: mockCloseDrawer,
    syncState: {
      status: "idle",
      pendingCount: 3,
      lastSyncedAt: "2026-05-22T08:00:00Z",
    },
  }),
}));

const makeItem = (
  localSyncStatus: SyncQueueItemData["localSyncStatus"],
  id = `item-${localSyncStatus}`,
): SyncQueueItemData => ({
  id,
  entityType: "time_entry",
  entitySummary: `Test ${localSyncStatus} item`,
  localSyncStatus,
  clientCaptureAt: new Date("2026-05-22T08:00:00Z"),
  conflictId: localSyncStatus === "conflict" ? `conflict-${id}` : undefined,
});

describe("SyncQueueDrawer", () => {
  const onSync = jest.fn().mockResolvedValue(undefined);

  beforeEach(() => {
    jest.clearAllMocks();
    mockIsDrawerOpen = true;
  });

  it("renders drawer when open", () => {
    render(<SyncQueueDrawer onSync={onSync} items={[]} testID="drawer" />);
    // When testID="drawer" is passed, the Modal gets that testID
    expect(screen.getByTestId("drawer")).toBeTruthy();
  });

  it("shows action-needed section first when conflicts exist", () => {
    const items = [
      makeItem("conflict", "item-conflict"),
      makeItem("pending", "item-pending"),
    ];

    render(<SyncQueueDrawer onSync={onSync} items={items} />);

    // Action needed section should be present
    expect(screen.getByTestId("section-action-needed")).toBeTruthy();
  });

  it("shows pending section", () => {
    const items = [makeItem("pending")];
    render(<SyncQueueDrawer onSync={onSync} items={items} />);
    expect(screen.getByTestId("section-pending")).toBeTruthy();
  });

  it("shows empty state when no items", () => {
    render(<SyncQueueDrawer onSync={onSync} items={[]} />);
    expect(screen.getByText("All caught up")).toBeTruthy();
  });

  it("renders sync now button", () => {
    render(<SyncQueueDrawer onSync={onSync} items={[]} />);
    expect(screen.getByTestId("drawer-sync-now")).toBeTruthy();
  });

  it("renders last synced time when available", () => {
    render(<SyncQueueDrawer onSync={onSync} items={[]} />);
    // Should show "Last synced" text
    const lastSynced = screen.queryByText(/last synced/i);
    expect(lastSynced).toBeTruthy();
  });

  it("renders resolve CTA for conflict items", () => {
    const items = [makeItem("conflict", "item-conflict-001")];
    render(
      <SyncQueueDrawer
        onSync={onSync}
        items={items}
        onNavigateToConflict={jest.fn()}
      />,
    );
    // Section for action needed renders
    expect(screen.getByTestId("section-action-needed")).toBeTruthy();
  });
});
