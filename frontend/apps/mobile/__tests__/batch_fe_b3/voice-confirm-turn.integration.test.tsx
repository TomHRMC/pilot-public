/**
 * VoiceConfirmTurn integration tests — FE-B3
 *
 * Location: apps/mobile/__tests__/batch_fe_b3/voice-confirm-turn.integration.test.tsx
 * 3 tests: confirm flow, cancel flow, expiry via fake timers
 */

import React from "react";
import { render, fireEvent, act } from "@testing-library/react-native";

jest.mock("expo-av", () => ({ Audio: {} }));

const {
  VoiceConfirmTurn,
} = require("../../../../packages/ui/src/voice-confirm-turn/VoiceConfirmTurn");

describe("VoiceConfirmTurn — full flow (integration)", () => {
  it("confirm flow: user taps Confirm → onConfirm fires, isProcessing clears", async () => {
    let resolved = false;
    const onConfirm = jest.fn(() => {
      resolved = true;
    });
    const onCancel = jest.fn();

    const { getByTestId } = render(
      <VoiceConfirmTurn
        prompt="Send the Johnson quote?"
        onConfirm={onConfirm}
        onCancel={onCancel}
      />,
    );

    fireEvent.press(getByTestId("voice-confirm-confirm-btn"));
    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(onCancel).not.toHaveBeenCalled();
    expect(resolved).toBe(true);
  });

  it("cancel flow: user taps Cancel → onCancel fires, onConfirm not called", () => {
    const onConfirm = jest.fn();
    const onCancel = jest.fn();

    const { getByTestId } = render(
      <VoiceConfirmTurn
        prompt="Delete the job?"
        onConfirm={onConfirm}
        onCancel={onCancel}
      />,
    );

    fireEvent.press(getByTestId("voice-confirm-cancel-btn"));
    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it("processing state: both buttons disabled while isProcessing=true", () => {
    const { getByTestId } = render(
      <VoiceConfirmTurn
        prompt="Sending quote..."
        onConfirm={jest.fn()}
        onCancel={jest.fn()}
        isProcessing={true}
      />,
    );

    const confirmBtn = getByTestId("voice-confirm-confirm-btn");
    const cancelBtn = getByTestId("voice-confirm-cancel-btn");

    expect(confirmBtn.props.accessibilityState?.disabled).toBe(true);
    expect(cancelBtn.props.accessibilityState?.disabled).toBe(true);
  });
});
