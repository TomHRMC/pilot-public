/**
 * impersonation — tenant impersonation session store
 *
 * Location: packages/shared-api/src/impersonation.ts
 *
 * C-B15 Part B: Module-level store persisted to sessionStorage.
 * Platform operators (Tom) use this to act as any tenant's owner for
 * support and onboarding assistance. The session is tab-scoped
 * (sessionStorage) — closing the tab ends the session (a safety feature).
 *
 * The apiClient request interceptor reads getImpersonation() on every
 * request and attaches the X-Impersonate-Tenant header when a session
 * is active. AuthProvider.fetchUserFromBackend() does the same for its
 * raw fetch() call (sanctioned pre-apiClient-mandate exception).
 *
 * useImpersonation() is a React hook that reads the store on mount and
 * subscribes to the custom "pilot:impersonation-change" event + the
 * "storage" event (cross-tab sync) so components re-render when the
 * session changes.
 *
 * RULE 29: uses process.env.NODE_ENV (not __DEV__) — this package is
 * consumed by both web and mobile.
 */

import { useEffect, useState } from "react";

// ── Types ────────────────────────────────────────────────────────────────────

export interface ImpersonationSession {
  tenantId: string;
  tenantName: string;
}

// ── Constants ────────────────────────────────────────────────────────────────

const STORAGE_KEY = "pilot.impersonation";
const CHANGE_EVENT = "pilot:impersonation-change";

// ── Store functions ──────────────────────────────────────────────────────────

/**
 * Read the active impersonation session from sessionStorage.
 * Returns null if absent, invalid JSON, or during SSR (no window).
 */
export function getImpersonation(): ImpersonationSession | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as ImpersonationSession;
    if (
      typeof parsed !== "object" ||
      parsed === null ||
      typeof parsed.tenantId !== "string" ||
      typeof parsed.tenantName !== "string"
    ) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

/**
 * Write the impersonation session to sessionStorage and dispatch
 * a change event so subscribers (useImpersonation) re-render.
 */
export function setImpersonation(session: ImpersonationSession): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(session));
    window.dispatchEvent(new CustomEvent(CHANGE_EVENT));
  } catch {
    // sessionStorage unavailable — no-op
  }
}

/**
 * Remove the impersonation session from sessionStorage and dispatch
 * a change event so subscribers (useImpersonation) re-render.
 */
export function clearImpersonation(): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.removeItem(STORAGE_KEY);
    window.dispatchEvent(new CustomEvent(CHANGE_EVENT));
  } catch {
    // sessionStorage unavailable — no-op
  }
}

// ── React hook ───────────────────────────────────────────────────────────────

/**
 * useImpersonation — React hook that returns the active impersonation
 * session (or null). Subscribes to the custom change event + the
 * storage event for cross-tab sync.
 *
 * This is a legitimate identity-sensitive subscription case (Context-adjacent).
 * A small hand-rolled subscription is appropriate; do not over-engineer.
 */
export function useImpersonation(): ImpersonationSession | null {
  const [session, setSession] = useState<ImpersonationSession | null>(() =>
    getImpersonation(),
  );

  useEffect(() => {
    const handleChange = () => setSession(getImpersonation());

    // Custom event — fired by setImpersonation/clearImpersonation
    window.addEventListener(CHANGE_EVENT, handleChange);
    // Storage event — cross-tab sync (sessionStorage does NOT fire storage
    // events, but we listen anyway for safety if the store ever moves to
    // localStorage; it's a no-op today).
    window.addEventListener("storage", handleChange);

    return () => {
      window.removeEventListener(CHANGE_EVENT, handleChange);
      window.removeEventListener("storage", handleChange);
    };
  }, []);

  return session;
}
