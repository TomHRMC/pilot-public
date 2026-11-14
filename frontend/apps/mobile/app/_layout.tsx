// ── Polyfills — MUST be the very first imports ──────────────────────────────
//
// 1. react-native-get-random-values: polyfills crypto.getRandomValues() for
//    React Native.  AWS Amplify v6's SRP authentication calls this function
//    during sign-in.  Without it, Amplify throws:
//      "An unknown error has occurred." (assertServiceError from signInWithSRP)
//    This import MUST come before aws-amplify or amplify-config.
// 2. amplify-config: configures the Cognito User Pool connection on native.
//    On web: skipped (MSW intercepts all API calls, no real Cognito needed).
// 3. backgroundSync: MUST be imported before BackgroundFetch.registerTaskAsync
//    so TaskManager.defineTask is registered before the OS invokes the task.
import "react-native-get-random-values";
import "../lib/amplify-config";
// backgroundSync import below (named + side-effect) — do NOT add a separate side-effect import

import {
  DarkTheme,
  DefaultTheme,
  ThemeProvider,
} from "@react-navigation/native";
import { Stack, useRouter, useSegments } from "expo-router";
import { StatusBar } from "expo-status-bar";
import "react-native-reanimated";
import { QueryClientProvider } from "@tanstack/react-query";
import { GluestackUIProvider } from "@gluestack-ui/themed";
import { useEffect } from "react";
import { Platform } from "react-native";
import * as BackgroundFetch from "expo-background-fetch";
import * as TaskManager from "expo-task-manager";

import { useColorScheme } from "@/hooks/use-color-scheme";
import { pilotConfig } from "@/theme/gluestack-config";
import { createQueryClient } from "@pilot/shared-api";
import { AuthProvider, useAuth } from "@pilot/ui/auth";
import { NotificationQueueProvider } from "@pilot/ui/notification-banner";
import { usePushTokenRegistration } from "../hooks/usePushTokenRegistration";
import { BACKGROUND_SYNC_TASK_NAME } from "../lib/backgroundSync";

// ─── MSW Browser Service Worker (web + mock auth only) ────────────────────────
//
// When EXPO_PUBLIC_USE_MOCK_AUTH=true and running on web (localhost:8081),
// we start the MSW service worker so all Axios API calls are intercepted
// by the shared mock handlers in mocks/handlers/.  This means the web view
// shows real-looking data without a running FastAPI backend or Cognito session.
//
// Two guards are required:
//   1. Platform.OS === "web" — prevents this code from running on native.
//   2. typeof window !== "undefined" — prevents execution during Metro's Node.js
//      SSR pass (node/render.js).  Without this guard, setupWorker() throws:
//      "[MSW] Failed to execute `setupWorker` in a non-browser environment"
//
// startMockServiceWorker() is a lazy async function — it calls setupWorker()
// only when invoked, never at module evaluation time, avoiding the SSR crash.
if (
  Platform.OS === "web" &&
  typeof window !== "undefined" &&
  process.env.EXPO_PUBLIC_USE_MOCK_AUTH === "true"
) {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { startMockServiceWorker } = require("../mocks/browser") as {
    startMockServiceWorker: (opts?: Record<string, unknown>) => Promise<void>;
  };
  startMockServiceWorker({
    // Bypass unhandled requests — lets hot-reload WebSocket and other dev-server
    // traffic pass through without MSW warnings.
    onUnhandledRequest: "bypass",
  })
    .then(() => {
      if (__DEV__) {
        console.log("[MSW] Browser service worker started (mock auth mode)");
      }
    })
    .catch((err: Error) => {
      console.warn("[MSW] Service worker failed to start:", err.message);
    });
}

// Stable QueryClient instance — created once per app session
const queryClient = createQueryClient();

export const unstable_settings = {
  anchor: "(tabs)",
};

/**
 * AuthGuard — redirects unauthenticated users to (auth)/login.
 * Called inside providers so useAuth() has context.
 * FE-B2: design doc §C mobile auth guard
 */
function AuthGuard() {
  const { isAuthenticated } = useAuth();
  const router = useRouter();
  const segments = useSegments();

  useEffect(() => {
    const inAuthGroup = segments[0] === "(auth)";

    if (!isAuthenticated && !inAuthGroup) {
      // Unauthenticated: redirect to login
      router.replace("/(auth)/login");
    }
  }, [isAuthenticated, router, segments]);

  return null;
}

export default function RootLayout() {
  const colorScheme = useColorScheme();

  // MOB-B8: Register Expo push token with backend on every app open (upsert)
  usePushTokenRegistration();

  // MOB-B8: Register BGAppRefreshTask (iOS) + WorkManager (Android)
  // Only on native — web does not support BackgroundFetch
  useEffect(() => {
    if (Platform.OS === "web") return;

    const registerBackgroundSync = async () => {
      try {
        const isRegistered = await TaskManager.isTaskRegisteredAsync(
          BACKGROUND_SYNC_TASK_NAME,
        );
        if (!isRegistered) {
          await BackgroundFetch.registerTaskAsync(BACKGROUND_SYNC_TASK_NAME, {
            minimumInterval: 15 * 60, // 15 minutes minimum (OS enforces regardless)
            stopOnTerminate: false, // continue after app is terminated (Android)
            startOnBoot: true, // register on device boot (Android)
          });
        }
      } catch (err) {
        // Silent failure — background sync is enhancement, not critical path
        console.warn("[BackgroundSync] registration failed:", err);
      }
    };

    registerBackgroundSync();
  }, []); // runs once on mount

  return (
    <QueryClientProvider client={queryClient}>
      <NotificationQueueProvider>
        <AuthProvider
          mockUser={
            // Only inject mock user on web (localhost:8081 dev view).
            // Native (Expo Go / device) uses real Cognito authentication
            // even when EXPO_PUBLIC_USE_MOCK_AUTH=true so the app can hit
            // the real FastAPI backend with a valid JWT.
            Platform.OS === "web" &&
            process.env.EXPO_PUBLIC_USE_MOCK_AUTH === "true"
              ? {
                  role:
                    (process.env.EXPO_PUBLIC_MOCK_USER_ROLE as
                      | "owner"
                      | "technician") ?? "technician",
                  email: "mockuser@pilot-dev.example.com",
                  displayName: "Mock User",
                }
              : undefined
          }
        >
          <GluestackUIProvider
            config={pilotConfig}
            colorMode={colorScheme === "dark" ? "dark" : "light"}
          >
            <ThemeProvider
              value={colorScheme === "dark" ? DarkTheme : DefaultTheme}
            >
              {/* Auth guard — redirects unauthenticated users to login */}
              <AuthGuard />
              <Stack>
                <Stack.Screen name="(auth)" options={{ headerShown: false }} />
                <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
                <Stack.Screen
                  name="modal"
                  options={{ presentation: "modal", title: "Modal" }}
                />
              </Stack>
              <StatusBar style="auto" />
            </ThemeProvider>
          </GluestackUIProvider>
        </AuthProvider>
      </NotificationQueueProvider>
    </QueryClientProvider>
  );
}
