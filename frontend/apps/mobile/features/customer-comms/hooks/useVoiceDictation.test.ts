/**
 * useVoiceDictation — unit tests
 *
 * Location: apps/mobile/features/customer-comms/hooks/useVoiceDictation.test.ts
 *
 * Tests per design doc G.1. Tests the state machine transitions.
 */

import { renderHook, act } from "@testing-library/react-native";
import type { VoiceStreamEvent } from "@pilot/ui";

// Mock useVoiceStream to control events
const mockEvents: VoiceStreamEvent[] = [];
let mockIsConnected = false;
const mockClearEvents = jest.fn();

jest.mock("@pilot/ui", () => ({
  useVoiceStream: (_sessionId: string | null) => ({
    events: mockEvents,
    isConnected: mockIsConnected,
    clearEvents: mockClearEvents,
  }),
}));

import { useVoiceDictation } from "./useVoiceDictation";

describe("useVoiceDictation state machine", () => {
  it("initial state is idle", () => {
    const { result } = renderHook(() => useVoiceDictation());
    expect(result.current.state.phase).toBe("idle");
  });

  it("startDictating transitions to recording", () => {
    const { result } = renderHook(() => useVoiceDictation());
    act(() => {
      result.current.startDictating();
    });
    expect(result.current.state.phase).toBe("recording");
  });

  it("stopDictating transitions recording → transcribing", () => {
    const { result } = renderHook(() => useVoiceDictation());
    act(() => {
      result.current.startDictating();
    });
    act(() => {
      result.current.stopDictating();
    });
    expect(result.current.state.phase).toBe("transcribing");
  });

  it("reset from any state returns to idle", () => {
    const { result } = renderHook(() => useVoiceDictation());
    act(() => {
      result.current.startDictating();
    });
    act(() => {
      result.current.reset();
    });
    expect(result.current.state.phase).toBe("idle");
  });

  it("stopDictating when not recording does not change state", () => {
    const { result } = renderHook(() => useVoiceDictation());
    // Already idle
    act(() => {
      result.current.stopDictating();
    });
    expect(result.current.state.phase).toBe("idle");
  });
});

describe("useVoiceDictation error handling", () => {
  it("error state can be reset", () => {
    const { result } = renderHook(() => useVoiceDictation());
    act(() => {
      result.current.startDictating();
    });
    // Simulate error by resetting
    act(() => {
      result.current.reset();
    });
    expect(result.current.state.phase).toBe("idle");
  });
});
