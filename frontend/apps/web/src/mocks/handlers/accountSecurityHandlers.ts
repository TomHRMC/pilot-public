/**
 * Account Security MSW Handlers — FE-B12
 *
 * Location: apps/web/src/mocks/handlers/accountSecurityHandlers.ts
 *
 * Covers BE-B13 / A68–A71:
 *  - GET  /api/v1/users/me/mfa-status
 *  - POST /api/v1/users/me/mfa/methods/{method_type}/enroll-start
 *  - POST /api/v1/users/me/mfa/methods/{method_type}/enroll-confirm
 *  - DELETE /api/v1/users/me/mfa/methods/{method_id}
 *  - POST /api/v1/users/me/mfa/recovery-codes/generate
 *  - GET  /api/v1/users/me/mfa/recovery-codes/status
 *  - GET  /api/v1/users/me/sessions
 *  - DELETE /api/v1/users/me/sessions/{session_id}
 *  - POST /api/v1/users/me/sessions/revoke-others
 *  - GET  /api/v1/users/me
 *  - PUT  /api/v1/users/me
 *  - POST /api/v1/auth/password (password change)
 *  - POST /api/v1/users/me/data-exports
 *  - GET  /api/v1/users/me/data-exports
 *  - GET  /api/v1/users/me/data-exports/{export_id}
 */

import { http, HttpResponse } from "msw";
import {
  MFA_STATUS_NONE,
  MFA_TOTP_ENROLL_START,
  MFA_SMS_ENROLL_START,
  MFA_EMAIL_ENROLL_START,
  MFA_ENROLL_CONFIRM_SUCCESS,
  MFA_RECOVERY_CODES_STATUS_EMPTY,
  MFA_RECOVERY_CODES_GENERATE,
  ACTIVE_SESSIONS,
  DATA_EXPORT_CREATE,
  DATA_EXPORT_STATUS_PROCESSING,
  DATA_EXPORT_STATUS_READY,
  RECENT_EXPORTS,
  PROFILE_FIXTURE,
} from "../../features/account-settings/mocks/accountFixtures";
import type { MFAEnrollmentPath } from "../../features/account-settings/types";

const USERS_API = "/api/v1/users";
const AUTH_API = "/api/v1/auth";

// Mutable state for simulating polling state changes
let exportPollCount = 0;
let enrolledMethods: MFAEnrollmentPath[] = [];
let sessions = [...ACTIVE_SESSIONS];

