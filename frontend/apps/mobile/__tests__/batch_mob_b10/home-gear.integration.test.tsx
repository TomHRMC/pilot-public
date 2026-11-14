/**
 * Home gear icon integration tests (MOB-B10)
 *
 * Verifies: gear button renders in HomeLayout, pressing it routes to settings/index
 */
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react-native";
import HomeLayout from "../../app/(tabs)/(home)/_layout";

// ── Expo Router mock ──────────────────────────────────────────────────────────
// Mock Stack to render Stack.Screen options (including headerRight) so we can
// find the GearButton rendered by the layout.

const mockPush = jest.fn();

jest.mock("expo-router", () => {
  const React = require("react");
  const { Fragment } = React;

  // Minimal Stack mock: renders Stack.Screen children including headerRight
  const ScreenMock = ({
    options,
  }: {
    name: string;
    options?: {
      headerRight?: () => React.ReactNode;
      headerShown?: boolean;
    };
  }) => {
    if (options?.headerRight) {
      return React.createElement(Fragment, null, options.headerRight());
    }
    return null;
  };

  const StackMock = Object.assign(
    ({ children }: { children: React.ReactNode }) =>
      React.createElement(Fragment, null, children),
    { Screen: ScreenMock },
  );

  return {
    useRouter: () => ({ push: mockPush, back: jest.fn(), replace: jest.fn() }),
    useLocalSearchParams: () => ({}),
    router: { push: mockPush, back: jest.fn() },
    Link: ({ children }: { children: React.ReactNode }) => children,
    Stack: StackMock,
  };
});

beforeEach(() => mockPush.mockClear());

// ── WatermelonDB mock ─────────────────────────────────────────────────────────

jest.mock("../../database", () => ({
  database: {
    write: jest.fn((fn: () => unknown) => fn()),
    get: jest.fn(() => ({
      create: jest.fn((fn: (r: Record<string, unknown>) => void) => {
        const record = { id: "mock-id", localSyncStatus: "pending" };
        fn(record);
        return Promise.resolve(record);
      }),
    })),
  },
}));

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("HomeLayout gear icon", () => {
  it("gear button with testID='home-gear-button' is present in the layout", () => {
    render(<HomeLayout />);
    expect(screen.getByTestId("home-gear-button")).toBeTruthy();
  });

  it("pressing gear button calls router.push with settings path", () => {
    render(<HomeLayout />);

    fireEvent.press(screen.getByTestId("home-gear-button"));

    expect(mockPush).toHaveBeenCalledWith(expect.stringContaining("settings"));
  });
});
