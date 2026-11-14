/**
 * Jest setup file — global mocks for native modules
 *
 * Location: apps/mobile/jest.setup.ts
 *
 * MOB-B6: Added global mocks for expo-location and expo-image-picker.
 * These native modules require `createPermissionHook` which is unavailable
 * in the jsdom/react-native test environment. All tests importing any
 * component that transitively uses these modules need this mock.
 *
 * SDK alignment: @react-native-async-storage/async-storage was downgraded
 * from v3.x → v2.2.0 (Expo SDK 54 compatible).  v2.x requires an explicit
 * Jest mock because it no longer auto-mocks NativeModule resolution.
 * The official mock is at @react-native-async-storage/async-storage/jest/async-storage-mock.
 */

// ── AsyncStorage (v2.2.0 requires explicit mock) ──────────────────────────────
jest.mock("@react-native-async-storage/async-storage", () =>
  require("@react-native-async-storage/async-storage/jest/async-storage-mock"),
);

// ── expo-location ─────────────────────────────────────────────────────────────

jest.mock("expo-location", () => ({
  requestForegroundPermissionsAsync: jest
    .fn()
    .mockResolvedValue({ status: "granted" }),
  getCurrentPositionAsync: jest.fn().mockResolvedValue({
    coords: { latitude: 37.7749, longitude: -122.4194, accuracy: 10 },
  }),
  Accuracy: { High: 5, Balanced: 3, Low: 1 },
}));

// ── expo-image-picker ─────────────────────────────────────────────────────────

jest.mock("expo-image-picker", () => ({
  requestCameraPermissionsAsync: jest
    .fn()
    .mockResolvedValue({ status: "granted" }),
  requestMediaLibraryPermissionsAsync: jest
    .fn()
    .mockResolvedValue({ status: "granted" }),
  launchCameraAsync: jest.fn().mockResolvedValue({
    canceled: false,
    assets: [
      {
        uri: "file://test-camera-photo.jpg",
        mimeType: "image/jpeg",
        fileSize: 102400,
      },
    ],
  }),
  launchImageLibraryAsync: jest.fn().mockResolvedValue({
    canceled: false,
    assets: [
      {
        uri: "file://test-library-photo.jpg",
        mimeType: "image/jpeg",
        fileSize: 204800,
      },
    ],
  }),
  MediaTypeOptions: { Images: "images" },
}));

// ── expo-haptics (MFA-WIRE-1 Part C — wizard haptic feedback) ─────────────────

jest.mock("expo-haptics", () => ({
  notificationAsync: jest.fn().mockResolvedValue(undefined),
  NotificationFeedbackType: {
    Success: "success",
    Warning: "warning",
    Error: "error",
  },
  ImpactFeedbackStyle: {
    Light: "light",
    Medium: "medium",
    Heavy: "heavy",
  },
  impactAsync: jest.fn().mockResolvedValue(undefined),
  selectionAsync: jest.fn().mockResolvedValue(undefined),
}));

// ── expo-clipboard (MFA-WIRE-1 Part C — copy affordances; Rule 9.8 approved) ──

jest.mock("expo-clipboard", () => ({
  setStringAsync: jest.fn().mockResolvedValue(true),
  getStringAsync: jest.fn().mockResolvedValue(""),
  setString: jest.fn(),
}));