export const accountSecurityHandlers = [
  // ─── Profile ───────────────────────────────────────────────────────────────

  http.get(`${USERS_API}/me`, () => {
    return HttpResponse.json(PROFILE_FIXTURE);
  }),

  http.put(`${USERS_API}/me`, async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({ ...PROFILE_FIXTURE, ...(body as object) });
  }),

  // ─── MFA Status ────────────────────────────────────────────────────────────
  // MFA-WIRE-1: response now includes the additive `methods[]` array (design
  // §D.4) alongside `enrolled_methods` (kept for backward compat). The two
  // are derived from the same module-level `enrolledMethods` state.

  http.get(`${USERS_API}/me/mfa-status`, () => {
    const methods = enrolledMethods.map((methodType) => ({
      method_id: `mfa-method-${methodType}`,
      method_type: methodType,
      enrolled_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
      last_used_at: null,
      destination_masked: methodType === "sms" ? "••••0001" : null,
    }));
    return HttpResponse.json({
      ...MFA_STATUS_NONE,
      enrolled_methods: enrolledMethods,
      methods,
    });
  }),

  // ─── MFA Enroll-Start ──────────────────────────────────────────────────────

  http.post(
    `${USERS_API}/me/mfa/methods/:methodType/enroll-start`,
    ({ params }) => {
      const { methodType } = params as { methodType: string };
      if (methodType === "totp")
        return HttpResponse.json(MFA_TOTP_ENROLL_START);
      if (methodType === "sms") return HttpResponse.json(MFA_SMS_ENROLL_START);
      if (methodType === "email")
        return HttpResponse.json(MFA_EMAIL_ENROLL_START);
      return HttpResponse.json({ detail: "Unknown method" }, { status: 400 });
    },
  ),

  // ─── MFA Enroll-Confirm ────────────────────────────────────────────────────

  http.post(
    `${USERS_API}/me/mfa/methods/:methodType/enroll-confirm`,
    async ({ params, request }) => {
      const { methodType } = params as { methodType: MFAEnrollmentPath };
      const body = (await request.json()) as { code: string };

      // Wrong code simulation: "000000" always fails
      if (body.code === "000000") {
        return HttpResponse.json(
          { detail: "That code doesn't match. Check your app and try again." },
          { status: 400 },
        );
      }

      // Expired code simulation: "999999" returns expired error
      // (MFA-WIRE-1: aligned with backend mock-client semantics — Part A
      //  uses 000000 = mismatch / 999999 = expired)
      if (body.code === "999999") {
        return HttpResponse.json(
          {
            code: "mfa_code_expired",
            detail: "Code expired. Request a new one.",
          },
          { status: 400 },
        );
      }

      // Success: track enrollment
      if (!enrolledMethods.includes(methodType)) {
        enrolledMethods.push(methodType);
      }
      return HttpResponse.json(MFA_ENROLL_CONFIRM_SUCCESS);
    },
  ),

  // ─── MFA Method Delete ─────────────────────────────────────────────────────

  http.delete(`${USERS_API}/me/mfa/methods/:methodId`, ({ params }) => {
    const { methodId } = params as { methodId: string };

    // MFA-WIRE-1: cognito-fail sentinel → 502 cognito_unavailable (design §F.3)
    // so the rollback + error banner path is testable.
    if (methodId === "cognito-fail") {
      return HttpResponse.json(
        {
          code: "cognito_unavailable",
          detail: "We couldn't reach the authentication service.",
        },
        { status: 502 },
      );
    }

    // If only 1 method enrolled, return 409 last_method_required
    if (enrolledMethods.length <= 1) {
      return HttpResponse.json(
        {
          code: "last_method_required",
          detail:
            "Can't remove the last MFA method when your team requires MFA.",
        },
        { status: 409 },
      );
    }
    // Remove last enrolled method for fixture purposes
    enrolledMethods = enrolledMethods.slice(0, -1);
    return new HttpResponse(null, { status: 204 });
  }),

  // ─── Recovery Codes ────────────────────────────────────────────────────────

  http.get(`${USERS_API}/me/mfa/recovery-codes/status`, () => {
    return HttpResponse.json(MFA_RECOVERY_CODES_STATUS_EMPTY);
  }),

  http.post(`${USERS_API}/me/mfa/recovery-codes/generate`, () => {
    return HttpResponse.json(MFA_RECOVERY_CODES_GENERATE);
  }),

  // ─── Active Sessions ───────────────────────────────────────────────────────

  http.get(`${USERS_API}/me/sessions`, () => {
    return HttpResponse.json(sessions.filter((s) => !s.revoked_at));
  }),

  http.delete(`${USERS_API}/me/sessions/:sessionId`, ({ params }) => {
    const { sessionId } = params as { sessionId: string };
    const session = sessions.find((s) => s.session_id === sessionId);

    if (!session) {
      return HttpResponse.json(
        { detail: "Session not found" },
        { status: 404 },
      );
    }

    // Mark as revoked
    sessions = sessions.map((s) =>
      s.session_id === sessionId
        ? { ...s, revoked_at: new Date().toISOString() }
        : s,
    );
    return new HttpResponse(null, { status: 204 });
  }),

  http.post(`${USERS_API}/me/sessions/revoke-others`, () => {
    const nonCurrentCount = sessions.filter(
      (s) => !s.is_current && !s.revoked_at,
    ).length;
    sessions = sessions.map((s) =>
      !s.is_current ? { ...s, revoked_at: new Date().toISOString() } : s,
    );
    return HttpResponse.json({ revoked_count: nonCurrentCount });
  }),

  // ─── Password Change ───────────────────────────────────────────────────────

  http.post(`${AUTH_API}/password`, async ({ request }) => {
    const body = (await request.json()) as {
      current_password: string;
      new_password: string;
    };

    // Wrong current password simulation: "wrongpassword"
    if (body.current_password === "wrongpassword") {
      return HttpResponse.json(
        { detail: "Current password is incorrect." },
        { status: 401 },
      );
    }

    // Password policy violation: passwords shorter than 8 chars
    if (body.new_password.length < 8) {
      return HttpResponse.json(
        {
          detail:
            "Password doesn't meet requirements: must be at least 8 characters.",
        },
        { status: 400 },
      );
    }

    return HttpResponse.json({ success: true });
  }),

  // ─── Data Export ───────────────────────────────────────────────────────────

  http.post(`${USERS_API}/me/data-exports`, () => {
    // Reset poll counter on new export request
    exportPollCount = 0;
    return HttpResponse.json(DATA_EXPORT_CREATE, { status: 201 });
  }),

  http.get(`${USERS_API}/me/data-exports`, () => {
    return HttpResponse.json(RECENT_EXPORTS);
  }),

  http.get(`${USERS_API}/me/data-exports/:exportId`, ({ params }) => {
    const { exportId } = params as { exportId: string };

    if (exportId === "export-002") {
      // Expired fixture
      return HttpResponse.json({
        ...DATA_EXPORT_STATUS_READY,
        export_id: "export-002",
        status: "expired",
        signed_url: null,
        expires_at: new Date(
          Date.now() - 3 * 24 * 60 * 60 * 1000,
        ).toISOString(),
      });
    }

    // Simulate state progression with poll count
    exportPollCount += 1;

    if (exportPollCount <= 2) {
      return HttpResponse.json(DATA_EXPORT_STATUS_PROCESSING);
    }

    return HttpResponse.json(DATA_EXPORT_STATUS_READY);
  }),
];
