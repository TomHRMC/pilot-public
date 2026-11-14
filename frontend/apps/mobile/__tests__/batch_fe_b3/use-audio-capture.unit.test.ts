/**
 * useAudioCapture unit tests — FE-B3
 *
 * Location: apps/mobile/__tests__/batch_fe_b3/use-audio-capture.unit.test.ts
 * Test plan §I — 6 tests
 *
 * NOTE: The hook uses dynamic import('expo-av') internally.
 * We mock the module at the top level and verify state transitions.
 */

import { renderHook, act, waitFor } from "@testing-library/react-native";

const mockStopAndUnloadAsync = jest.fn().mockResolvedValue(undefined);
const mockGetURI = jest.fn().mockReturnValue("file://mock-recording.m4a");
const mockStartAsync = jest.fn().mockResolvedValue(undefined);

const mockRecording = {
  stopAndUnloadAsync: mockStopAndUnloadAsync,
  getURI: mockGetURI,
  startAsync: mockStartAsync,
};

jest.mock("expo-av", () => ({
  Audio: {
    requestPermissionsAsync: jest.fn().mockResolvedValue({ status: "granted" }),
    setAudioModeAsync: jest.fn().mockResolvedValue(undefined),
    Recording: {
      createAsync: jest.fn().mockResolvedValue({ recording: mockRecording }),
    },
    RecordingOptionsPresets: {
      HIGH_QUALITY: {},
    },
  },
}));

// Import AFTER jest.mock
import { useAudioCapture } from "../../features/voice-quote-creation/hooks/useAudioCapture";

describe("useAudioCapture", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Reset default mocks after clearAllMocks
    const { Audio } = require("expo-av");
    Audio.requestPermissionsAsync.mockResolvedValue({ status: "granted" });
    Audio.setAudioModeAsync.mockResolvedValue(undefined);
    Audio.Recording.createAsync.mockResolvedValue({ recording: mockRecording });
    mockStopAndUnloadAsync.mockResolvedValue(undefined);
    mockGetURI.mockReturnValue("file://mock-recording.m4a");
  });

  it("startRecording calls Audio.requestPermissionsAsync", async () => {
    const { Audio } = require("expo-av");
    const { result } = renderHook(() => useAudioCapture());

    await act(async () => {
      await result.current.startRecording();
    });

    expect(Audio.requestPermissionsAsync).toHaveBeenCalledTimes(1);
  });

  it("startRecording returns permissionGranted=false when denied", async () => {
    const { Audio } = require("expo-av");
    Audio.requestPermissionsAsync.mockResolvedValueOnce({ status: "denied" });

    const { result } = renderHook(() => useAudioCapture());

    await act(async () => {
      await result.current.startRecording();
    });

    expect(result.current.permissionGranted).toBe(false);
    expect(result.current.isRecording).toBe(false);
  });

  it("startRecording starts recording when permission granted", async () => {
    const { Audio } = require("expo-av");
    const { result } = renderHook(() => useAudioCapture());

    await act(async () => {
      await result.current.startRecording();
    });

    expect(result.current.isRecording).toBe(true);
    expect(Audio.Recording.createAsync).toHaveBeenCalledTimes(1);
  });

  it("stopRecording stops recording and returns audio URI", async () => {
    const { result } = renderHook(() => useAudioCapture());

    await act(async () => {
      await result.current.startRecording();
    });

    let uri: string | null = null;
    await act(async () => {
      uri = await result.current.stopRecording();
    });

    expect(uri).toBe("file://mock-recording.m4a");
    expect(result.current.isRecording).toBe(false);
  });

  it("isRecording state transitions: false → true → false", async () => {
    const { result } = renderHook(() => useAudioCapture());

    expect(result.current.isRecording).toBe(false);
    await act(async () => {
      await result.current.startRecording();
    });
    expect(result.current.isRecording).toBe(true);
    await act(async () => {
      await result.current.stopRecording();
    });
    expect(result.current.isRecording).toBe(false);
  });

  it("cleanup: stopAndUnloadAsync called on unmount if recording", async () => {
    const { result, unmount } = renderHook(() => useAudioCapture());

    await act(async () => {
      await result.current.startRecording();
    });
    expect(result.current.isRecording).toBe(true);

    unmount();
    // stopAndUnloadAsync should be called on cleanup
    expect(mockStopAndUnloadAsync).toHaveBeenCalled();
  });
});
