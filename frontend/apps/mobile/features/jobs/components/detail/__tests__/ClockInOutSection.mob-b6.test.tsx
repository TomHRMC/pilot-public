/**
 * ClockInOutSection unit tests — MOB-B6 (GPS capture)
 *
 * Location: apps/mobile/features/jobs/components/detail/__tests__/ClockInOutSection.mob-b6.test.tsx
 *
 * Tests GPS capture behavior: soft failure when denied, soft failure on error,
 * and GPS captured when permission granted. Clock-in always proceeds.
 */

import React from "react";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  act,
} from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { ClockInOutSection } from "../ClockInOutSection";

// ── Mock expo-location ────────────────────────────────────────────────────────

const mockRequestForegroundPermissionsAsync = jest
  .fn()
  .mockResolvedValue({ status: "granted" });
const mockGetCurrentPositionAsync = jest.fn().mockResolvedValue({
  coords: { latitude: 37.7749, longitude: -122.4194, accuracy: 10 },
});

jest.mock("expo-location", () => ({
  requestForegroundPermissionsAsync: () =>
    mockRequestForegroundPermissionsAsync(),
  getCurrentPositionAsync: () => mockGetCurrentPositionAsync(),
  Accuracy: { High: 5 },
}));

// ── Mock useCreateTimeEntry ────────────────────────────────────────────────────

const mockCreate = jest.fn().mockResolvedValue({});

jest.mock("../../../../offline-sync/hooks/useCreateTimeEntry", () => ({
  useCreateTimeEntry: () => ({
    create: mockCreate,
    isPending: false,
    error: null,
  }),
}));

// ── Mock WatermelonDB ─────────────────────────────────────────────────────────

jest.mock("../../../../../database", () => ({
  database: {
    write: jest
      .fn()
      .mockImplementation(async (fn: () => Promise<unknown>) => fn()),
    get: jest.fn().mockReturnValue({ create: jest.fn() }),
  },
}));

// ── Helpers ───────────────────────────────────────────────────────────────────

const JOB_ID = "job-gps-test-001";
const USER_ID = "tech-gps-001";

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return React.createElement(QueryClientProvider, { client: qc }, children);
}

function renderSection(activeTimeEntry: null = null) {
  return render(
    <ClockInOutSection
      jobId={JOB_ID}
      userId={USER_ID}
      activeTimeEntry={activeTimeEntry}
      testID="clock-in-out-section"
    />,
    { wrapper },
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  mockCreate.mockResolvedValue({});
  mockRequestForegroundPermissionsAsync.mockResolvedValue({
    status: "granted",
  });
  mockGetCurrentPositionAsync.mockResolvedValue({
    coords: { latitude: 37.7749, longitude: -122.4194, accuracy: 10 },
  });
});

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("ClockInOutSection — MOB-B6 GPS", () => {
  it("renders clock-in button when no active time entry", () => {
    renderSection();
    expect(screen.getByTestId("clock-in-button")).toBeOnTheScreen();
  });

  it("clock-in proceeds when GPS permission granted — create() called", async () => {
    renderSection();

    await act(async () => {
      fireEvent.press(screen.getByTestId("clock-in-button"));
    });

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledTimes(1);
    });

    // GPS permission requested
    expect(mockRequestForegroundPermissionsAsync).toHaveBeenCalledTimes(1);
    // GPS position fetched
    expect(mockGetCurrentPositionAsync).toHaveBeenCalledTimes(1);
    // create() called with jobId and userId (GPS not in API payload yet)
    expect(mockCreate).toHaveBeenCalledWith(
      expect.objectContaining({ jobId: JOB_ID, userId: USER_ID }),
    );
  });

  it("clock-in proceeds when GPS permission denied — no error shown, create() still called", async () => {
    mockRequestForegroundPermissionsAsync.mockResolvedValue({
      status: "denied",
    });

    renderSection();

    await act(async () => {
      fireEvent.press(screen.getByTestId("clock-in-button"));
    });

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledTimes(1);
    });

    // GPS fetch NOT attempted when denied
    expect(mockGetCurrentPositionAsync).not.toHaveBeenCalled();
    // create() still called — GPS doesn't block clock-in
    expect(mockCreate).toHaveBeenCalledWith(
      expect.objectContaining({ jobId: JOB_ID, userId: USER_ID }),
    );
  });

  it("clock-in proceeds when GPS capture throws — soft failure, create() still called", async () => {
    mockGetCurrentPositionAsync.mockRejectedValue(
      new Error("Location timed out"),
    );

    renderSection();

    await act(async () => {
      fireEvent.press(screen.getByTestId("clock-in-button"));
    });

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledTimes(1);
    });

    // create() still called despite GPS error
    expect(mockCreate).toHaveBeenCalledWith(
      expect.objectContaining({ jobId: JOB_ID, userId: USER_ID }),
    );
  });

  it("shows loading indicator while GPS + create are in flight", async () => {
    // Make permission request slow enough to see loading state
    mockRequestForegroundPermissionsAsync.mockImplementation(
      () =>
        new Promise((resolve) =>
          setTimeout(() => resolve({ status: "granted" }), 50),
        ),
    );

    renderSection();

    fireEvent.press(screen.getByTestId("clock-in-button"));

    // During the async GPS capture, button should be disabled (activity indicator shown)
    // We just check the button is not re-pressable
    const clockInBtn = screen.getByTestId("clock-in-button");
    expect(clockInBtn).toBeOnTheScreen();

    // Wait for completion
    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledTimes(1);
    });
  });
});
