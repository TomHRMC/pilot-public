/**
 * Sync Screen integration tests (MOB-B2)
 *
 * Location: apps/mobile/__tests__/batch_mob_b2/sync-screen.integration.test.tsx
 *
 * Verifies that PLACEHOLDER_ITEMS is replaced with usePendingSyncItems()
 * and the SyncQueueSection components receive real items.
 */

import React from "react";
import { render, screen, waitFor } from "@testing-library/react-native";

// ── Import screen under test ───────────────────────────────────────────────────

import SyncPendingScreen from "../../app/(tabs)/(home)/sync/index";

// ── Mocks ──────────────────────────────────────────────────────────────────────

jest.mock("expo-router", () => ({
  useRouter: () => ({ push: jest.fn(), back: jest.fn() }),
}));

// RoleGate passes children through — can't reference React in factory,
// so use __esModule + a named export with require inside.
jest.mock("@pilot/ui", () => {
  const { View } = require("react-native");
  return {
    RoleGate: ({ children }: { children: unknown }) => children,
  };
});

jest.mock("../../features/offline-sync/store", () => ({
  useSyncQueueStore: () => ({
    syncState: { status: "idle", pendingCount: 2, lastSyncedAt: null },
  }),
}));

jest.mock("../../features/offline-sync/components/SyncNowButton", () => ({
  SyncNowButton: () => null,
}));

// Mock usePendingSyncItems to return controlled test data
const MOCK_PENDING_ITEMS = [
  {
    id: "te-001",
    entityType: "time_entry" as const,
    entitySummary: "Time entry — Job today-001 at 9:00 AM",
    localSyncStatus: "pending" as const,
    clientCaptureAt: new Date(),
  },
  {
    id: "exp-001",
    entityType: "expense" as const,
    entitySummary: "Expense — materials · $45.00",
    localSyncStatus: "failed" as const,
    clientCaptureAt: new Date(),
  },
];

jest.mock("../../features/offline-sync/hooks/usePendingSyncItems", () => ({
  usePendingSyncItems: () => ({
    items: MOCK_PENDING_ITEMS,
    totalCount: MOCK_PENDING_ITEMS.length,
  }),
}));

jest.mock("../../database", () => ({
  database: {
    get: jest.fn().mockReturnValue({
      query: jest
        .fn()
        .mockReturnValue({ fetch: jest.fn().mockResolvedValue([]) }),
    }),
  },
}));

jest.mock("@nozbe/watermelondb", () => ({
  Q: { where: jest.fn(), oneOf: jest.fn() },
}));

describe("Sync Screen — PLACEHOLDER_ITEMS replaced", () => {
  it("renders the sync screen without crashing (no undefined PLACEHOLDER_ITEMS)", async () => {
    render(React.createElement(SyncPendingScreen));

    await waitFor(() => {
      expect(screen.getByTestId("sync-pending-screen")).toBeTruthy();
    });
  });

  it("shows the pending section when a pending item exists", async () => {
    render(React.createElement(SyncPendingScreen));

    await waitFor(() => {
      expect(screen.getByTestId("screen-pending")).toBeTruthy();
    });
  });

  it("shows the failed section when a failed item exists", async () => {
    render(React.createElement(SyncPendingScreen));

    await waitFor(() => {
      expect(screen.getByTestId("screen-failed")).toBeTruthy();
    });
  });

  it("does NOT show the 'All synced' empty state when items exist", async () => {
    render(React.createElement(SyncPendingScreen));

    await waitFor(() => {
      expect(screen.queryByText("All synced")).toBeNull();
    });
  });
});
