/**
 * MyQuotesEntryRow unit tests (MOB-B1)
 *
 * Location: apps/mobile/features/jobs/components/__tests__/MyQuotesEntryRow.test.tsx
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react-native";
import { MyQuotesEntryRow } from "../MyQuotesEntryRow";

describe("MyQuotesEntryRow", () => {
  it("shows badge with count when pendingCount > 0", () => {
    render(<MyQuotesEntryRow pendingCount={3} onPress={() => {}} />);
    expect(screen.getByTestId("my-quotes-badge")).toBeTruthy();
    expect(screen.getByText("3")).toBeTruthy();
  });

  it("shows '99+' when pendingCount > 99", () => {
    render(<MyQuotesEntryRow pendingCount={150} onPress={() => {}} />);
    expect(screen.getByText("99+")).toBeTruthy();
  });

  it("shows 'All caught up' when pendingCount is 0", () => {
    render(<MyQuotesEntryRow pendingCount={0} onPress={() => {}} />);
    expect(screen.getByText("All caught up")).toBeTruthy();
    expect(screen.queryByTestId("my-quotes-badge")).toBeNull();
  });

  it("always shows the 'My Quotes' label", () => {
    render(<MyQuotesEntryRow pendingCount={0} onPress={() => {}} />);
    expect(screen.getByText("My Quotes")).toBeTruthy();
  });

  it("calls onPress when tapped", () => {
    const onPress = jest.fn();
    render(
      <MyQuotesEntryRow
        pendingCount={2}
        onPress={onPress}
        testID="my-quotes-entry-row"
      />,
    );
    fireEvent.press(screen.getByTestId("my-quotes-entry-row"));
    expect(onPress).toHaveBeenCalledTimes(1);
  });
});
