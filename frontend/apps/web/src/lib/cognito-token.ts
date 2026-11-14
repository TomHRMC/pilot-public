/**
 * getCognitoAccessToken — MFA-WIRE-1 (design §G-Q1)
 *
 * Location: apps/web/src/lib/cognito-token.ts
 *
 * Cognito user-scoped MFA APIs (AssociateSoftwareToken, VerifySoftwareToken,
 * SetUserMFAPreference, GetUserAttributeVerificationCode, VerifyUserAttribute)
 * require the **access token**, not the ID token. This helper fetches it from
 * the active Amplify session.
 *
 * SECURITY: The access token is **in-memory only** — never logged, never
 * persisted, never returned to a caller that would store it. Callers must
 * use it immediately in a request header and discard the reference.
 *
 * This is the second file in apps/web/src/lib/ (the first is amplify-config.ts).
 * It is NOT an API client — all /api/v1/... calls still go through apiClient
 * (new code) or the wizard's documented PLAT-DEBT fetch helper.
 */
import { fetchAuthSession } from "aws-amplify/auth";

/**
 * Returns the current Cognito access token as a string, or null if the
 * session is unavailable / expired. Callers should send the result in an
 * `X-Cognito-Access-Token` header and handle null by still sending the
 * request (the backend maps the missing/invalid token to the correct
 * RFC 7807 error code — design §F.3).
 */
export async function getCognitoAccessToken(): Promise<string | null> {
  try {
    const session = await fetchAuthSession();
    return session.tokens?.accessToken?.toString() ?? null;
  } catch {
    // Not authenticated — return null; the backend will 400/401 with the
    // appropriate RFC 7807 code. Never log the session or token.
    return null;
  }
}
