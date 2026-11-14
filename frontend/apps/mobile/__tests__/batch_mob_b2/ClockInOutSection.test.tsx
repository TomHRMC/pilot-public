/**
 * ClockInOutSection unit tests (MOB-B2)
 *
 * Location: apps/mobile/__tests__/batch_mob_b2/ClockInOutSection.test.tsx
 */

import React from "react";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  act,
} from "@testing-library/react-native";

import { ClockInOutSection } from "../../features/jobs/components/detail/ClockInOutSection";

// ── Mocks ──────────────────────────────────────────────────────────────────────

const mockCreate = jest.fn().mockResolvedValue({});

// ── Mock expo-location (added by MOB-B6 — must mock or test runner crashes) ───
jest.mock("expo-location", () => ({
  requestForegroundPermissionsAsync: jest
    .fn()
    .mockResolvedValue({ status: "granted" }),
  getCurrentPositionAsync: jest.fn().mockResolvedValue({
    coords: { latitude: 37.7749, longitude: -122.4194, accuracy: 10 },
  }),
  Accuracy: { High: 5 },
}));

jest.mock("../../features/offline-sync/hooks/useCreateTimeEntry", () => ({
  useCreateTimeEntry: () => ({
    create: mockCreate,
    isPending: false,
    error: null,
  }),
}));

// Mock database (not used directly, but imported transitively)
jest.mock("../../database", () => ({
  database: {
    write: jest
      .fn()
      .mockImplementation(async (fn: () => Promise<unknown>) => fn()),
    get: jest.fn().mockReturnValue({ create: jest.fn() }),
  },
}));

// ── Test data ─────────────────────────────────────────────────────────────────

const TODAY = new Date().toISOString().slice(0, 10);

const ACTIVE_TIME_ENTRY = {
  id: "te-001",
  job_id: "job-today-001",
  user_id: "tech-user-001",
  started_at: `${TODAY}T09:00:00Z`,
  ended_at: null as null,
  hours: null as null,
  notes: null as null,
  hourly_rate_cents: 8500,
};

describe("ClockInOutSection", () => {
  const jobId = "job-today-001";
  const userId = "tech-user-001";

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders Clock In button when activeTimeEntry is null", () => {
    render(
      <ClockInOutSection
        jobId={jobId}
        userId={userId}
        activeTimeEntry={null}
        testID="clock-section"
      />,
    );

    expect(screen.getByTestId("clock-in-button")).toBeTruthy();
    expect(screen.queryByTestId("clock-out-button")).toBeNull();
  });

  it("renders running timer and Clock Out when activeTimeEntry is set", () => {
    render(
      <ClockInOutSection
        jobId={jobId}
        userId={userId}
        activeTimeEntry={ACTIVE_TIME_ENTRY}
        testID="clock-section"
      />,
    );

    expect(screen.getByTestId("clock-out-button")).toBeTruthy();
    expect(screen.getByTestId("elapsed-timer")).toBeTruthy();
    expect(screen.queryByTestId("clock-in-button")).toBeNull();
  });

  it("calls create() with jobId and userId on Clock In", async () => {
    render(
      <ClockInOutSection
        jobId={jobId}
        userId={userId}
        activeTimeEntry={null}
        testID="clock-section"
      />,
    );

    await act(async () => {
      fireEvent.press(screen.getByTestId("clock-in-button"));
    });

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith(
        expect.objectContaining({ jobId, userId }),
      );
    });
  });

  it("shows ETC prompt modal when Clock Out is pressed", async () => {
    render(
      <ClockInOutSection
        jobId={jobId}
        userId={userId}
        activeTimeEntry={ACTIVE_TIME_ENTRY}
        testID="clock-section"
      />,
    );

    act(() => {
      fireEvent.press(screen.getByTestId("clock-out-button"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("etc-prompt-modal")).toBeTruthy();
      expect(screen.getByTestId("etc-hours-input")).toBeTruthy();
    });
  });

  it("calls create() with hoursRemainingEstimate when ETC Done is pressed", async () => {
    render(
      <ClockInOutSection
        jobId={jobId}
        userId={userId}
        activeTimeEntry={ACTIVE_TIME_ENTRY}
        testID="clock-section"
      />,
    );

    // Open ETC modal
    act(() => {
      fireEvent.press(screen.getByTestId("clock-out-button"));
    });

    await waitFor(() =>
      expect(screen.getByTestId("etc-hours-input")).toBeTruthy(),
    );

    // Enter hours and confirm
    fireEvent.changeText(screen.getByTestId("etc-hours-input"), "1.5");

    await act(async () => {
      fireEvent.press(screen.getByTestId("etc-done-button"));
    });

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          jobId,
          userId,
          hoursRemainingEstimate: 1.5,
          endedAt: expect.any(Date),
        }),
      );
    });
  });

  it("calls create() WITHOUT hoursRemainingEstimate when ETC Skip is pressed", async () => {
    render(
      <ClockInOutSection
        jobId={jobId}
        userId={userId}
        activeTimeEntry={ACTIVE_TIME_ENTRY}
        testID="clock-section"
      />,
    );

    act(() => {
      fireEvent.press(screen.getByTestId("clock-out-button"));
    });

    await waitFor(() =>
      expect(screen.getByTestId("etc-skip-button")).toBeTruthy(),
    );

    await act(async () => {
      fireEvent.press(screen.getByTestId("etc-skip-button"));
    });

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          jobId,
          userId,
          endedAt: expect.any(Date),
        }),
      );
      // No hoursRemainingEstimate
      expect(mockCreate).toHaveBeenCalledWith(
        expect.not.objectContaining({
          hoursRemainingEstimate: expect.anything(),
        }),
      );
    });
  });
});
