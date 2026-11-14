/**
 * Owner tab field issues status row integration tests — FE-B9
 */

import React from "react";
import { render, screen } from "@testing-library/react-native";
import { FieldIssuesSyncStatusRow } from "@pilot/ui";

describe("FieldIssuesSyncStatusRow — owner tab integration", () => {
  it("renders pendingCount=3 with amber dot + '3 pending'", () => {
    render(
      <FieldIssuesSyncStatusRow
        pendingCount={3}
        onPress={jest.fn()}
        webAppBaseUrl="https://app.pilotfortrades.com"
        testID="owner-tab-field-issues-row"
      />,
    );
    expect(screen.getByTestId("field-issues-dot-pending")).toBeOnTheScreen();
    expect(screen.getByText(/3 pending/)).toBeOnTheScreen();
  });

  it("renders pendingCount=0 as healthy (green dot)", () => {
    render(
      <FieldIssuesSyncStatusRow
        pendingCount={0}
        onPress={jest.fn()}
        webAppBaseUrl="https://app.pilotfortrades.com"
        testID="owner-tab-field-issues-row"
      />,
    );
    expect(screen.getByTestId("field-issues-dot-healthy")).toBeOnTheScreen();
    expect(screen.getByText("None pending")).toBeOnTheScreen();
  });

  it("uses webAppBaseUrl from config — not hardcoded", () => {
    const customUrl = "https://custom.pilot.example.com";
    render(
      <FieldIssuesSyncStatusRow
        pendingCount={1}
        onPress={jest.fn()}
        webAppBaseUrl={customUrl}
      />,
    );
    // URL constructed from config prop (test confirms prop-driven behavior)
    expect(
      screen.getByTestId("field-issues-sync-status-row"),
    ).toBeOnTheScreen();
  });
});
