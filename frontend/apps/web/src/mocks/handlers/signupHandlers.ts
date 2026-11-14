/**
 * Signup MSW Handlers — FE-B13
 *
 * Location: apps/web/src/mocks/handlers/signupHandlers.ts
 *
 * Covers BE-B14 / A73–A76:
 *  - POST /api/v1/signup                              (step 1 — public, no JWT)
 *  - GET  /api/v1/signup/:tenantId/state              (resumability)
 *  - PUT  /api/v1/signup/:tenantId/step2              (legal acceptance advance)
 *  - PUT  /api/v1/signup/:tenantId/step3              (phone verification advance)
 *  - PUT  /api/v1/signup/:tenantId/step4              (tier selection advance)
 *  - PUT  /api/v1/signup/:tenantId/step5              (confirmation advance)
 *  - GET  /api/v1/signup/:tenantId/legal/required     (legal doc list + acceptance state)
 *  - POST /api/v1/signup/:tenantId/legal/accept       (immutable acceptance record)
 *  - POST /api/v1/signup/:tenantId/phone/send-otp     (send OTP)
 *  - POST /api/v1/signup/:tenantId/phone/confirm-otp  (confirm OTP)
 *  - GET  /api/v1/subscription-tiers                  (tier list)
 *  - POST /api/v1/signup/:tenantId/payment-intent     (Stripe test client_secret)
 *  - POST /api/v1/tenants/:tenantId/subscription/convert-from-trial
 */

import { http, HttpResponse } from "msw";
import {
  SIGNUP_INITIATE_SUCCESS,
  SIGNUP_DUPLICATE_EMAIL_ERROR,
  SIGNUP_STATE_STEP1,
  SIGNUP_STATE_STEP2,
  SIGNUP_STATE_STEP3,
  SIGNUP_STATE_STEP4,
  SIGNUP_STATE_STEP5_TRIAL,
  SIGNUP_STATE_STEP5_CHARTER,
  SIGNUP_STATE_COMPLETE,
  SIGNUP_STATE_COMPLETE_CHARTER,
  LEGAL_REQUIRED_RESPONSE,
  LEGAL_ACCEPT_TOS_RESPONSE,
  LEGAL_ACCEPT_PRIVACY_RESPONSE,
  LEGAL_ACCEPT_EULA_RESPONSE,
  PHONE_OTP_SEND_SUCCESS,
  PHONE_OTP_CONFIRM_SUCCESS,
  PHONE_OTP_CONFIRM_WRONG_CODE,
  STRIPE_SUBSCRIPTION_PAYMENT_INTENT,
  SUBSCRIPTION_TIERS_LIST,
  SUBSCRIPTION_TIERS_LIST_CHARTER,
  SUBSCRIPTION_CONFIRM_SUCCESS,
} from "../../features/onboarding/mocks/onboardingFixtures";

const SIGNUP_API = "/api/v1/signup";
const TIERS_API = "/api/v1/subscription-tiers";
const TENANTS_API = "/api/v1/tenants";

// Mutable in-process state to simulate state machine progression
let currentSignupState = "step1_account";
// Track which legal docs have been accepted (RULE 7: immutable once set)
const legalAccepted = new Set<string>();
// SIGNUP-C: track the owner's SMS consent status for /state polling.
// Set to "opted_in" by the test harness to simulate the YES webhook reply.
let smsConsentStatus: string | null = null;
// The user_endpoint_id returned by POST /phone/consent (reused by send-optin).
let lastUserEndpointId: string | null = null;
// Resend cooldown timestamp (ms) to simulate 429 on rapid re-submit.
let lastOptinSentAt = 0;
const OPTIN_COOLDOWN_MS = 5000;

/**
 * Test helper: sets the simulated SMS consent status returned by /state.
 * Call `setSmsConsentStatus("opted_in")` to simulate the YES webhook reply.
 * Call `setSmsConsentStatus(null)` to reset between tests.
 */
export function setSmsConsentStatus(status: string | null): void {
  smsConsentStatus = status;
}

