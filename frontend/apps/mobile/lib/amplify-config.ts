/**
 * amplify-config.ts — Configures AWS Amplify for the mobile app
 *
 * Location: apps/mobile/lib/amplify-config.ts
 *
 * This file MUST be imported before any aws-amplify/auth usage.
 * Import it as the FIRST import in app/_layout.tsx so it runs before
 * AuthProvider's useEffect calls fetch fetchAuthSession().
 *
 * Cognito config (see dev-docs/devops/aws-cognito-setup.md):
 *   User Pool:  us-east-1_XXXXXXXXX
 *   App Client: xxxxxxxxxxxxxxxxxxxxxxxxxx (SPA type — no client secret)
 *   Region:     us-east-1
 *
 * Amplify configuration matrix:
 * ┌──────────────────────────────┬────────────────────────────────────────┐
 * │ Environment                  │ Amplify behaviour                      │
 * ├──────────────────────────────┼────────────────────────────────────────┤
 * │ Native (iOS/Android)         │ Always configured — AsyncStorage used  │
 * │ Web, MOCK_AUTH=true          │ Skipped — MSW intercepts all API calls │
 * │ Web, MOCK_AUTH=false         │ Configured — real Cognito on web       │
 * └──────────────────────────────┴────────────────────────────────────────┘
 *
 * Rule 21: EXPO_PUBLIC_USE_MOCK_AUTH is only honoured on web.
 * Rule 22: Only EXPO_PUBLIC_ vars are injected by Metro.
 * Rule 23: AsyncStorage backend required on native for token persistence.
 */

import { Amplify } from "aws-amplify";
import { Platform } from "react-native";

const userPoolId = process.env.EXPO_PUBLIC_COGNITO_USER_POOL_ID ?? "";
const userPoolClientId = process.env.EXPO_PUBLIC_COGNITO_APP_CLIENT_ID ?? "";

// On web, EXPO_PUBLIC_USE_MOCK_AUTH=true bypasses Cognito entirely.
// On native, this flag is always treated as false (real Cognito required).
const isMockAuth =
  Platform.OS === "web" && process.env.EXPO_PUBLIC_USE_MOCK_AUTH === "true";

if (!isMockAuth && userPoolId && userPoolClientId) {
  if (Platform.OS !== "web") {
    // ── Native (iOS / Android) ──────────────────────────────────────────────
    // AsyncStorage must be used as Amplify's token storage backend on React
    // Native. Without it, tokens live in memory only — fetchAuthSession()
    // returns empty tokens after the initial signIn, causing 401s on all
    // subsequent API requests.
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const AsyncStorage =
      require("@react-native-async-storage/async-storage").default;

    Amplify.configure(
      {
        Auth: {
          Cognito: {
            userPoolId,
            userPoolClientId,
            loginWith: {
              email: true,
            },
          },
        },
      },
      {
        Storage: AsyncStorage,
      },
    );
  } else {
    // ── Web with real Cognito (EXPO_PUBLIC_USE_MOCK_AUTH=false) ─────────────
    // Browser-based local storage is used by default — no explicit Storage
    // option required. Amplify must still be configured so that signIn /
    // fetchAuthSession / signOut calls succeed.
    Amplify.configure({
      Auth: {
        Cognito: {
          userPoolId,
          userPoolClientId,
          loginWith: {
            email: true,
          },
        },
      },
    });
  }

  if (process.env.NODE_ENV !== "production") {
    console.log(
      `[Amplify] Configured — pool: ${userPoolId}, client: ${userPoolClientId.slice(0, 6)}… (platform: ${Platform.OS})`,
    );
  }
} else if (!isMockAuth) {
  // Fires if env vars are missing — helps diagnose prefix issues
  console.warn(
    "[Amplify] NOT configured — missing EXPO_PUBLIC_COGNITO_USER_POOL_ID or EXPO_PUBLIC_COGNITO_APP_CLIENT_ID",
  );
}
