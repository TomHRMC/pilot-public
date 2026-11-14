/**
 * Disambiguation integration tests — FE-B3
 *
 * Location: apps/mobile/__tests__/batch_fe_b3/disambiguation.integration.test.tsx
 * 3 tests: multiple matches, user selects, zero matches
 */

import React from "react";
import { render, fireEvent } from "@testing-library/react-native";

jest.mock("expo-av", () => ({ Audio: {} }));

const {
  DisambiguationList,
} = require("../../features/voice-quote-creation/components/DisambiguationList");

const mockOptions = [
  { id: "c-001", label: "Tom Johnson", sublabel: "42 Oak Street, Springfield" },
  { id: "c-002", label: "Tom Johnson", sublabel: "18 Maple Ave, Riverside" },
];

describe("DisambiguationList (integration)", () => {
  it("multiple customers match → renders all options", () => {
    const { getByTestId } = render(
      <DisambiguationList options={mockOptions} onSelect={jest.fn()} />,
    );
    expect(getByTestId("disambiguation-option-c-001")).toBeTruthy();
    expect(getByTestId("disambiguation-option-c-002")).toBeTruthy();
  });

  it("user selects option → onSelect called with correct option", () => {
    const onSelect = jest.fn();
    const { getByTestId } = render(
      <DisambiguationList options={mockOptions} onSelect={onSelect} />,
    );
    fireEvent.press(getByTestId("disambiguation-option-c-001"));
    expect(onSelect).toHaveBeenCalledWith(mockOptions[0]);
  });

  it('zero matches → shows "No matching customer found" error banner', () => {
    const { getByText } = render(
      <DisambiguationList options={[]} onSelect={jest.fn()} />,
    );
    expect(getByText("No matching customer found")).toBeTruthy();
  });
});
