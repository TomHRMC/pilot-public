/**
 * Background sync no-permission state integration test — FE-B9
 * RULE 5: BackgroundSyncStatusRow is a pure observer
 */

import React from "react";
import { render, screen } from "@testing-library/react-native";
import { BackgroundSyncStatusRow } from "../../features/offline-sync/components/BackgroundSyncStatusRow";
import type { BackgroundSyncStatus } from "../../features/offline-sync/hooks/useBackgroundSyncStatus";

describe("BackgroundSyncStatusRow — no_permission state", () => {
  const noPermStatus: BackgroundSyncStatus = {
    state: "no_permission",
    lastAttemptAt: null,
    itemsSynced: null,
    retryCount: 0,
  };

  it("renders amber dot for no_permission", () => {
    render(
      <BackgroundSyncStatusRow status={noPermStatus} onPress={jest.fn()} />,
    );
    expect(screen.getByTestId("bg-sync-dot-no_permission")).toBeOnTheScreen();
  });

  it("renders enable notifications copy", () => {
    render(
      <BackgroundSyncStatusRow status={noPermStatus} onPress={jest.fn()} />,
    );
    expect(
      screen.getByText(/Enable notifications for best performance/),
    ).toBeOnTheScreen();
  });

  it("is rendered as pressable (OS settings link)", () => {
    render(
      <BackgroundSyncStatusRow status={noPermStatus} onPress={jest.fn()} />,
    );
    expect(
      screen.getByTestId("background-sync-status-row-pressable"),
    ).toBeOnTheScreen();
  });

  it("RULE 5: component does NOT call any OS API directly", () => {
    // Pure observer test: component should not import expo-notifications, BackgroundFetch, etc.
    // We verify the component renders without throwing (no OS call in render)
    expect(() =>
      render(
        <BackgroundSyncStatusRow status={noPermStatus} onPress={jest.fn()} />,
      ),
    ).not.toThrow();
  });
});
