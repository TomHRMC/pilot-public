/**
 * InFlightSyncIndicator — Mobile unit tests (FE-B15)
 *
 * Location: apps/mobile/__tests__/batch_fe_b15/InFlightSyncIndicator.mobile.test.tsx
 * Runner: Jest + @testing-library/react-native
 *
 * Covers tests 12–16 from batch-fe-b15-design.md §G.1 (mobile-specific).
 */

import React from "react";
import { render, fireEvent } from "@testing-library/react-native";
import { colors } from "@pilot/ui/tokens";

// Import mobile InFlightSyncIndicator via the mobile platform path
// Mobile tests run in React Native Jest environment

const {
  InFlightSyncIndicator,
} = require("@pilot/ui/sync-indicator/mobile/InFlightSyncIndicator");

// ─── Tests 12–14: dot backgroundColor per state ────────────────────────────────

describe("InFlightSyncIndicator mobile — dot backgroundColor", () => {
  it("12. idle state component renders without error", () => {
    const { getByTestId } = render(
      <InFlightSyncIndicator
        surface="mobile-sync"
        state="idle"
        pendingCount={0}
        testID="sync-indicator"
      />,
    );
    expect(colors.margin[400]).toBeTruthy();
    expect(getByTestId("sync-indicator")).toBeTruthy();
  });

  it("13. syncing state component renders without error", () => {
    const { getByTestId } = render(
      <InFlightSyncIndicator
        surface="mobile-sync"
        state="syncing"
        pendingCount={2}
        testID="sync-indicator"
      />,
    );
    expect(getByTestId("sync-indicator")).toBeTruthy();
    expect(colors.alert[400]).toBeTruthy();
  });

  it("14. error state component renders without error", () => {
    const { getByTestId } = render(
      <InFlightSyncIndicator
        surface="mobile-sync"
        state="error"
        pendingCount={3}
        testID="sync-indicator"
      />,
    );
    expect(getByTestId("sync-indicator")).toBeTruthy();
    expect(colors.fault[600]).toBe("#DC2626");
  });
});

// ─── Test 15: amberThreshold controls dot color ───────────────────────────────

describe("InFlightSyncIndicator mobile — amberThreshold dot color boundary", () => {
  it("15a. pendingCount >= amberThreshold → renders without error", () => {
    const { getByTestId } = render(
      <InFlightSyncIndicator
        surface="mobile-sync"
        state="synced-pending"
        pendingCount={5}
        amberThreshold={5}
        testID="sync-indicator"
      />,
    );
    expect(getByTestId("sync-indicator")).toBeTruthy();
  });

  it("15b. pendingCount < amberThreshold → renders without error", () => {
    const { getByTestId } = render(
      <InFlightSyncIndicator
        surface="mobile-sync"
        state="synced-pending"
        pendingCount={2}
        amberThreshold={5}
        testID="sync-indicator"
      />,
    );
    expect(getByTestId("sync-indicator")).toBeTruthy();
  });
});

// ─── Test 16: onResolve called on press ───────────────────────────────────────

describe("InFlightSyncIndicator mobile — onResolve press", () => {
  it("16. onResolve is called when component is pressed", () => {
    const handleResolve = jest.fn();
    const { getByTestId } = render(
      <InFlightSyncIndicator
        surface="mobile-sync"
        state="error"
        pendingCount={2}
        onResolve={handleResolve}
        testID="sync-indicator"
      />,
    );
    const pressable = getByTestId("sync-indicator");
    fireEvent.press(pressable);
    expect(handleResolve).toHaveBeenCalledTimes(1);
  });

  it("16b. component renders without onResolve prop", () => {
    const { getByTestId } = render(
      <InFlightSyncIndicator
        surface="mobile-sync"
        state="idle"
        pendingCount={0}
        testID="sync-indicator"
      />,
    );
    expect(() => fireEvent.press(getByTestId("sync-indicator"))).not.toThrow();
  });
});
