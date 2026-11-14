/**
 * ConflictSummaryCard unit tests — MOB-B6
 *
 * Location: apps/mobile/features/voice-quote-creation/components/__tests__/ConflictSummaryCard.test.tsx
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react-native";
import { Linking } from "react-native";

import { ConflictSummaryCard } from "../ConflictSummaryCard";

// ── Helpers ───────────────────────────────────────────────────────────────────

const CONFLICT_PAYLOAD = {
  conflict_id: "conflict-abc-123",
  entity_type: "customer",
  conflict_type: "modified_modified",
  summary: "Both local and remote versions of this customer were modified.",
};

beforeEach(() => {
  jest.clearAllMocks();
});

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("ConflictSummaryCard", () => {
  it("renders conflict type and entity type from payload", () => {
    render(<ConflictSummaryCard payload={CONFLICT_PAYLOAD} />);

    expect(screen.getByTestId("conflict-summary-card")).toBeOnTheScreen();
    expect(screen.getByTestId("conflict-title")).toBeOnTheScreen();
    // Title should contain entity type and conflict type
    expect(screen.getByText(/Customer/)).toBeOnTheScreen();
    expect(screen.getByText(/Modified Modified/)).toBeOnTheScreen();
  });

  it("renders summary text from payload", () => {
    render(<ConflictSummaryCard payload={CONFLICT_PAYLOAD} />);

    expect(screen.getByTestId("conflict-summary")).toBeOnTheScreen();
    expect(
      screen.getByText(
        "Both local and remote versions of this customer were modified.",
      ),
    ).toBeOnTheScreen();
  });

  it("renders conflict ID", () => {
    render(<ConflictSummaryCard payload={CONFLICT_PAYLOAD} />);

    expect(screen.getByTestId("conflict-id")).toBeOnTheScreen();
    expect(screen.getByText(/conflict-abc-123/)).toBeOnTheScreen();
  });

  it("shows Resolve on web button", () => {
    render(<ConflictSummaryCard payload={CONFLICT_PAYLOAD} />);

    expect(screen.getByTestId("resolve-on-web-button")).toBeOnTheScreen();
    expect(screen.getByText("Resolve on web →")).toBeOnTheScreen();
  });

  it("pressing Resolve on web button attempts to open URL", async () => {
    const canOpenURLSpy = jest
      .spyOn(Linking, "canOpenURL")
      .mockResolvedValue(true);
    const openURLSpy = jest
      .spyOn(Linking, "openURL")
      .mockResolvedValue(undefined);

    render(<ConflictSummaryCard payload={CONFLICT_PAYLOAD} />);

    fireEvent.press(screen.getByTestId("resolve-on-web-button"));

    // Wait for async operations
    await new Promise((resolve) => setTimeout(resolve, 50));

    expect(canOpenURLSpy).toHaveBeenCalledWith(
      expect.stringContaining("conflict-abc-123"),
    );
    expect(openURLSpy).toHaveBeenCalledWith(
      expect.stringContaining("conflict-abc-123"),
    );
  });

  it("renders default summary when no summary provided", () => {
    render(
      <ConflictSummaryCard
        payload={{
          conflict_id: "cid-999",
          entity_type: "job",
          conflict_type: "deleted_modified",
        }}
      />,
    );

    expect(screen.getByTestId("conflict-summary")).toBeOnTheScreen();
    // Should show default description mentioning entity type
    expect(screen.getByText(/job/)).toBeOnTheScreen();
  });

  it("renders gracefully when payload is empty", () => {
    render(<ConflictSummaryCard payload={{}} />);
    expect(screen.getByTestId("conflict-summary-card")).toBeOnTheScreen();
    expect(screen.getByTestId("resolve-on-web-button")).toBeOnTheScreen();
  });
});
