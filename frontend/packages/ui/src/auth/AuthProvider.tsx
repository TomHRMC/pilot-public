/**
 * AuthProvider — shared auth context provider
 *
 * Location: packages/ui/src/auth/AuthProvider.tsx
 *
 * Wraps the application in an AuthContext that provides user state,
 * signIn/signOut, and JWT refresh via AWS Amplify Cognito.
 *
 * Authorization model:
 *   - Cognito is the IDENTITY provider only (proves who you are via JWT).
 *   - Role + tenantId come from GET /api/v1/auth/me (the local DB).
 *   - This avoids storing authorization data in Cognito custom claims.
 *
 * When NEXT_PUBLIC_USE_MOCK_AUTH=true (web) or EXPO_PUBLIC_USE_MOCK_AUTH=true (mobile)
 * AND a `mockUser` prop is supplied, the provider bypasses Amplify entirely and
 * returns a fake PilotUser — enables dev/test flows without a live Cognito pool.
 *
 * FE-B2 changes:
 *   - signIn now returns { nextStep } so useLoginFlow can handle MFA challenges
 *   - confirmMfaChallenge added to AuthContextValue
 */

"use client";

import React, {
  createContext,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import type { SignInOutput } from "aws-amplify/auth";
import { getImpersonation } from "@pilot/shared-api";
import { useQueryClient } from "@tanstack/react-query";
import { ROLE_PERMISSION_MAP } from "../role-gate/permissions";
import type {
  AuthContextValue,
  AuthProviderProps,
  PilotRole,
  PilotUser,
} from "./types";

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

export const AuthContext = createContext<AuthContextValue | null>(null);
AuthContext.displayName = "AuthContext";

// ---------------------------------------------------------------------------
// Mock constants (dev only)
// ---------------------------------------------------------------------------

const MOCK_TENANT_ID = "mock-tenant-001";

function buildMockUser(
  partial: Pick<PilotUser, "role" | "email" | "displayName">,
): PilotUser {
  // PLP-FIX-7: mock mode derives permissions from the static map so existing
  // tests keep working without a live /users/me/permissions call.
  const perms = Array.from(ROLE_PERMISSION_MAP[partial.role]) as string[];
  return {
    id: "mock-user-001",
    tenantId: MOCK_TENANT_ID,
    accessToken: "mock-access-token",
    permissions: perms,
    ...partial,
  };
}

// Mock nextStep response — used in mock mode to signal successful login
const MOCK_DONE_NEXT_STEP: SignInOutput["nextStep"] = {
  signInStep: "DONE",
};

// ---------------------------------------------------------------------------
// Helper: load user from backend after Cognito auth
// Fetches GET /api/v1/auth/me to get role + tenantId from the local DB.
// ---------------------------------------------------------------------------

interface UserPermissionsResponse {
  user_id: string;
  tenant_id: string;
  role_code: PilotRole;
  role_name: string;
  permissions: string[];
}

async function fetchUserFromBackend(
  token: string,
  fallbackEmail: string,
): Promise<PilotUser | null> {
  const apiBase =
    (typeof process !== "undefined" &&
      (process.env?.NEXT_PUBLIC_API_URL || process.env?.EXPO_PUBLIC_API_URL)) ||
    "http://127.0.0.1:8000";

  // C-B15: Attach impersonation header when a session is active.
  // This is the sanctioned raw fetch() exception (predates the apiClient
  // mandate). The header is ignored by the backend for tenant users.
  const imp = getImpersonation();
  const res = await fetch(`${apiBase}/api/v1/users/me/permissions`, {
    headers: {
      Authorization: `Bearer ${token}`,
      ...(imp ? { "X-Impersonate-Tenant": imp.tenantId } : {}),
    },
  });

  if (!res.ok) {
    // SIGNUP-UI-FIX-1: Any non-OK response means the user's token is invalid,
    // the user was deleted from the DB (404), or the backend is unreachable.
    // In all cases, return null so the user is treated as not authenticated
    // (RequireAuth redirects to /login). The previous fallback to a minimal
    // user with tenantId="" caused deleted users to see the dashboard.
    return null;
  }

  const data = (await res.json()) as UserPermissionsResponse;

  return {
    id: data.user_id,
    email: fallbackEmail,
    displayName: fallbackEmail,
    role: data.role_code,
    tenantId: data.tenant_id,
    accessToken: token,
    // PLP-FIX-7: carry the server-authoritative permission set.
    permissions: data.permissions ?? [],
  };
}
// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function AuthProvider({ children, mockUser }: AuthProviderProps) {
  const [user, setUser] = useState<PilotUser | null>(null);
  const [loading, setLoading] = useState(true);

  // PLP-FIX-9 (INV-BUG-7): obtain the QueryClient from context so signOut
  // can clear the cache at session boundaries. useQueryClient() always
  // resolves to the correct instance (production singleton or test-local).
  const queryClient = useQueryClient();

  // PLP-FIX-7: userRef mirrors `user` state synchronously so whenSessionReady()
  // can return the latest user without waiting for a React re-render. This
  // eliminates the role race (INV-BUG-2) where useLoginFlow read a stale
  // `role` from the context closure after signIn returned.
  const userRef = useRef<PilotUser | null>(null);
  const updateUser = useCallback((u: PilotUser | null) => {
    userRef.current = u;
    setUser(u);
  }, []);

  // Determine if we're in mock mode
  const isMockMode =
    Boolean(mockUser) &&
    (process.env.NEXT_PUBLIC_USE_MOCK_AUTH === "true" ||
      process.env.EXPO_PUBLIC_USE_MOCK_AUTH === "true");

  useEffect(() => {
    if (isMockMode && mockUser) {
      updateUser(buildMockUser(mockUser));
      setLoading(false);
      return;
    }

    // Real Amplify session check — lazy-import to avoid bundling Amplify
    // when running in mock mode (saves ~300KB in test bundles).
    let cancelled = false;

    async function loadSession() {
      try {
        const { fetchAuthSession, getCurrentUser } =
          await import("aws-amplify/auth");
        const [session, cognitoUser] = await Promise.all([
          fetchAuthSession(),
          getCurrentUser(),
        ]);

        if (cancelled) return;

        const token = session.tokens?.idToken?.toString() ?? "";
        if (!token) {
          updateUser(null);
          return;
        }

        const fallbackEmail =
          cognitoUser.signInDetails?.loginId ?? cognitoUser.username;

        const pilotUser = await fetchUserFromBackend(token, fallbackEmail);
        if (!cancelled) updateUser(pilotUser);
        // SIGNUP-UI-FIX-1: if backend returned null (401/403 — user deleted
        // from DB), clear the stale Amplify session so the user is fully
        // logged out and can start a fresh signup.
        if (pilotUser === null && !cancelled) {
          try {
            const { signOut: amplifySignOut } =
              await import("aws-amplify/auth");
            await amplifySignOut();
          } catch {
            // Ignore — session may already be invalid
          }
        }
      } catch {
        // Not authenticated — leave user as null
        updateUser(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadSession();
    return () => {
      cancelled = true;
    };
  }, [isMockMode, mockUser, updateUser]);

  const signIn = useCallback(
    async (
      email: string,
      password: string,
    ): Promise<{ nextStep: SignInOutput["nextStep"] }> => {
      if (isMockMode && mockUser) {
        updateUser(buildMockUser(mockUser));
        return { nextStep: MOCK_DONE_NEXT_STEP };
      }

      const { signIn: amplifySignIn } = await import("aws-amplify/auth");

      // On React Native (Expo Go + production), use USER_PASSWORD_AUTH because:
      // - SRP (USER_SRP_AUTH) requires @aws-amplify/react-native for native crypto
      // - @aws-amplify/react-native requires pod install + native build → not available in Expo Go
      // - USER_PASSWORD_AUTH sends credentials over TLS without native crypto modules
      // - "Username and password" flow is enabled on the App Client alongside SRP
      //
      // On web, the default USER_SRP_AUTH is used (web has native crypto.getRandomValues).
      //
      // Detection: navigator.product === 'ReactNative' is the canonical RN detection
      // that works in both Expo Go and production builds without importing Platform.
      const isReactNative =
        typeof navigator !== "undefined" && navigator.product === "ReactNative";

      const result = await amplifySignIn({
        username: email,
        password,
        options: isReactNative
          ? { authFlowType: "USER_PASSWORD_AUTH" as const }
          : undefined,
      });

      // Only load session when sign-in is fully complete (no pending MFA)
      if (result.nextStep.signInStep === "DONE") {
        const { fetchAuthSession, getCurrentUser } =
          await import("aws-amplify/auth");
        const [session, cognitoUser] = await Promise.all([
          fetchAuthSession(),
          getCurrentUser(),
        ]);
        const token = session.tokens?.idToken?.toString() ?? "";
        const fallbackEmail =
          cognitoUser.signInDetails?.loginId ?? cognitoUser.username;

        const pilotUser = await fetchUserFromBackend(token, fallbackEmail);
        updateUser(pilotUser);
      }

      return { nextStep: result.nextStep };
    },
    [isMockMode, mockUser, updateUser],
  );

  const confirmMfaChallenge = useCallback(
    async (code: string): Promise<{ nextStep: SignInOutput["nextStep"] }> => {
      if (isMockMode) {
        return { nextStep: MOCK_DONE_NEXT_STEP };
      }

      const { confirmSignIn } = await import("aws-amplify/auth");
      const result = await confirmSignIn({ challengeResponse: code });

      // Load session after successful MFA confirmation
      if (result.nextStep.signInStep === "DONE") {
        const { fetchAuthSession, getCurrentUser } =
          await import("aws-amplify/auth");
        const [session, cognitoUser] = await Promise.all([
          fetchAuthSession(),
          getCurrentUser(),
        ]);
        const token = session.tokens?.idToken?.toString() ?? "";
        const fallbackEmail =
          cognitoUser.signInDetails?.loginId ?? cognitoUser.username;

        const pilotUser = await fetchUserFromBackend(token, fallbackEmail);
        updateUser(pilotUser);
      }

      return { nextStep: result.nextStep };
    },
    [isMockMode, updateUser],
  );

  const signOut = useCallback(async () => {
    // PLP-FIX-9 (INV-BUG-7): clear the TanStack Query cache at every session
    // boundary so stale tenant-scoped data from a prior user never renders
    // for the next user. This runs in BOTH the mock-mode and live paths.
    queryClient.clear();
    if (isMockMode) {
      updateUser(null);
      return;
    }
    const { signOut: amplifySignOut } = await import("aws-amplify/auth");
    await amplifySignOut();
    queryClient.clear();
    updateUser(null);
  }, [isMockMode, updateUser, queryClient]);

  const refreshSession = useCallback(async (): Promise<string> => {
    if (isMockMode) return "mock-access-token";
    const { fetchAuthSession } = await import("aws-amplify/auth");
    const session = await fetchAuthSession({ forceRefresh: true });
    const token = session.tokens?.idToken?.toString() ?? "";
    // Re-fetch user from backend to pick up any role changes
    if (token && userRef.current) {
      const updated = await fetchUserFromBackend(token, userRef.current.email);
      updateUser(updated);
    }
    return token;
  }, [isMockMode, updateUser]);

  // PLP-FIX-7: whenSessionReady — resolves with the latest PilotUser from the
  // ref (synchronous, post-setUser) or null. Used by useLoginFlow to await
  // the resolved role before routing, eliminating the role race (INV-BUG-2).
  const whenSessionReady = useCallback(async (): Promise<PilotUser | null> => {
    return userRef.current;
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: user !== null,
      role: user?.role ?? null,
      // PLP-FIX-7: expose server-authoritative permissions for gating.
      permissions: user?.permissions ?? [],
      signIn,
      confirmMfaChallenge,
      signOut,
      refreshSession,
      whenSessionReady,
    }),
    [
      user,
      signIn,
      confirmMfaChallenge,
      signOut,
      refreshSession,
      whenSessionReady,
    ],
  );

  // Show nothing while checking session to avoid auth flash
  if (loading) return null;

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
