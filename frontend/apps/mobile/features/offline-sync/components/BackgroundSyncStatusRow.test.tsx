/**
 * BackgroundSyncStatusRow unit tests — FE-B9
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react-native";
import { BackgroundSyncStatusRow } from "./BackgroundSyncStatusRow";
import type { BackgroundSyncStatus } from "../hooks/useBackgroundSyncStatus";

const makeStatus = (
  overrides: Partial<BackgroundSyncStatus>,
): BackgroundSyncStatus => ({
  state: "recent_success",
  lastAttemptAt: new Date("2026-05-25T14:00:00Z"),
  itemsSynced: 3,
  retryCount: 0,
  ...overrides,
});

describe("BackgroundSyncStatusRow", () => {
  it("renders 'Last background sync: X min ago (N items)' for recent_success", () => {
    const status = makeStatus({ state: "recent_success", itemsSynced: 5 });
    render(<BackgroundSyncStatusRow status={status} onPress={jest.fn()} />);
    expect(screen.getByTestId("bg-sync-dot-recent_success")).toBeOnTheScreen();
    expect(screen.getByTestId("bg-sync-subtitle")).toBeOnTheScreen();
  });

  it("renders recent_success_no_work state", () => {
    const status = makeStatus({
      state: "recent_success_no_work",
      itemsSynced: 0,
    });
    render(<BackgroundSyncStatusRow status={status} onPress={jest.fn()} />);
    expect(
      screen.getByTestId("bg-sync-dot-recent_success_no_work"),
    ).toBeOnTheScreen();
    expect(screen.getByText(/Nothing to sync/)).toBeOnTheScreen();
  });

  it("renders amber state for recent_failed", () => {
    const status = makeStatus({ state: "recent_failed" });
    render(<BackgroundSyncStatusRow status={status} onPress={jest.fn()} />);
    expect(screen.getByTestId("bg-sync-dot-recent_failed")).toBeOnTheScreen();
    expect(screen.getByText(/Background sync degraded/)).toBeOnTheScreen();
  });

  it("renders disabled state with correct copy", () => {
    const status = makeStatus({ state: "disabled", lastAttemptAt: null });
    render(<BackgroundSyncStatusRow status={status} onPress={jest.fn()} />);
    expect(screen.getByTestId("bg-sync-dot-disabled")).toBeOnTheScreen();
    expect(screen.getByText(/Background sync off/)).toBeOnTheScreen();
    expect(
      screen.getByText(/Items will sync when you open the app/),
    ).toBeOnTheScreen();
  });

  it("renders never_run state as 'Background sync ready'", () => {
    const status = makeStatus({ state: "never_run", lastAttemptAt: null });
    render(<BackgroundSyncStatusRow status={status} onPress={jest.fn()} />);
    expect(screen.getByTestId("bg-sync-dot-never_run")).toBeOnTheScreen();
    expect(screen.getByText(/Background sync ready/)).toBeOnTheScreen();
  });

  it("renders amber + OS-settings link for no_permission", () => {
    const status = makeStatus({ state: "no_permission", lastAttemptAt: null });
    render(<BackgroundSyncStatusRow status={status} onPress={jest.fn()} />);
    expect(screen.getByTestId("bg-sync-dot-no_permission")).toBeOnTheScreen();
    expect(screen.getByText(/Enable notifications/)).toBeOnTheScreen();
    expect(
      screen.getByTestId("background-sync-status-row-pressable"),
    ).toBeOnTheScreen();
  });

  it("invokes onPress callback when actionable state is tapped", () => {
    const mockPress = jest.fn();
    const status = makeStatus({ state: "disabled" });
    render(<BackgroundSyncStatusRow status={status} onPress={mockPress} />);
    fireEvent.press(screen.getByTestId("background-sync-status-row-pressable"));
    expect(mockPress).toHaveBeenCalledTimes(1);
  });

  it("does NOT render pressable when state is recent_success (not actionable)", () => {
    const status = makeStatus({ state: "recent_success" });
    render(<BackgroundSyncStatusRow status={status} onPress={jest.fn()} />);
    expect(
      screen.queryByTestId("background-sync-status-row-pressable"),
    ).not.toBeOnTheScreen();
  });
});
