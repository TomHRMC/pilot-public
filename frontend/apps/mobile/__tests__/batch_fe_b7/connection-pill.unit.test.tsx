/**
 * ConnectionStatePill Unit Tests
 *
 * Location: apps/mobile/__tests__/batch_fe_b7/connection-pill.unit.test.tsx
 *
 * Tests: all 4 states render correctly; tap opens drawer.
 * Per batch-fe-b7-design.md Section I.1.
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react-native";
import { ConnectionStatePill } from "../../features/offline-sync/components/ConnectionStatePill";

// Mock useSyncQueueStore
const mockOpenDrawer = jest.fn();
let mockSyncState = {
  status: "idle" as string,
  pendingCount: 0,
  lastSyncedAt: null as string | null,
};

jest.mock("../../features/offline-sync/store", () => ({
  useSyncQueueStore: () => ({
    syncState: mockSyncState,
    openDrawer: mockOpenDrawer,
  }),
}));

describe("ConnectionStatePill", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSyncState = { status: "idle", pendingCount: 0, lastSyncedAt: null };
  });

  it("renders null when idle with 0 pending (hidden state)", () => {
    mockSyncState = { status: "idle", pendingCount: 0, lastSyncedAt: null };
    const { toJSON } = render(<ConnectionStatePill />);
    expect(toJSON()).toBeNull();
  });

  it("renders amber pill when pending items exist", () => {
    mockSyncState = { status: "idle", pendingCount: 3, lastSyncedAt: null };
    render(<ConnectionStatePill />);
    expect(screen.getByTestId("connection-state-pill")).toBeTruthy();
    expect(screen.getByText("3 pending")).toBeTruthy();
  });

  it("renders 'Syncing…' pill when syncing", () => {
    mockSyncState = {
      status: "syncing" as string,
      pendingCount: 5,
      lastSyncedAt: null,
    };
    render(<ConnectionStatePill />);
    expect(screen.getByText("Syncing…")).toBeTruthy();
  });

  it("renders error pill when sync fails", () => {
    mockSyncState = {
      status: "error" as string,
      pendingCount: 2,
      lastSyncedAt: null,
    };
    render(<ConnectionStatePill />);
    expect(screen.getByText("Sync error")).toBeTruthy();
  });

  it("calls openDrawer when tapped", () => {
    mockSyncState = { status: "idle", pendingCount: 5, lastSyncedAt: null };
    render(<ConnectionStatePill />);
    const pill = screen.getByTestId("connection-state-pill");
    fireEvent.press(pill);
    expect(mockOpenDrawer).toHaveBeenCalledTimes(1);
  });

  it("has correct accessibility label", () => {
    mockSyncState = { status: "idle", pendingCount: 3, lastSyncedAt: null };
    render(<ConnectionStatePill />);
    const pill = screen.getByTestId("connection-state-pill");
    expect(pill.props.accessibilityLabel).toBe("3 pending");
  });
});
