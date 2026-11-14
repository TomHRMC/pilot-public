/**
 * Ambient module declaration for react-native (web build stub)
 *
 * Location: apps/web/src/types/react-native.d.ts
 *
 * Next.js type-checks all workspace packages it imports, including
 * packages/ui which has 24+ files importing from "react-native".
 * This declaration satisfies tsc for the web Docker build.
 *
 * Components accept { [key: string]: unknown } so RN-style style objects
 * (with flexDirection: string, paddingVertical: number, etc.) don't conflict
 * with the stricter React.CSSProperties DOM types.
 *
 * Runtime stub: apps/web/src/lib/react-native-stub.js (no-ops)
 * Turbopack alias: next.config.ts resolveAlias["react-native"]
 */

declare module "react-native" {
  import type * as React from "react";

  // Permissive prop type — RN style objects are NOT DOM CSSProperties.
  // Using React.HTMLAttributes would enforce FlexDirection union on flexDirection,
  // but StyleSheet.create() returns { flexDirection: string }, causing type errors.
  type RNProps = { [key: string]: unknown };

  // ─── Components ─────────────────────────────────────────────────────────────
  export const View: React.ComponentType<RNProps>;
  export const Text: React.ComponentType<RNProps>;
  export const Pressable: React.ComponentType<RNProps>;
  export const TouchableOpacity: React.ComponentType<RNProps>;
  export const TouchableHighlight: React.ComponentType<RNProps>;
  export const ActivityIndicator: React.ComponentType<RNProps>;
  export const Image: React.ComponentType<RNProps>;
  export const ScrollView: React.ComponentType<RNProps>;
  export const FlatList: <T = unknown>(
    props: RNProps & {
      data?: readonly T[];
      renderItem?: (info: { item: T; index: number }) => React.ReactNode;
      keyExtractor?: (item: T, index: number) => string;
    },
  ) => React.ReactElement | null;
  export const TextInput: React.ComponentType<RNProps>;
  export const Modal: React.ComponentType<RNProps>;
  export const SafeAreaView: React.ComponentType<RNProps>;
  export const StatusBar: React.ComponentType<RNProps>;
  export const KeyboardAvoidingView: React.ComponentType<RNProps>;

  // ─── StyleSheet ─────────────────────────────────────────────────────────────
  export type ViewStyle = { [key: string]: unknown };
  export type TextStyle = { [key: string]: unknown };
  export type ImageStyle = { [key: string]: unknown };
  export type StyleProp<T> = T | readonly T[] | null | undefined;
  export const StyleSheet: {
    create<T extends Record<string, Record<string, unknown>>>(styles: T): T;
    flatten<T>(style: StyleProp<T>): T;
    hairlineWidth: number;
    absoluteFill: ViewStyle;
    absoluteFillObject: ViewStyle;
  };

  // ─── Platform ───────────────────────────────────────────────────────────────
  export const Platform: {
    OS: "web" | "ios" | "android" | "windows" | "macos";
    Version: number | string;
    select<T>(
      specifics: Partial<
        Record<
          | "web"
          | "ios"
          | "android"
          | "windows"
          | "macos"
          | "native"
          | "default",
          T
        >
      >,
    ): T;
    isPad?: boolean;
    isTV?: boolean;
  };

  // ─── Animated ───────────────────────────────────────────────────────────────
  export namespace Animated {
    class Value {
      constructor(value: number);
      setValue(value: number): void;
      interpolate(config: {
        inputRange: number[];
        outputRange: number[] | string[];
      }): Value;
    }
    const View: React.ComponentType<RNProps>;
    const Text: React.ComponentType<RNProps>;
    function timing(
      value: Value,
      config: Record<string, unknown>,
    ): { start(cb?: () => void): void };
    function spring(
      value: Value,
      config: Record<string, unknown>,
    ): { start(cb?: () => void): void };
    function createAnimatedComponent<T>(component: T): T;
    function parallel(animations: Array<{ start(cb?: () => void): void }>): {
      start(cb?: () => void): void;
    };
    function sequence(animations: Array<{ start(cb?: () => void): void }>): {
      start(cb?: () => void): void;
    };
    function loop(
      animation: { start(cb?: () => void): void },
      options?: Record<string, unknown>,
    ): { start(cb?: () => void): void };
  }

  // ─── Dimensions ─────────────────────────────────────────────────────────────
  export const Dimensions: {
    get(dim: "window" | "screen"): {
      width: number;
      height: number;
      scale: number;
      fontScale: number;
    };
    addEventListener(
      event: string,
      handler: (dims: {
        window: { width: number; height: number };
        screen: { width: number; height: number };
      }) => void,
    ): { remove(): void };
  };

  // ─── Linking ────────────────────────────────────────────────────────────────
  export const Linking: {
    openURL(url: string): Promise<void>;
    canOpenURL(url: string): Promise<boolean>;
    getInitialURL(): Promise<string | null>;
    addEventListener(
      event: string,
      handler: (event: { url: string }) => void,
    ): { remove(): void };
  };

  // ─── Misc ───────────────────────────────────────────────────────────────────
  export const NativeModules: Record<string, unknown>;
  export class NativeEventEmitter {
    constructor(nativeModule?: Record<string, unknown>);
    addListener(
      event: string,
      listener: (...args: unknown[]) => void,
    ): { remove(): void };
    removeAllListeners(event: string): void;
  }
  export const AccessibilityInfo: {
    announceForAccessibility(message: string): void;
    addEventListener(
      event: string,
      handler: (...args: unknown[]) => void,
    ): { remove(): void };
    isScreenReaderEnabled(): Promise<boolean>;
  };
  export const PermissionsAndroid: {
    request(permission: string): Promise<string>;
    check(permission: string): Promise<boolean>;
    PERMISSIONS: Record<string, string>;
    RESULTS: Record<string, string>;
  };
  export const Appearance: {
    getColorScheme(): "light" | "dark" | null;
    addChangeListener(
      handler: (preferences: { colorScheme: "light" | "dark" | null }) => void,
    ): { remove(): void };
  };
}
