/**
 * amplify-config.ts — Configures AWS Amplify once at module load.
 *
 * This file MUST be imported before any aws-amplify/auth usage.
 * It is imported at the top of providers.tsx to guarantee evaluation
 * order ahead of AuthProvider's useEffect calls.
 *
 * Skipped entirely when NEXT_PUBLIC_USE_MOCK_AUTH=true (dev/test mock mode).
 */

import { Amplify } from "aws-amplify";

const userPoolId = process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID ?? "";
const userPoolClientId = process.env.NEXT_PUBLIC_COGNITO_APP_CLIENT_ID ?? "";

if (
  process.env.NEXT_PUBLIC_USE_MOCK_AUTH !== "true" &&
  userPoolId &&
  userPoolClientId
) {
  Amplify.configure({
    Auth: {
      Cognito: {
        userPoolId,
        userPoolClientId,
      },
    },
  });
}
