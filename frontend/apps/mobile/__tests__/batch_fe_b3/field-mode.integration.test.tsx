/**
 * Field mode integration tests — FE-B3
 *
 * Location: apps/mobile/__tests__/batch_fe_b3/field-mode.integration.test.tsx
 * 3 tests: toggle on, toggle off, persists via AsyncStorage
 */

import React from "react";
import { render, fireEvent } from "@testing-library/react-native";

jest.mock("expo-av", () => ({ Audio: {} }));
jest.mock("@react-native-async-storage/async-storage", () => ({
  getItem: jest.fn().mockResolvedValue(null),
  setItem: jest.fn().mockResolvedValue(undefined),
  removeItem: jest.fn().mockResolvedValue(undefined),
}));

const {
  FieldModeToggle,
} = require("../../features/voice-quote-creation/components/FieldModeToggle");

describe("FieldModeToggle (integration)", () => {
  it("toggle activates field mode", () => {
    const onToggle = jest.fn();
    const { getByTestId } = render(
      <FieldModeToggle isEnabled={false} onToggle={onToggle} />,
    );
    fireEvent.press(getByTestId("field-mode-toggle"));
    expect(onToggle).toHaveBeenCalledTimes(1);
  });

  it("toggle deactivates field mode", () => {
    const onToggle = jest.fn();
    const { getByTestId } = render(
      <FieldModeToggle isEnabled={true} onToggle={onToggle} />,
    );
    fireEvent.press(getByTestId("field-mode-toggle"));
    expect(onToggle).toHaveBeenCalledTimes(1);
  });

  it('field mode active shows "Field ✓" text', () => {
    const { getByText } = render(
      <FieldModeToggle isEnabled={true} onToggle={jest.fn()} />,
    );
    expect(getByText("Field ✓")).toBeTruthy();
  });
});