export const signupHandlers = [
  // ─── Step 1: Account Creation (PUBLIC — no JWT) ────────────────────────

  http.post(`${SIGNUP_API}`, async ({ request }) => {
    const body = (await request.json()) as { owner_email?: string };

    // Duplicate email simulation
    if (body.owner_email === "duplicate@example.com") {
      return HttpResponse.json(SIGNUP_DUPLICATE_EMAIL_ERROR, { status: 409 });
    }

    // Reset state machine for new signup
    currentSignupState = "step1_account";
    legalAccepted.clear();

    return HttpResponse.json(SIGNUP_INITIATE_SUCCESS, { status: 201 });
  }),

  // ─── Signup State (Resumability) ────────────────────────────────────────

  http.get(`${SIGNUP_API}/:tenantId/state`, ({ params }) => {
    const { tenantId } = params as { tenantId: string };

    // C-B5: Charter-mode tenant IDs return Charter signup state fixtures.
    // These are used by tests for the Charter wizard flow + dashboard badge.
    if (tenantId === "tenant-charter-step5") {
      return HttpResponse.json(SIGNUP_STATE_STEP5_CHARTER);
    }
    if (tenantId === "tenant-charter-complete") {
      return HttpResponse.json(SIGNUP_STATE_COMPLETE_CHARTER);
    }

    const stateMap: Record<string, object> = {
      step1_account: SIGNUP_STATE_STEP1,
      step2_legal: SIGNUP_STATE_STEP2,
      step3_phone: SIGNUP_STATE_STEP3,
      step4_tier: SIGNUP_STATE_STEP4,
      step5_confirm: SIGNUP_STATE_STEP5_TRIAL,
      complete: SIGNUP_STATE_COMPLETE,
    };

    // 404 for unknown tenants (wizard resume: session expired)
    if (tenantId === "tenant-not-found") {
      return HttpResponse.json({ detail: "Tenant not found" }, { status: 404 });
    }

    const base = stateMap[currentSignupState] ?? SIGNUP_STATE_STEP1;
    // SIGNUP-C: merge sms_consent_status into collected_data for /state polling.
    // The test harness sets smsConsentStatus to "opted_in" to simulate the YES.
    if (smsConsentStatus !== null) {
      return HttpResponse.json({
        ...base,
        collected_data: {
          ...(base as { collected_data?: Record<string, unknown> })
            .collected_data,
          sms_consent_status: smsConsentStatus,
        },
      });
    }
    return HttpResponse.json(base);
  }),

  // ─── Step 2: Legal Advance ───────────────────────────────────────────────
  // SIGNUP-GA-B1: single-step transition mirroring backend VALID_STATE_TRANSITIONS
  // (step1_account → step2_legal). Previously double-jumped to step3_phone,
  // which masked the off-by-one page-guard bug.

  http.put(`${SIGNUP_API}/:tenantId/step2`, () => {
    currentSignupState = "step2_legal";
    return HttpResponse.json({
      tenant_id: SIGNUP_STATE_STEP1.tenant_id,
      signup_state: "step2_legal",
      next_step: "phone",
    });
  }),

  // ─── Step 3: Phone Advance ───────────────────────────────────────────────
  // SIGNUP-C: phone is REQUIRED (phone_skipped removed). Accepts the new
  // { phone_number, sms_consent } shape. Backward-compatible with the old
  // { phone_verified, phone_skipped } shape for the SIGNUP-GA-B1 regression.

  http.put(`${SIGNUP_API}/:tenantId/step3`, async ({ request }) => {
    const body = (await request.json()) as {
      phone_number?: string;
      sms_consent?: boolean;
      phone_verified?: boolean;
      phone_skipped?: boolean;
    };
    currentSignupState = "step3_phone";
    return HttpResponse.json({
      tenant_id: SIGNUP_STATE_STEP1.tenant_id,
      signup_state: "step3_phone",
      next_step: "plan",
      ...(body.phone_number !== undefined && {
        phone_number: body.phone_number,
      }),
      ...(body.sms_consent !== undefined && {
        sms_consent: body.sms_consent,
      }),
      ...(body.phone_verified !== undefined && {
        phone_verified: body.phone_verified,
      }),
      ...(body.phone_skipped !== undefined && {
        phone_skipped: body.phone_skipped,
      }),
    });
  }),

  // ─── Step 4: Tier Selection Advance ─────────────────────────────────────
  // SIGNUP-GA-B1: single-step (step3_phone → step4_tier).

  http.put(`${SIGNUP_API}/:tenantId/step4`, async ({ request }) => {
    const body = (await request.json()) as { selected_tier_id?: string };
    currentSignupState = "step4_tier";
    return HttpResponse.json({
      tenant_id: SIGNUP_STATE_STEP1.tenant_id,
      signup_state: "step4_tier",
      next_step: "ready",
      selected_tier_id: body.selected_tier_id,
    });
  }),

  // ─── Step 5: Confirmation Advance ────────────────────────────────────────

  http.put(`${SIGNUP_API}/:tenantId/step5`, () => {
    currentSignupState = "complete";
    return HttpResponse.json({
      tenant_id: SIGNUP_STATE_STEP1.tenant_id,
      signup_state: "complete",
      next_step: null,
    });
  }),

  // ─── Legal Required ──────────────────────────────────────────────────────

  http.get(`${SIGNUP_API}/:tenantId/legal/required`, () => {
    // If all already accepted, return already_accepted:true (RULE 7 support)
    if (
      legalAccepted.has("tos") &&
      legalAccepted.has("privacy") &&
      legalAccepted.has("eula")
    ) {
      return HttpResponse.json({
        required_documents: LEGAL_REQUIRED_RESPONSE.required_documents.map(
          (doc) => ({ ...doc, already_accepted: true }),
        ),
      });
    }
    return HttpResponse.json(LEGAL_REQUIRED_RESPONSE);
  }),

  // ─── Legal Accept (IMMUTABLE — RULE 7) ──────────────────────────────────

  http.post(`${SIGNUP_API}/:tenantId/legal/accept`, async ({ request }) => {
    const body = (await request.json()) as { document_type: string };

    // RULE 7: If already accepted, return 200 with existing acceptance (idempotent)
    if (legalAccepted.has(body.document_type)) {
      const existingMap: Record<string, object> = {
        tos: LEGAL_ACCEPT_TOS_RESPONSE,
        privacy: LEGAL_ACCEPT_PRIVACY_RESPONSE,
        eula: LEGAL_ACCEPT_EULA_RESPONSE,
      };
      return HttpResponse.json(
        existingMap[body.document_type] ?? LEGAL_ACCEPT_TOS_RESPONSE,
        { status: 200 },
      );
    }

    // First acceptance — record it
    legalAccepted.add(body.document_type);

    const responseMap: Record<string, object> = {
      tos: LEGAL_ACCEPT_TOS_RESPONSE,
      privacy: LEGAL_ACCEPT_PRIVACY_RESPONSE,
      eula: LEGAL_ACCEPT_EULA_RESPONSE,
    };

    return HttpResponse.json(
      responseMap[body.document_type] ?? LEGAL_ACCEPT_TOS_RESPONSE,
      { status: 201 },
    );
  }),

  // ─── Phone OTP Send ──────────────────────────────────────────────────────

  http.post(`${SIGNUP_API}/:tenantId/phone/send-otp`, async ({ request }) => {
    const body = (await request.json()) as { phone_number?: string };

    // Simulate OTP delivery failure for invalid-looking numbers
    if (body.phone_number === "+10000000000") {
      return HttpResponse.json(
        { detail: "Couldn't deliver code. Check your number or try again." },
        { status: 422 },
      );
    }

    return HttpResponse.json(PHONE_OTP_SEND_SUCCESS);
  }),

  // ─── Phone OTP Confirm ───────────────────────────────────────────────────

  http.post(
    `${SIGNUP_API}/:tenantId/phone/confirm-otp`,
    async ({ request }) => {
      const body = (await request.json()) as { code: string };

      // Wrong code simulation
      if (body.code !== "123456") {
        return HttpResponse.json(PHONE_OTP_CONFIRM_WRONG_CODE, { status: 400 });
      }

      return HttpResponse.json(PHONE_OTP_CONFIRM_SUCCESS);
    },
  ),

  // ─── Phone Consent (SIGNUP-C) ─────────────────────────────────────────────
  // POST /api/v1/signup/:tenantId/phone/consent
  // Records the owner's mobile + SMS-alerts consent + disclosure hash.
  // Returns { user_endpoint_id, verification_status: "pending" }.

  http.post(`${SIGNUP_API}/:tenantId/phone/consent`, async ({ request }) => {
    const body = (await request.json()) as {
      phone_number?: string;
      sms_consent?: boolean;
      disclosure_hash?: string;
    };

    // 422 if phone_number missing/invalid
    if (!body.phone_number || !/^\+?[1-9]\d{6,14}$/.test(body.phone_number)) {
      return HttpResponse.json(
        { detail: "Invalid phone number" },
        { status: 422 },
      );
    }

    // Generate a stable user_endpoint_id for this consent record.
    lastUserEndpointId = "ue-test-00000000-0000-0000-0000-000000000001";

    return HttpResponse.json(
      {
        user_endpoint_id: lastUserEndpointId,
        verification_status: "pending",
      },
      { status: 201 },
    );
  }),

  // ─── Send Opt-In (SIGNUP-C) ───────────────────────────────────────────────
  // POST /api/v1/signup/:tenantId/phone/send-optin
  // Triggers the platform double-opt-in SMS. Returns { status: "sent" }.
  // 429 if called within the cooldown window (resend throttle).

  http.post(`${SIGNUP_API}/:tenantId/phone/send-optin`, async ({ request }) => {
    const body = (await request.json()) as { user_endpoint_id?: string };

    // 422 if no user_endpoint_id
    if (!body.user_endpoint_id) {
      return HttpResponse.json(
        { detail: "user_endpoint_id is required" },
        { status: 422 },
      );
    }

    // 429 resend cooldown
    const now = Date.now();
    if (now - lastOptinSentAt < OPTIN_COOLDOWN_MS) {
      return HttpResponse.json(
        { detail: "Too many requests. Wait before resending." },
        { status: 429 },
      );
    }
    lastOptinSentAt = now;

    return HttpResponse.json({ status: "sent" });
  }),

  // ─── Subscription Tiers ──────────────────────────────────────────────────
  // C-B5: Charter-mode returns only the Charter tier (is_active=true).
  // The default returns 4 fixture tiers from an early pricing draft (trial, starter,
  // professional, enterprise); the shipped tiers are starter, teams and charter.

  http.get(TIERS_API, ({ request }) => {
    const url = new URL(request.url);
    const charterMode = url.searchParams.get("charter") === "true";
    if (charterMode) {
      return HttpResponse.json(SUBSCRIPTION_TIERS_LIST_CHARTER);
    }
    return HttpResponse.json(SUBSCRIPTION_TIERS_LIST);
  }),

  // ─── Stripe Payment Intent (test mode) ───────────────────────────────────

  http.post(`${SIGNUP_API}/:tenantId/payment-intent`, () => {
    return HttpResponse.json(STRIPE_SUBSCRIPTION_PAYMENT_INTENT);
  }),

  // ─── Trial-to-Paid Conversion ─────────────────────────────────────────────

  http.post(
    `${TENANTS_API}/:tenantId/subscription/convert-from-trial`,
    async ({ request }) => {
      const body = (await request.json()) as {
        stripe_payment_method_id?: string;
        selected_tier_id?: string;
      };

      // Simulate decline for test card 4000000000000002
      if (body.stripe_payment_method_id === "pm_card_chargeDeclined") {
        return HttpResponse.json(
          {
            detail: "Your card was declined.",
            code: "card_declined",
            decline_code: "card_declined",
          },
          { status: 402 },
        );
      }

      return HttpResponse.json({
        ...SUBSCRIPTION_CONFIRM_SUCCESS,
        new_tier_id:
          body.selected_tier_id ?? SUBSCRIPTION_CONFIRM_SUCCESS.new_tier_id,
      });
    },
  ),
];
