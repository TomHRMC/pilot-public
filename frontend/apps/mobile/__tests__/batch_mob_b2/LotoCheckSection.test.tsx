/**
 * LotoCheckSection unit tests (MOB-B2)
 *
 * Location: apps/mobile/__tests__/batch_mob_b2/LotoCheckSection.test.tsx
 */

import React from "react";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  act,
} from "@testing-library/react-native";

import { LotoCheckSection } from "../../features/jobs/components/detail/LotoCheckSection";

const mockConfirm = jest.fn().mockResolvedValue({});

jest.mock("../../features/offline-sync/hooks/useConfirmLoto", () => ({
  useConfirmLoto: () => ({
    confirm: mockConfirm,
    isPending: false,
    error: null,
  }),
}));

// MOB-B7: LotoCheckSection now uses useLotoPolicy — mock it with optional mode (default)
jest.mock("../../features/jobs/hooks/useLotoPolicy", () => ({
  useLotoPolicy: () => ({
    data: { loto_confirmation_required: false },
  }),
}));

jest.mock("../../database", () => ({
  database: {
    write: jest
      .fn()
      .mockImplementation(async (fn: () => Promise<unknown>) => fn()),
    get: jest.fn().mockReturnValue({ create: jest.fn() }),
  },
}));

const JOB_ID = "job-today-001";

describe("LotoCheckSection", () => {
  beforeEach(() => jest.clearAllMocks());

  it("renders all 3 LOTO items unchecked when existingConfirmations is empty", () => {
    render(
      <LotoCheckSection
        jobId={JOB_ID}
        existingConfirmations={[]}
        testID="loto-section"
      />,
    );

    expect(screen.getByTestId("loto-item-lockout_points")).toBeTruthy();
    expect(screen.getByTestId("loto-item-de_energized")).toBeTruthy();
    expect(screen.getByTestId("loto-item-tag_placement")).toBeTruthy();

    // None should show the confirmed checkmark emoji
    expect(screen.queryAllByText("✅")).toHaveLength(0);
  });

  it("shows confirmed item with ✅ and makes it non-interactive", () => {
    render(
      <LotoCheckSection
        jobId={JOB_ID}
        existingConfirmations={[
          {
            id: "loto-001",
            check_type: "lockout_points",
            confirmed_at: new Date().toISOString(),
          },
        ]}
        testID="loto-section"
      />,
    );

    // First item confirmed — ✅ visible
    expect(screen.getAllByText("✅")).toHaveLength(1);
  });

  it("calls confirm() with jobId and checkType on tap", async () => {
    render(
      <LotoCheckSection
        jobId={JOB_ID}
        existingConfirmations={[]}
        testID="loto-section"
      />,
    );

    await act(async () => {
      fireEvent.press(screen.getByTestId("loto-item-lockout_points"));
    });

    await waitFor(() => {
      expect(mockConfirm).toHaveBeenCalledWith(
        expect.objectContaining({
          jobId: JOB_ID,
          checkType: "lockout_points",
          confirmedAt: expect.any(Date),
        }),
      );
    });
  });

  it("does NOT call confirm() when tapping an already-confirmed item", async () => {
    render(
      <LotoCheckSection
        jobId={JOB_ID}
        existingConfirmations={[
          {
            id: "loto-001",
            check_type: "lockout_points",
            confirmed_at: new Date().toISOString(),
          },
        ]}
        testID="loto-section"
      />,
    );

    fireEvent.press(screen.getByTestId("loto-item-lockout_points"));

    await waitFor(() => {
      expect(mockConfirm).not.toHaveBeenCalled();
    });
  });
});
