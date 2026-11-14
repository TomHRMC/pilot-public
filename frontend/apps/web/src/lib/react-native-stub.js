/**
 * React Native stub for Next.js web build and Vitest
 *
 * Location: apps/web/src/lib/react-native-stub.js
 *
 * Stubs out ALL React Native + Expo mobile-only exports so the web
 * build doesn't fail when packages/ui barrel imports mobile components.
 *
 * Exports every named export that VoiceConfirmTurn, expo-av, expo-asset,
 * expo-modules-core, etc. might use. All are no-ops.
 */

const noop = () => null;
const noopClass = class {};

// Core React Native components
export const View = noop;
export const Text = noop;
export const Pressable = noop;
export const TouchableOpacity = noop;
export const TouchableHighlight = noop;
export const ActivityIndicator = noop;
export const Image = noop;
export const ScrollView = noop;
export const FlatList = noop;
export const TextInput = noop;
export const Modal = noop;
export const SafeAreaView = noop;
export const StatusBar = noop;
export const KeyboardAvoidingView = noop;
export const Animated = {
  View: noop,
  Text: noop,
  Value: noopClass,
  timing: () => ({ start: noop }),
  spring: () => ({ start: noop }),
  createAnimatedComponent: (c) => c,
};
export const StyleSheet = { create: (s) => s, flatten: (s) => s };
export const Platform = {
  OS: "web",
  select: (obj) => obj.web ?? obj.default,
  Version: 0,
};
export const Dimensions = { get: () => ({ width: 375, height: 812 }) };
export const Linking = {
  openURL: () => Promise.resolve(),
  canOpenURL: () => Promise.resolve(true),
  getInitialURL: () => Promise.resolve(null),
  addEventListener: () => ({ remove: noop }),
};
export const NativeModules = {};
export const NativeEventEmitter = noopClass;
export const AccessibilityInfo = {
  announceForAccessibility: noop,
  addEventListener: () => ({ remove: noop }),
  isScreenReaderEnabled: () => Promise.resolve(false),
};
export const PermissionsAndroid = {
  request: () => Promise.resolve("granted"),
  check: () => Promise.resolve(true),
  PERMISSIONS: {},
  RESULTS: { GRANTED: "granted" },
};

// Async storage stub
export const AsyncStorage = {
  getItem: () => Promise.resolve(null),
  setItem: () => Promise.resolve(),
  removeItem: () => Promise.resolve(),
  multiGet: () => Promise.resolve([]),
  multiSet: () => Promise.resolve(),
  clear: () => Promise.resolve(),
};

// Appearance
export const Appearance = {
  getColorScheme: () => "light",
  addChangeListener: noop,
};

// eslint-disable-next-line import/no-anonymous-default-export
export default {
  View,
  Text,
  Pressable,
  ActivityIndicator,
  StyleSheet,
  Platform,
  NativeModules,
  AccessibilityInfo,
  Linking,
};
