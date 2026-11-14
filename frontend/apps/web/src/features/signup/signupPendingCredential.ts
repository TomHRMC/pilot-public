/**
 * signupPendingCredential — in-memory holder for the email + password
 * collected on /signup/account, consumed by /signup/verify for auto-sign-in.
 *
 * Location: apps/web/src/features/signup/signupPendingCredential.ts
 *
 * SIGNUP-GA-1 (ADR-0011): the password MUST NEVER be written to sessionStorage
 * or any persistent store. This module-level object survives client-side
 * navigation (App Router) but is lost on a full page reload — which is the
 * intended fallback (verify page routes to /login?confirmed=true instead of
 * auto-sign-in when the password is gone).
 *
 * Also holds the business/owner form fields so the verify step can complete
 * POST /api/v1/signup after Cognito confirmation (the Lambda's Path 3 fires
 * on ConfirmSignUp, creating the tenant; the wizard's resolve-or-attach call
 * then overwrites the placeholder name with business_name — design §D).
 */

export interface SignupPendingCredential {
  email: string;
  password: string;
  /** Business/owner fields collected on the account page, POSTed to
   *  /api/v1/signup after Cognito confirmation. */
  businessFields: {
    business_name: string;
    trade: string;
    business_size: string;
    zip: string;
    time_zone: string;
    owner_email: string;
    owner_first_name: string;
    owner_last_name: string;
  };
}

/**
 * Module-level in-memory holder. Survives client-side navigation only.
 * Cleared after the verify step consumes it (auto-sign-in + POST /signup).
 */
export const signupPendingCredential: {
  current: SignupPendingCredential | null;
} = {
  current: null,
};

/** Convenience: set the pending credential (called from account page). */
export function setSignupPendingCredential(
  cred: SignupPendingCredential,
): void {
  signupPendingCredential.current = cred;
}

/** Convenience: read + clear (called from verify page after consumption). */
export function consumeSignupPendingCredential(): SignupPendingCredential | null {
  const cred = signupPendingCredential.current;
  signupPendingCredential.current = null;
  return cred;
}

/** Convenience: peek without clearing (for the hard-reload fallback check). */
export function peekSignupPendingCredential(): SignupPendingCredential | null {
  return signupPendingCredential.current;
}

/** Convenience: clear (e.g. on error / abandon). */
export function clearSignupPendingCredential(): void {
  signupPendingCredential.current = null;
}
