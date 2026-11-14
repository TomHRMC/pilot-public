/**
 * PhotoSection unit tests — MOB-B6 (photo picker enabled)
 *
 * Location: apps/mobile/features/jobs/components/detail/__tests__/PhotoSection.mob-b6.test.tsx
 *
 * Tests that + Add Photo is enabled, shows permission requests, and
 * creates a WatermelonDB record on successful pick.
 */

import React from "react";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  act,
} from "@testing-library/react-native";
import { Alert, Platform } from "react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { PhotoSection } from "../PhotoSection";

// ── Set Platform to android before tests run ──────────────────────────────────

beforeAll(() => {
  Object.defineProperty(Platform, "OS", { value: "android", writable: true });
});

// ── Mock expo-image-picker ────────────────────────────────────────────────────

const mockRequestCameraPermissionsAsync = jest
  .fn()
  .mockResolvedValue({ status: "granted" });
const mockRequestMediaLibraryPermissionsAsync = jest
  .fn()
  .mockResolvedValue({ status: "granted" });
const mockLaunchCameraAsync = jest.fn().mockResolvedValue({
  canceled: false,
  assets: [
    {
      uri: "file://test-camera-photo.jpg",
      mimeType: "image/jpeg",
      fileSize: 102400,
    },
  ],
});
const mockLaunchImageLibraryAsync = jest.fn().mockResolvedValue({
  canceled: false,
  assets: [
    {
      uri: "file://test-library-photo.jpg",
      mimeType: "image/jpeg",
      fileSize: 204800,
    },
  ],
});

jest.mock("expo-image-picker", () => ({
  requestCameraPermissionsAsync: () => mockRequestCameraPermissionsAsync(),
  requestMediaLibraryPermissionsAsync: () =>
    mockRequestMediaLibraryPermissionsAsync(),
  launchCameraAsync: () => mockLaunchCameraAsync(),
  launchImageLibraryAsync: () => mockLaunchImageLibraryAsync(),
  MediaTypeOptions: { Images: "images" },
}));

// ── Mock expo-location (not used by PhotoSection, but prevents transitive crash) ───

jest.mock("expo-location", () => ({
  requestForegroundPermissionsAsync: jest
    .fn()
    .mockResolvedValue({ status: "granted" }),
  getCurrentPositionAsync: jest.fn().mockResolvedValue({
    coords: { latitude: 37.7749, longitude: -122.4194, accuracy: 10 },
  }),
  Accuracy: { High: 5 },
}));

// ── Mock useCreatePhoto ───────────────────────────────────────────────────────

const mockCreatePhoto = jest.fn().mockResolvedValue({
  id: "mock-photo-id",
  localUri: "file://test-photo.jpg",
  uploadProgress: 0,
  localSyncStatus: "pending",
});

jest.mock("../../../../offline-sync/hooks/useCreatePhoto", () => ({
  useCreatePhoto: () => ({
    create: mockCreatePhoto,
    isPending: false,
    error: null,
  }),
}));

// ── Mock WatermelonDB ─────────────────────────────────────────────────────────

jest.mock("../../../../../database", () => ({
  database: {
    write: jest
      .fn()
      .mockImplementation(async (fn: () => Promise<unknown>) => fn()),
    get: jest.fn().mockReturnValue({
      query: jest.fn().mockReturnValue({
        fetch: jest.fn().mockResolvedValue([]),
      }),
      create: jest.fn(),
    }),
  },
}));

// ── Helpers ───────────────────────────────────────────────────────────────────

const JOB_ID = "job-photo-test-001";

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return React.createElement(QueryClientProvider, { client: qc }, children);
}

beforeEach(() => {
  jest.clearAllMocks();
  mockCreatePhoto.mockResolvedValue({
    id: "mock-photo-id",
    localUri: "file://test-photo.jpg",
    uploadProgress: 0,
    localSyncStatus: "pending",
  });
});

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("PhotoSection — MOB-B6 photo picker", () => {
  it("renders + Add button (enabled, not disabled)", () => {
    render(<PhotoSection jobId={JOB_ID} />, { wrapper });
    const addBtn = screen.getByTestId("add-photo-button");
    expect(addBtn).toBeOnTheScreen();
    // No disabled accessibilityState set (button is enabled)
    expect(addBtn.props.accessibilityState?.disabled).not.toBe(true);
  });

  it("pressing + Add shows action options (Android Alert)", async () => {
    const alertSpy = jest.spyOn(Alert, "alert");

    render(<PhotoSection jobId={JOB_ID} />, { wrapper });

    await act(async () => {
      fireEvent.press(screen.getByTestId("add-photo-button"));
    });

    expect(alertSpy).toHaveBeenCalledWith(
      "Add Photo",
      "Choose a source",
      expect.any(Array),
    );
  });

  it("after library pick: createPhoto called with correct URI", async () => {
    jest.spyOn(Alert, "alert").mockImplementation((...args) => {
      const buttons = args[2] as {
        text: string;
        onPress?: () => void;
      }[];
      const libraryBtn = buttons?.find((b) => b.text === "Choose from Library");
      libraryBtn?.onPress?.();
    });

    render(<PhotoSection jobId={JOB_ID} />, { wrapper });

    await act(async () => {
      fireEvent.press(screen.getByTestId("add-photo-button"));
    });

    await waitFor(() => {
      expect(mockCreatePhoto).toHaveBeenCalledWith(
        expect.objectContaining({
          jobId: JOB_ID,
          localUri: "file://test-library-photo.jpg",
        }),
      );
    });
  });

  it("shows empty state when no photos", () => {
    render(<PhotoSection jobId={JOB_ID} />, { wrapper });
    expect(screen.getByText("No photos captured")).toBeOnTheScreen();
  });

  it("does NOT create photo record when picker is cancelled", async () => {
    mockLaunchImageLibraryAsync.mockResolvedValueOnce({
      canceled: true,
      assets: [],
    });

    jest.spyOn(Alert, "alert").mockImplementation((...args) => {
      const buttons = args[2] as {
        text: string;
        onPress?: () => void;
      }[];
      const libraryBtn = buttons?.find((b) => b.text === "Choose from Library");
      libraryBtn?.onPress?.();
    });

    render(<PhotoSection jobId={JOB_ID} />, { wrapper });

    await act(async () => {
      fireEvent.press(screen.getByTestId("add-photo-button"));
    });

    await waitFor(() => {
      expect(mockCreatePhoto).not.toHaveBeenCalled();
    });
  });
});
