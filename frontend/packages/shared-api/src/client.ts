/**
 * apiClient — shared Axios instance
 *
 * Location: packages/shared-api/src/client.ts
 *
 * All surface API calls in the Pilot app route through this client.
 * Provides:
 *   - Base URL from env vars (NEXT_PUBLIC_API_URL or EXPO_PUBLIC_API_URL)
 *   - Content-Type: application/json header
 *   - JWT request interceptor — attaches Cognito ID token from AWS Amplify
 *   - 401 response interceptor — refreshes token once, then dispatches
 *     auth:session-expired custom event before rejecting
 *
 * FE-B2: On unrecoverable 401 (refresh failed), dispatches
 *   window.dispatchEvent(new CustomEvent('auth:session-expired'))
 *   so useSessionExpiry hooks can respond without circular imports.
 */

import axios, { isAxiosError } from "axios";
import { getImpersonation } from "./impersonation";

// Re-exported so consumers (apps/web, apps/mobile) don't need a direct axios dep
export { isAxiosError };

export const apiClient = axios.create({
  baseURL:
    (typeof process !== "undefined" && process.env?.NEXT_PUBLIC_API_URL) ||
    (typeof process !== "undefined" && process.env?.EXPO_PUBLIC_API_URL) ||
    "http://127.0.0.1:8000",
  headers: {
    "Content-Type": "application/json",
  },
});

// ---------------------------------------------------------------------------
// Request interceptor — attaches JWT + tenant ID header
// ---------------------------------------------------------------------------

apiClient.interceptors.request.use(async (config) => {
  try {
    // Dynamic import: avoids bundling aws-amplify in environments that don't need it
    const { fetchAuthSession } = await import("aws-amplify/auth");
    const session = await fetchAuthSession();
    const token = session.tokens?.idToken?.toString();
    if (token) {
      config.headers["Authorization"] = `Bearer ${token}`;
      if (process.env.NODE_ENV !== "production") {
        console.log(
          "[apiClient] JWT attached — token prefix:",
          token.slice(0, 20) + "…",
        );
      }
    } else {
      if (process.env.NODE_ENV !== "production") {
        console.warn(
          "[apiClient] No token from fetchAuthSession — request will 401. session.tokens:",
          JSON.stringify(session.tokens),
        );
      }
    }
  } catch (e) {
    // Not authenticated — let request through; backend will 401
    if (process.env.NODE_ENV !== "production") {
      console.warn("[apiClient] fetchAuthSession threw:", e);
    }
  }

  // C-B15: Attach impersonation header when a session is active.
  // Read synchronously from sessionStorage on every request — no React state.
  // The header is ignored by the backend for tenant users (only platform users
  // with impersonate_tenant permission activate the impersonation path).
  const imp = getImpersonation();
  if (imp) {
    config.headers["X-Impersonate-Tenant"] = imp.tenantId;
  }

  return config;
});

// ---------------------------------------------------------------------------
// Response interceptor — catches 401, refreshes token, retries once
// ---------------------------------------------------------------------------

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalConfig = error.config as typeof error.config & {
      _retried?: boolean;
    };
    if (error.response?.status === 401 && !originalConfig._retried) {
      originalConfig._retried = true;
      try {
        const { fetchAuthSession } = await import("aws-amplify/auth");
        const session = await fetchAuthSession({ forceRefresh: true });
        const token = session.tokens?.idToken?.toString();
        if (token) {
          originalConfig.headers["Authorization"] = `Bearer ${token}`;
          return apiClient(originalConfig);
        }
      } catch {
        // Refresh failed — dispatch session-expired event so auth layer can respond
        if (typeof window !== "undefined") {
          window.dispatchEvent(new CustomEvent("auth:session-expired"));
        }
      }
    }
    return Promise.reject(error);
  },
);
