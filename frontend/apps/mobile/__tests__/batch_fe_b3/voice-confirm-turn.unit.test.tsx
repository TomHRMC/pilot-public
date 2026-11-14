/**
 * VoiceConfirmTurn component unit tests — FE-B3
 *
 * Location: apps/mobile/__tests__/batch_fe_b3/voice-confirm-turn.unit.test.tsx
 * Test plan §I — 8 tests
 */

import React from "react";
import { render, fireEvent } from "@testing-library/react-native";

jest.mock("expo-av", () => ({ Audio: {} }));

const {
  VoiceConfirmTurn,
} = require("../../../../packages/ui/src/voice-confirm-turn/VoiceConfirmTurn");

describe("VoiceConfirmTurn", () => {
  const defaultProps = {
    prompt: "Send the Johnson panel quote to tom@johnson.example.com?",
    onConfirm: jest.fn(),
    onCancel: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders prompt text", () => {
    const { getByText } = render(<VoiceConfirmTurn {...defaultProps} />);
    expect(
      getByText("Send the Johnson panel quote to tom@johnson.example.com?"),
    ).toBeTruthy();
  });

  it('"Confirm" button calls onConfirm', () => {
    const onConfirm = jest.fn();
    const { getByTestId } = render(
      <VoiceConfirmTurn {...defaultProps} onConfirm={onConfirm} />,
    );
    fireEvent.press(getByTestId("voice-confirm-confirm-btn"));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it('"Cancel" button calls onCancel', () => {
    const onCancel = jest.fn();
    const { getByTestId } = render(
      <VoiceConfirmTurn {...defaultProps} onCancel={onCancel} />,
    );
    fireEvent.press(getByTestId("voice-confirm-cancel-btn"));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it("both buttons are disabled when isProcessing={true}", () => {
    const { getByTestId } = render(
      <VoiceConfirmTurn {...defaultProps} isProcessing={true} />,
    );
    const confirmBtn = getByTestId("voice-confirm-confirm-btn");
    const cancelBtn = getByTestId("voice-confirm-cancel-btn");
    // accessibilityState.disabled should be true
    expect(confirmBtn.props.accessibilityState?.disabled).toBe(true);
    expect(cancelBtn.props.accessibilityState?.disabled).toBe(true);
  });

  it("has correct accessibility labels on both buttons", () => {
    const { getByLabelText } = render(<VoiceConfirmTurn {...defaultProps} />);
    expect(getByLabelText("Confirm voice action")).toBeTruthy();
    expect(getByLabelText("Cancel voice action")).toBeTruthy();
  });

  it("testID is applied to container", () => {
    const { getByTestId } = render(
      <VoiceConfirmTurn {...defaultProps} testID="my-confirm-turn" />,
    );
    expect(getByTestId("my-confirm-turn")).toBeTruthy();
  });

  it("does not call onConfirm when cancelled before processing", () => {
    const onConfirm = jest.fn();
    const onCancel = jest.fn();
    const { getByTestId } = render(
      <VoiceConfirmTurn
        onConfirm={onConfirm}
        onCancel={onCancel}
        prompt="test"
      />,
    );
    fireEvent.press(getByTestId("voice-confirm-cancel-btn"));
    expect(onConfirm).not.toHaveBeenCalled();
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it("shows ActivityIndicator spinner when isProcessing={true}", () => {
    const { UNSAFE_getAllByType } = render(
      <VoiceConfirmTurn {...defaultProps} isProcessing={true} />,
    );
    const { ActivityIndicator } = require("react-native");
    expect(UNSAFE_getAllByType(ActivityIndicator).length).toBeGreaterThan(0);
  });
});
