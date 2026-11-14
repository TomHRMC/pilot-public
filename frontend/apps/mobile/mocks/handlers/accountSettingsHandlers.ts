// MSW handlers for account settings endpoints (MOB-B10)
// Endpoints verified against openapi_schema_map.md:
//   GET/PATCH /api/v1/users/me/profile  (NOT /api/v1/users/me)
//   GET /api/v1/users/me/mfa-status
//   POST /api/v1/users/me/mfa/methods/{method_type}/enroll-start
//   POST /api/v1/users/me/mfa/methods/{method_type}/enroll-confirm
//   POST /api/v1/users/me/mfa/recovery-codes/generate
//
// Mobile handlers use wildcard prefix ("*/api/v1/...") because apiClient.baseURL
// is an absolute LAN IP — relative paths silently miss all requests. (Rule 18)
//
// MFA-WIRE-1 Part C: enroll-start/enroll-confirm handlers match Part A's
// MockCognitoMfaClient code matrix exactly:
//   - enroll-start: TOTP → { secret, qr_code_uri }; SMS → { destination_masked }
//   - enroll-confirm: 000000 → 400 mfa_code_invalid; 999999 → 400 mfa_code_expired;
//     any other 6-digit code → 201 { method_id, enrolled_at }
import { http, HttpResponse } from "msw";

const MOCK_PROFILE = {
  id: "00000000-0000-0000-0000-000000000001",
  first_name: "Tom",
  last_name: "Owner",
  email: "dev@pilot.local",
  phone_number: "+13035550001",
  time_zone: "America/Denver",
  profile_photo_s3_key: null,
  language_preference: "en",
};

const MOCK_MFA_STATUS = {
  enrolled_methods: [] as string[],
  tenant_policy_required: false,
  grace_period_active: false,
  grace_ends_at: null,
  enforcement_activated: false,
};

const MOCK_RECOVERY_CODES = {
  codes: [
    "ABCD-1234",
    "EFGH-5678",
    "IJKL-9012",
    "MNOP-3456",
    "QRST-7890",
    "UVWX-1234",
    "YZAB-5678",
    "CDEF-9012",
  ],
  set_id: "rc-set-0001",
};

export const accountSettingsHandlers = [
  http.get("*/api/v1/users/me/profile", () => HttpResponse.json(MOCK_PROFILE)),
  http.patch("*/api/v1/users/me/profile", async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ ...MOCK_PROFILE, ...body });
  }),
  http.get("*/api/v1/users/me/mfa-status", () =>
    HttpResponse.json(MOCK_MFA_STATUS),
  ),

  // ── enroll-start (MFA-WIRE-1 Part C — STEP 6) ──────────────────────────────
  http.post(
    "*/api/v1/users/me/mfa/methods/:methodType/enroll-start",
    ({ params }) => {
      const methodType = params.methodType as string;

      if (methodType === "totp") {
        return HttpResponse.json({
          method_type: "totp",
          qr_code_uri:
            "otpauth://totp/PilotForTrades:dev@pilot.local?secret=JBSWY3DPEHPK3PXP&issuer=PilotForTrades",
          secret: "JBSWY3DPEHPK3PXP",
        });
      }

      if (methodType === "sms") {
        return HttpResponse.json({
          method_type: "sms",
          destination_masked: "•••0001",
        });
      }

      // email — not available on the pool (design §G-Q2)
      return HttpResponse.json(
        {
          code: "email_mfa_not_available",
          detail: "Email MFA is not available.",
        },
        { status: 400 },
      );
    },
  ),

  // ── enroll-confirm (MFA-WIRE-1 Part C — STEP 6) ────────────────────────────
  // Code matrix matches Part A's MockCognitoMfaClient exactly:
  //   000000 → 400 mfa_code_invalid
  //   999999 → 400 mfa_code_expired
  //   any other 6-digit → 201 success
  http.post(
    "*/api/v1/users/me/mfa/methods/:methodType/enroll-confirm",
    async ({ request, params }) => {
      const methodType = params.methodType as string;
      const body = (await request.json()) as { code?: string };
      const code = body.code ?? "";

      if (code === "000000") {
        return HttpResponse.json(
          { code: "mfa_code_invalid", detail: "That code didn't match." },
          { status: 400 },
        );
      }

      if (code === "999999") {
        return HttpResponse.json(
          { code: "mfa_code_expired", detail: "That code has expired." },
          { status: 400 },
        );
      }

      return HttpResponse.json(
        {
          method_id: `${methodType}-method-0001`,
          enrolled_at: new Date().toISOString(),
        },
        { status: 201 },
      );
    },
  ),

  // ── recovery-codes/generate (MFA-WIRE-1 Part C — complete step) ────────────
  http.post("*/api/v1/users/me/mfa/recovery-codes/generate", () =>
    HttpResponse.json(MOCK_RECOVERY_CODES, { status: 201 }),
  ),
];
