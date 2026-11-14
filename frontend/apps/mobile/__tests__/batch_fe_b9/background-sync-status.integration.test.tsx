/**
 * Background sync status row integration tests — FE-B9
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react-native";
import { BackgroundSyncStatusRow } from "../../features/offline-sync/components/BackgroundSyncStatusRow";
import type { BackgroundSyncStatus } from "../../features/offline-sync/hooks/useBackgroundSyncStatus";

function makeStatus(
  overrides: Partial<BackgroundSyncStatus> = {},
): BackgroundSyncStatus {
  return {
    state: "recent_success",
    lastAttemptAt: new Date("2026-05-25T13:00:00Z"),
    itemsSynced: 2,
    retryCount: 0,
    ...overrides,
  };
}

describe("BackgroundSyncStatusRow integration", () => {
  it("recent_success renders with correct copy and margin dot", () => {
    render(
      <BackgroundSyncStatusRow status={makeStatus()} onPress={jest.fn()} />,
    );
    expect(screen.getByTestId("bg-sync-dot-recent_success")).toBeOnTheScreen();
    expect(screen.getByText(/Background sync/)).toBeOnTheScreen();
  });

  it("no_permission renders amber state + OS settings deep-link row", () => {
    render(
      <BackgroundSyncStatusRow
        status={makeStatus({ state: "no_permission", lastAttemptAt: null })}
        onPress={jest.fn()}
      />,
    );
    expect(screen.getByTestId("bg-sync-dot-no_permission")).toBeOnTheScreen();
    expect(screen.getByText(/Enable notifications/)).toBeOnTheScreen();
    // Pressable should be rendered for actionable state
    expect(
      screen.getByTestId("background-sync-status-row-pressable"),
    ).toBeOnTheScreen();
  });

  it("disabled state shows neutral copy + settings link", () => {
    render(
      <BackgroundSyncStatusRow
        status={makeStatus({ state: "disabled", lastAttemptAt: null })}
        onPress={jest.fn()}
      />,
    );
    expect(
      screen.getByText(/Items will sync when you open the app/),
    ).toBeOnTheScreen();
    expect(
      screen.getByTestId("background-sync-status-row-pressable"),
    ).toBeOnTheScreen();
  });

  it("tap invokes onPress callback", () => {
    const mockPress = jest.fn();
    render(
      <BackgroundSyncStatusRow
        status={makeStatus({ state: "disabled" })}
        onPress={mockPress}
      />,
    );
    fireEvent.press(screen.getByTestId("background-sync-status-row-pressable"));
    expect(mockPress).toHaveBeenCalledTimes(1);
  });
});
