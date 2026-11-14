/**
 * Auth Module — Shared Types
 *
 * Location: packages/ui/src/auth/types.ts
 *
 * Single source of truth for PilotRole, PilotUser, and AuthContextValue
 * consumed by AuthProvider, useAuth, RequireAuth, and RoleGate.
 *
 * FE-B2 changes:
 *   - signIn: return type upgraded to Promise<{ nextStep: SignInOutput['nextStep'] }>
 *   - confirmMfaChallenge: new method for handling Cognito MFA challenges at login
 *   - RequireAuthProps: added onRedirect prop for testable, framework-agnostic redirect
 */

import type { SignInOutput } from "aws-amplify/auth";

export type PilotRole = "owner" | "technician" | "office_staff" | "accountant";

export interface PilotUser {
  id: string;
  email: string;
  role: PilotRole;
  tenantId: string;
  displayName: string;
  accessToken: string;
  /**
   * PLP-FIX-7: Server-authoritative permission set from
   * GET /api/v1/users/me/permissions. Empty array when unauthenticated.
   * Mock mode derives from ROLE_PERMISSION_MAP for test compatibility.
   * Optional in the type so existing test mocks don't break — the provider
   * always sets it; useHasPermission falls back to ROLE_PERMISSION_MAP when
   * undefined.
   */
  permissions?: string[];
  /** FE-UI-NAV-S1: populated from GET /api/v1/users/me/profile (profile_photo_url field).
   *  Signed S3 URL or null when no avatar has been uploaded. */
  profile_photo_url?: string | null;
}

export interface AuthContextValue {
  user: PilotUser | null;
  isAuthenticated: boolean;
  role: PilotRole | null;
  /**
   * PLP-FIX-7: Server-authoritative permission set from
   * GET /api/v1/users/me/permissions. Empty array when unauthenticated.
   * Used by useHasPermission / useRequiresPermission / RoleGate.
   * Optional so existing test mocks don't break — the provider always sets it;
   * useHasPermission falls back to ROLE_PERMISSION_MAP when undefined.
   */
  permissions?: readonly string[];
  /**
   * Signs in via Amplify Cognito. Returns nextStep so callers can handle
   * MFA challenges. In mock mode returns { nextStep: { signInStep: 'DONE' } }.
   *
   * Callers MUST check nextStep.signInStep before assuming login is complete.
   */
  signIn: (
    email: string,
    password: string,
  ) => Promise<{ nextStep: SignInOutput["nextStep"] }>;
  /**
   * Confirms an MFA challenge during sign-in. Called after signIn returns
   * a non-DONE nextStep. In mock mode, always resolves successfully.
   */
  confirmMfaChallenge: (
    code: string,
  ) => Promise<{ nextStep: SignInOutput["nextStep"] }>;
  signOut: () => Promise<void>;
  /** Returns a fresh accessToken; called by apiClient 401 interceptor */
  refreshSession: () => Promise<string>;
  /**
   * PLP-FIX-7: Resolves with the fully-loaded PilotUser once the post-Cognito
   * backend fetch (GET /users/me/permissions) completes, or null if the
   * session resolves to no user. Used by useLoginFlow to await the resolved
   * role before routing — eliminates the role race (INV-BUG-2).
   *
   * Optional so existing test mocks don't break — the provider always sets it.
   * useLoginFlow falls back to reading `role` from context when absent.
   *
   * If a session load is already in-flight, the same promise is shared.
   * If no load is in-flight and user is already set, resolves immediately.
   */
  whenSessionReady?: () => Promise<PilotUser | null>;
}

export interface AuthProviderProps {
  children: React.ReactNode;
  /**
   * When set (dev only via NEXT_PUBLIC_USE_MOCK_AUTH=true / EXPO_PUBLIC_USE_MOCK_AUTH=true),
   * bypasses Cognito and returns a fake user with the given role.
   * Never set in production.
   */
  mockUser?: Pick<PilotUser, "role" | "email" | "displayName">;
}

export interface RequireAuthProps {
  children: React.ReactNode;
  /** '/login' for web; login screen name for mobile */
  redirectTo: string;
  /**
   * Platform-specific redirect function.
   * Web: router.replace from next/navigation.
   * Mobile: router.replace from expo-router.
   * Falls back to window.location.replace if not provided (for test compatibility).
   */
  onRedirect?: (path: string) => void;
}
