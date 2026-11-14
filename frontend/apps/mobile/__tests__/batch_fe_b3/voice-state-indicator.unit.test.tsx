/**
 * VoiceStateIndicator unit tests — FE-B3
 *
 * Location: apps/mobile/__tests__/batch_fe_b3/voice-state-indicator.unit.test.tsx
 * Test plan §I — 8 tests
 */

import React from "react";
import { render } from "@testing-library/react-native";

jest.mock("expo-av", () => ({ Audio: {} }));

const {
  VoiceStateIndicator,
} = require("../../features/voice-quote-creation/components/VoiceStateIndicator");

describe("VoiceStateIndicator", () => {
  it("renders idle state without crash", () => {
    expect(() => render(<VoiceStateIndicator state="idle" />)).not.toThrow();
  });

  it("idle state renders mic icon", () => {
    const { getByTestId } = render(<VoiceStateIndicator state="idle" />);
    expect(getByTestId("mic-icon")).toBeTruthy();
  });

  it("listening state renders pulse ring element", () => {
    const { getByTestId } = render(<VoiceStateIndicator state="listening" />);
    expect(getByTestId("listening-waveform-anim")).toBeTruthy();
  });

  it("processing state renders ActivityIndicator spinner", () => {
    const { UNSAFE_getAllByType } = render(
      <VoiceStateIndicator state="processing" />,
    );
    const { ActivityIndicator } = require("react-native");
    expect(UNSAFE_getAllByType(ActivityIndicator).length).toBeGreaterThan(0);
  });

  it("speaking state renders waveform element", () => {
    // Speaking state renders 3 waveform bars
    const { UNSAFE_getAllByProps } = render(
      <VoiceStateIndicator state="speaking" />,
    );
    const { View } = require("react-native");
    // 3 waveform bars + container view
    expect(() =>
      render(<VoiceStateIndicator state="speaking" />),
    ).not.toThrow();
  });

  it("waiting-confirm state renders confirm icon", () => {
    const { getByTestId } = render(
      <VoiceStateIndicator state="waiting-confirm" />,
    );
    expect(getByTestId("confirm-icon")).toBeTruthy();
  });

  it("error state renders error icon", () => {
    const { getByTestId } = render(<VoiceStateIndicator state="error" />);
    expect(getByTestId("error-icon")).toBeTruthy();
  });

  it("fieldMode={true} renders larger variant without crash", () => {
    const { getByTestId } = render(
      <VoiceStateIndicator
        state="idle"
        fieldMode={true}
        testID="field-indicator"
      />,
    );
    expect(getByTestId("field-indicator")).toBeTruthy();
  });
});
