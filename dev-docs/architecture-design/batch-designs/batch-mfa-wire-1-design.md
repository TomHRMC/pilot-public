# Batch MFA-WIRE-1 — MFA Backend Cognito Wiring + Web/Mobile Enrollment Activation: Design

**Version**: 1.2
**Date**: August 17, 2026
**Author**: Pilot Architect
**Status**: ✅ APPROVED 2026-08-16 (design gate — Tom); DevOps + Python prompts authored 2026-08-16, ready to run
**Changelog**: v1.2 — SNS origination strategy recorded per ADR-0015: **AWS toll-free + toll-free verification (2FA/OTP)** is the primary path; Cognito Custom SMS Sender → Telnyx recorded as the contingency escape hatch (§G-Q12); cost-delta line gains the ~$2/mo TFN lease. v1.1 — Tom-reported pre-existing DevOps gap incorporated: **Cognito pool has no `SmsConfiguration`** (no SNS IAM role for SMS delivery) → new gating DevOps pre-flight (§C Step 0), new error mapping `sms_delivery_not_configured` (§F.3), §0 row 9, §G-Q11. v1.0 — initial draft.
**Batch card**: `pilot-launch-plan.md` §2.3 MFA-WIRE-1
**Owners**: DevOps (Step 0 pre-flight — Cognito `SmsConfiguration`) + Python Engineer (Part A — backend) → React Engineer (Part B — web) → React Native Engineer (Part C — mobile)
**Estimate**: Part A 4–5h · Part B 2–3h · Part C 3–4h
**Cost delta**: **~$2/mo** — no new AWS service; Cognito user-pool MFA is inside the existing pool (free MAU tier at 100 users); MFA SMS rides Cognito→SNS (Pathway A, Pilot fixed cost, ~$0.00645/msg — negligible at beta volume) + **~$2/mo US toll-free origination lease** (ADR-0015, added 2026-08-17; flagged for Founder per infrastructure-constraints §1 — inside the $888 guardrail with buffer intact). ✅

---

## 0. Scope Reconciliation (card vs. code audit)

The launch-plan card says: *"Backend MFA enroll endpoints are mocks… Mobile wizard is a placeholder skeleton with zero API calls."* A full code + live-DB + Cognito-pool audit on 2026-08-16 confirms that and sharpens it:

| # | Card assumption | Audit finding | Design consequence |
|---|---|---|---|
| 1 | enroll-start / enroll-confirm are mocks | ✅ Confirmed — hardcoded TOTP secret `JBSWY3DPEHPK3PXP` (`account_security.py`); any ≥6-char code passes; `cognito_method_id = "mock-cognito-..."` (`:379`) | Replace with real Cognito calls behind a client seam |
| 2 | "Login challenge intercept" is backend work | ❌ **Not needed.** Zero challenge route handlers exist; the `MfaLoginChallenge*` schemas (`account_security.py`) are dead code. Login MFA is **Amplify-native**: once Cognito has an MFA preference for the user, Cognito issues `SOFTWARE_TOKEN_MFA`/`SMS_MFA` challenges at `InitiateAuth` and FE-B2's `AuthProvider.confirmMfaChallenge()` → Amplify `confirmSignIn` already handles them (web + mobile `MfaChallengeStep` exist) | **No backend login-challenge endpoint is built.** Part A deletes the dead schemas. Prod smoke test = "Cognito actually requires MFA at next login" |
| 3 | Web wizard "is fully built and wired" | ⚠️ Partially. It calls the real endpoints but (a) uses raw `fetch` (§8 violation — pre-existing, logged to PLAT-DEBT, not fixed here), (b) sends the **ID token** only (`MFAEnrollmentWizard.tsx`) — Cognito user-scoped MFA APIs (`AssociateSoftwareToken`, `VerifySoftwareToken`, `SetUserMFAPreference`, `GetUserAttributeVerificationCode`, `VerifyUserAttribute`) require the **access token** | Part B adds an `X-Cognito-Access-Token` header to the wizard's MFA calls; backend requires it on the three mutation routes |
| 4 | Three methods: TOTP + SMS + Email | ⚠️ Prod pool `us-east-1_XXXXXXXXX` has **TOTP + SMS factors only** (`aws-cognito-prod-setup.md`; ops §13.2). Cognito email-OTP MFA is not enabled and would require a pool feature/config change (possible Cognito plan cost — Founder decision) | Email enroll-start returns a clean 400 `email_mfa_not_available`; web pages pass `allowedPaths={["totp","sms"]}` (prop already exists; mobile already filters to totp/sms). Email MFA → follow-up decision, §G-Q2 |
| 5 | Mobile wizard is a skeleton | ✅ Confirmed — `handleNext()` advances steps with zero API calls (`mobile/MFAEnrollmentWizard.tsx`) | Part C wires it to the real endpoints (manual-secret TOTP entry — **no new native dep**; QR image stays with MOB-B11, §G-Q4) |
| 6 | — (not on card) | **Delete-method is unreachable from the UI**: `MfaStatusResponse.enrolled_methods` is `list[str]` — no `method_id`s — and the web page renders no Remove affordance; the web page also lacks recovery-code status | Part A extends mfa-status **additively** with a `methods[]` array (keeps `enrolled_methods` for backward compat); Part B adds method cards with Remove |
| 7 | — (not on card) | **Owner reset of user MFA (ops §13.10) does not exist** — no endpoint, and the ECS task role has **no `cognito-idp` IAM grants** (Terraform verified) | **Out of scope → new P2 batch MFA-WIRE-2** (needs Admin API IAM grant + `mfa_reset_by_owner` notification type/template seed — MCP-verified absent). §G-Q3 |
| 8 | — (not on card) | **Dev pool has MFA Disabled** (prod = Optional). Real Cognito enrollment cannot work against the dev pool | Client seam + `MFA_COGNITO_MOCK` env toggle (mirrors the `TELNYX_10DLC_MOCK` precedent); mock is the default outside prod |
| 9 | — (not on card) | ⚠️ **Cognito pool has no `SmsConfiguration` (Tom-reported known issue; design-verified)** — Terraform `modules/security/` contains zero `sms_configuration`/SNS IAM resources; the role `CognitoSNSRole-pilot-production` exists only as console-era setup-doc guidance (`aws-cognito-prod-setup.md` §MFA note) that ops §13.2 elevated to fact. The pool was never console-prompted (Terraform-managed), and the Cognito→SNS path has **never been exercised** (signup uses email codes; SMS-B2 smoke rode Telnyx) | **Gating DevOps pre-flight — §C Step 0.** SMS enrollment OTPs cannot deliver until the pool's `SmsConfiguration` (SNS IAM role, Terraform-managed) + SNS SMS account posture (out of sandbox) land. TOTP path unaffected (nothing is sent). Backend maps Cognito SMS-role failures to a distinct 503 `sms_delivery_not_configured` so an unfinished pre-flight is diagnosable in one read (§F.3) |

**No DB schema changes.** Every table/column this batch touches already exists and was MCP-verified (§A, §B).

---

## A. Input Read Summary

| Input | What it contributed | Status |
|---|---|---|
| `pilot-launch-plan.md` §2.0 row 6, §2.1 Order 3, §2.3 MFA-WIRE-1 card | Batch scope, DoD, owner split | ✅ Read |
| `mvp-prd.md` §3.5 (Multi-Method MFA Enrollment; Tenant-Required MFA Policy + 7-day grace; Owner Reset) | Product requirements | ✅ Read |
| `mvp-arch.md` §4.5 (MFA), §4.6 (refresh TTL), FIND-170 lockout boundary | Architecture contract: Cognito owns lockout; Pilot schema stores enrollment only — **no lockout columns, ever** | ✅ Read |
| `pilot-operations.md` §13.1–§13.13 (full MFA chapter) | Pool config (Optional MFA; TOTP+SMS; SNS role), endpoint contracts, grace machine, **Pathway A: MFA SMS = Cognito→SNS, never Telnyx** | ✅ Read |
| `mfa-integration-approach.md` Findings 0–6 | Historical 10DLC audit — Finding 0 resolved: MFA OTP never rides Telnyx (no 10DLC exposure in this batch) | ✅ Read |
| `pilot-adr-log.md` Decision Index; ADR-0011/0012/0013 | ADR-0011 consequence line explicitly aligns first-login/MFA challenge with MFA-WIRE-1 (Amplify-native); no conflicting ADR | ✅ Read |
| `aws-cognito-prod-setup.md` | Prod pool MFA = Optional, factors = TOTP + SMS; SNS role `CognitoSNSRole-pilot-production` live; Post-Authentication Lambda live (fires **after** MFA — challenge path proven); **dev pool MFA = Disabled** | ✅ Read |
| `pilot-architect-methods.md` §3 (design workflow), §3.9 (designer gate) | This document's structure; Part B/C designer-spec gates | ✅ Read |
| MCP `postgres-local` — columns of `user_mfa_method`, `user_mfa_recovery_code`, `mfa_grace_period_tracking`, `auth_mfa_otp` | All four tables exist with correct columns + all four audit columns per `StandardAuditMixin`/`AppendOnlyMixin` | ✅ Verified |
| MCP `postgres-local` — constraints on the same four tables | `uq_user_mfa_method_tenant_user_type` UNIQUE(tenant_id, user_id, method_type) ✅; PKs/FKs ✅; `auth_mfa_otp_channel_chk` = ('email','sms') | ✅ Verified |
| MCP `postgres-local` — `tenant.mfa_grace_period_started_at`, `user.mfa_enforced`, `user.preferred_mfa_channel`, `user.phone_number` | All exist; `user.phone_number` nullable varchar | ✅ Verified |
| MCP `postgres-local` — `platform_setting` MFA keys | System defaults present (`tenant_mfa_required=false`, `tenant_mfa_grace_period_days=7`, tenant_id NULL) | ✅ Verified |
| MCP `postgres-local` — `notification_type`/`notification_template` for MFA codes | **No `mfa_reset_by_owner` type exists** (only `platform_security_new_device` from PLATFORM-SMS-B2) → owner-reset email needs seed work → MFA-WIRE-2 | ✅ Verified |
| `backend/api/routes/account_security.py` (full file) | Mock impls (lines 289–398); real DB logic for status/delete/recovery/sessions/exports; dead `MfaLoginChallenge*` schemas; RBAC permissions in use: `mfa.enroll_self`, `mfa.reset_self` | ✅ Read |
| `backend/api/routes/settings.py` (`/tenant/mfa-required` GET/PUT) | Tenant policy endpoints already built (B13) — out of scope | ✅ Read |
| `backend/core/auth.py` | JWKS verification; `AuthenticatedUser` context; impersonation pattern | ✅ Read |
| Terraform `modules/security/main.tf` | Only Cognito→Lambda invoke grants; **no `cognito-idp` IAM on any ECS role** | ✅ Read |
| Web: `mfa/page.tsx`, `web/MFAEnrollmentWizard.tsx`, `AuthProvider.tsx`, `MfaChallengeStep.tsx`, `shared-api/client.ts` | FE contract lock; ID-token discovery; Amplify-native challenge confirmation | ✅ Read |
| Mobile: `mobile/MFAEnrollmentWizard.tsx` (skeleton) | Part C starting state | ✅ Read |

---

## B. Migration Plan

**No Alembic migration. No schema change. No seed rollout (no DB data added or modified).** §11.5 is satisfied by this explicit statement.

Pre-migration verification = the MCP result set recorded in §A (run 2026-08-16): all four MFA tables, tenant/user MFA columns, policy `platform_setting` keys, and the UNIQUE constraint all exist and match the models. The Python Engineer re-runs these two queries as prompt Pre-Work (drift guard):

```sql
SELECT table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema='public'
  AND table_name IN ('user_mfa_method','user_mfa_recovery_code','mfa_grace_period_tracking')
ORDER BY table_name, ordinal_position;

SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE connamespace='public'::regnamespace
  AND conrelid='public.user_mfa_method'::regclass;
```

**Environment/config change instead of a migration** (tracked in `aws-env-mgmt-ops-plan.md` — Architect updates it in the same change per §10.8):

| Var | dev/local | QA | prod | Purpose |
|---|---|---|---|---|
| `MFA_COGNITO_MOCK` | `true` (default) | `true` | **`false`** | Mock↔real Cognito MFA client toggle (precedent: `TELNYX_10DLC_MOCK`). Prod task-def env var set by DevOps at deploy; absence defaults to mock (fail-safe = never silently "real" in dev) |
| `COGNITO_REGION` / `COGNITO_USER_POOL_ID` | already present | already present | already present | Reused — no change |

---

## C. Execution Order

| # | Step | Owner | Gate |
|---|---|---|---|
| 0 | **DevOps pre-flight — Cognito `SmsConfiguration`** (blocks only the SMS path): (a) `aws cognito-idp describe-user-pool` → inspect `SmsConfiguration.SnsCallerArn`; (b) if absent — Terraform on `aws_cognito_user_pool.prod`: `sms_configuration { external_id, sns_caller_arn = aws_iam_role.cognito_sns.arn }` + new `aws_iam_role.cognito_sns` (trust `cognito-idp.amazonaws.com`; least-privilege `sns:Publish`) — **Terraform, not console** (infra guardrail); (c) verify SNS SMS account posture (out of sandbox / spend quota ≥ $5/mo — sandboxed SNS silently drops OTPs); (d) smoke: trigger one real Cognito SMS OTP to Tom's phone. ~1h | DevOps Engineer | Runs in parallel with Part A; **gates the §DoD SMS smoke (Step 7) only** — TOTP is independently shippable |
| 1 | **Part A — backend** (this doc §D/§F). Includes OpenAPI regen + commit (handoff signal) | Python Engineer | None — starts immediately on Tom's design approval |
| 2 | `pnpm sync-api-types` | React + RN Engineers | After Part A merges |
| 3 | **Web UI design spec** — method cards + Remove flow + `allowedPaths` change on the two MFA pages → `batch-mfa-wire-1-web-ui-design-spec.md` | `pilot-web-ui-designer` | May run in parallel with Part A; **Tom approval gates Part B** (Rule 1.5) |
| 4 | **Mobile UI design spec** — mobile wizard setup/verify/recovery step content → `batch-mfa-wire-1-mobile-ui-design-spec.md` | `pilot-voice-ui-designer` | May run in parallel with Part A; **Tom approval gates Part C** |
| 5 | **Part B — web** (§D.4 consumer + wizard access-token header + method cards) | React Engineer | Part A merged + spec approved |
| 6 | **Part C — mobile** (wizard flesh to real APIs, manual-secret TOTP) | RN Engineer | Part A merged + spec approved; no new native deps (Rule 9.8 — none requested) |
| 7 | **Prod smoke verification** (Tom): enroll TOTP on web → sign out → sign in → Cognito TOTP challenge → JWT issued; repeat SMS; owner toggles tenant policy → unenrolled test user force-flows | Tom (+ engineer on call) | After Parts A+B deploy |
| 8 | Plan bookkeeping: Appendix A rows, §2.0 flips, ops §13.13 status refresh (Python Engineer appends at close per RACI) | Python Engr + Architect | At batch close |

---

## D. API Endpoint Changes

**No new route paths.** All changes land on existing B13 routes under `/api/v1/users`. RBAC unchanged (`mfa.enroll_self` / `mfa.reset_self`).

### D.1 — `POST /me/mfa/methods/{method_type}/enroll-start` (rewired)

| | |
|---|---|
| Auth | Cognito JWT (ID token, as today) **+ new required header `X-Cognito-Access-Token`** |
| RBAC | `mfa.enroll_self` |
| `method_type=totp` | Backend: `AssociateSoftwareToken(AccessToken)` → `SecretCode`; builds `otpauth://totp/PilotForTrades:{user_email}?secret=…&issuer=PilotForTrades`. Response unchanged: `{ method_type, qr_code_uri, secret }` (real secret now) |
| `method_type=sms` | 400 `phone_number_required` if `user.phone_number` NULL; normalize to E.164 (US default `+1`) else 400 `phone_number_invalid`. Then `SetUserAttributes(phone_number)` → `GetUserAttributeVerificationCode(AttributeName="phone_number")` → Cognito/SNS sends OTP. Response: `{ method_type, destination_masked }` (mask from Cognito `DeliveryDetails` + our last-4) |
| `method_type=email` | **400 `email_mfa_not_available`** (RFC 7807; pool has no email factor — §G-Q2) |
| Re-enrollment | Calling enroll-start for an already-enrolled type re-associates (TOTP: new secret supersedes; SMS: resends code) — supports the wizard's "resend" path |
| Errors | 400 `mfa_access_token_required` (header missing) · 400 invalid method · 502 `cognito_unavailable` (upstream failure; **nothing is written**) |

### D.2 — `POST /me/mfa/methods/{method_type}/enroll-confirm` (rewired — the anti-mock guarantee)

| | |
|---|---|
| Auth | JWT + `X-Cognito-Access-Token` |
| TOTP | `VerifySoftwareToken(AccessToken, UserCode=code)` → on success `SetUserMFAPreference(SoftwareTokenMfaSettings={Enabled:true, PreferredMfa:<first-method?>})` → **only then** upsert `user_mfa_method` (`cognito_method_id="totp:software-token"`, `verification_status="verified"`) + grace-tracking `enrolled_at` (existing behavior) → 201 `{ method_id, enrolled_at }` |
| SMS | `VerifyUserAttribute(AttributeName="phone_number", Code=code)` → `SetUserMFAPreference(SMSMfaSettings={Enabled:true, …})` → upsert row (`cognito_method_id="sms:phone_number"`, `metadata={"destination_last4":"1234"}`) → 201 |
| Replay matrix | No row + verify success → 201. No row + verify fail → 400. Existing verified row + Cognito factor already enabled → **200 with existing `method_id`** (idempotent replay — safe for mobile retry/double-tap). Wrong/expired code → 400 `mfa_code_invalid` / `mfa_code_expired` (mapped from `CodeMismatchException` / `ExpiredCodeException`) |
| Failure invariant | **A Cognito failure ⇒ zero DB writes** (this is the regression test that kills the mock forever) |

### D.3 — `DELETE /me/mfa/methods/{method_id}` (wired; contract unchanged)

Lookup row (tenant+user scoped, as today) → 404 if absent → existing 409 `last_method_required` guard when `tenant_mfa_required` → `SetUserMFAPreference` disabling that factor (TOTP: `SoftwareTokenMfaSettings={Enabled:false}`; SMS: `SMSMfaSettings={Enabled:false}`) → if another method remains, set it `PreferredMfa:true` → delete row → 204. Cognito failure → 502, row **retained** (never strand a Cognito factor without a DB row). Requires `X-Cognito-Access-Token`.

### D.4 — `GET /me/mfa-status` (additive response extension — drives the new web Remove UI)

```jsonc
{
  "enrolled_methods": ["totp"],          // KEPT (deprecated) — mobile useMfaStatus consumes it
  "methods": [                            // NEW
    { "method_id": "uuid", "method_type": "totp",
      "enrolled_at": "…", "last_used_at": null,
      "destination_masked": null }
  ],
  "tenant_policy_required": false, "grace_period_active": false,
  "grace_ends_at": null, "enforcement_activated": false
}
```

`last_used_at` stays null this batch (Cognito owns challenge telemetry); field ships now so the UI contract is complete. **OpenAPI regen required** (response schema change) → `python export_openapi_json.py` + commit = Part A handoff signal.

### D.5 — Cleanup

Delete dead schemas `MfaLoginChallengeInitiateResponse`, `MfaLoginChallengeVerifyRequest`, `MfaLoginChallengeVerifyResponse` (`account_security.py`) — no route ever used them; login challenge is Amplify-native (§0-2). No OpenAPI impact (schemas unreferenced).

---

## E. Pattern Reuse Decisions (mvp-arch §16)

| Pattern | Applies? | How |
|---|---|---|
| **System-default / tenant-override settings** | ✅ consumed (no new UX) | Policy reads stay on `get_effective_setting("tenant_mfa_required"…)` — already wired in B13 code |
| **Optimistic UI** | ✅ Part B only | Method-card Remove: optimistic remove + rollback on non-204, per locked pattern |
| **Idempotency-Key header** | ❌ not required | MFA enrollment is **online-only by nature** (Cognito round-trip; never offline-queued by mobile sync). Replay safety is delivered by the §D.2 replay matrix + UNIQUE(tenant_id, user_id, method_type) natural key instead |
| **409-and-refresh / track-changes / confirm-as-turn / always-preview / four-class severity / mobile escalation / in-flight sync / bilateral conflict** | ❌ | Not enrollment-flow patterns |
| **Fail-loud external-call pattern** (PLATFORM-SMS-B1 precedent) | ✅ | 502 `cognito_unavailable` with zero DB writes; never swallow Cognito errors into a fake success |

Security patterns: access token is used **in-memory only** — never logged, never persisted, never returned (asserted by a logging test). FIND-170 respected: no lockout state in Pilot schema.

---

## F. Shared Module Interfaces

### F.1 — New module `backend/services/cognito_mfa_client.py`

```python
class CognitoMfaError(Exception): ...          # base — maps to 502 cognito_unavailable
class MfaAccessTokenInvalidError(CognitoMfaError): ...   # NotAuthorizedException → 401
class MfaCodeMismatchError(CognitoMfaError): ...         # CodeMismatchException → 400 mfa_code_invalid
class MfaCodeExpiredError(CognitoMfaError): ...          # ExpiredCodeException → 400 mfa_code_expired

class CognitoMfaClient(Protocol):
    def associate_software_token(self, access_token: str) -> str: ...
        """→ SecretCode. Raises CognitoMfaError."""
    def verify_software_token(self, access_token: str, user_code: str) -> None: ...
        """Raises MfaCodeMismatchError / MfaCodeExpiredError."""
    def set_phone_number(self, access_token: str, phone_e164: str) -> None: ...
    def send_phone_verification_code(self, access_token: str) -> str: ...
        """GetUserAttributeVerificationCode(phone_number) → masked destination."""
    def verify_phone_number(self, access_token: str, code: str) -> None: ...
    def set_mfa_preference(self, access_token: str, *,
                           totp_enabled: bool | None = None,
                           sms_enabled: bool | None = None,
                           prefer: Literal["totp","sms"] | None = None) -> None: ...

class RealCognitoMfaClient(CognitoMfaClient):
    """boto3 cognito-idp, Config(signature_version=UNSIGNED) — user-scoped calls
    need no IAM creds (verified: ECS task role has zero cognito-idp grants)."""

class MockCognitoMfaClient(CognitoMfaClient):
    """Deterministic for tests/dev: fixed secret; any 6-digit code verifies EXCEPT
    '000000' (mismatch) and '999999' (expired), so both error paths are testable."""

def get_cognito_mfa_client() -> CognitoMfaClient:
    """Mock when settings.MFA_COGNITO_MOCK else Real. Cached singleton."""
```

### F.2 — `backend/core/auth.py` helper

```python
def get_cognito_access_token(request: Request) -> str:
    """Extract X-Cognito-Access-Token header; 400 mfa_access_token_required if absent.
    Never logged."""
```

### F.3 — Exception → RFC 7807 mapping (single helper in `account_security.py`)

| Exception | HTTP | `code` |
|---|---|---|
| missing header | 400 | `mfa_access_token_required` |
| `MfaAccessTokenInvalidError` | 401 | `mfa_access_token_invalid` |
| `MfaCodeMismatchError` | 400 | `mfa_code_invalid` |
| `MfaCodeExpiredError` | 400 | `mfa_code_expired` |
| email path | 400 | `email_mfa_not_available` |
| missing/unparseable phone | 400 | `phone_number_required` / `phone_number_invalid` |
| Cognito SMS-role failures (`InvalidSmsRoleAccessPolicyException`, `InvalidSmsRoleTrustRelationshipException`) | 503 | `sms_delivery_not_configured` — distinct code so an unfinished §C Step 0 pre-flight surfaces as a one-read diagnosis, not a generic 502 |
| `CognitoMfaError` (any other) | 502 | `cognito_unavailable` |

### F.4 — E.164 phone normalization helper

`normalize_phone_e164(raw: str) -> str` — strips formatting; 10 digits → `+1` prefix; already-`+` passthrough; else raise → 400 `phone_number_invalid`.

### F.5 — Tests (Part A; domain folder `backend/tests/batch_mfa_wire_1/`)

Rewrite of mock-encoding B13 tests: `tests/batch_b13/test_a69_mfa_enrollment.py` currently asserts **any ≥6-char code passes** — must be reworked onto `MockCognitoMfaClient` semantics (the mock is injected into `/test` twins via `get_test_context` path + default-mock setting). New: client-seam unit tests (Stubber/mocked boto3 for Real client), error-mapping tests for every §F.3 row, replay-matrix tests, mfa-status `methods[]` shape test, delete-wiring test (preference disable + last-method 409), **no-DB-write-on-Cognito-failure** test, token-not-logged test. Existing status/recovery/session/export tests must keep passing untouched.

No new Celery tasks; `mfa_grace_reminders` untouched.

---

## G. Open Questions Resolved

| # | Question | Resolution |
|---|---|---|
| Q1 | Where does the backend get a Cognito **access token** for user-scoped MFA calls? The FE sends the ID token. | New `X-Cognito-Access-Token` header on the three mutation routes (Part B/C send `session.tokens?.accessToken`). Admin APIs can't substitute — `AssociateSoftwareToken`/`VerifySoftwareToken` have **no Admin variant**. Alternatives rejected: swapping `apiClient` globally to access tokens (blast radius); backend `AdminInitiateAuth` token minting (breaks password custody). |
| Q2 | Email OTP method? | **Deferred.** Pool has TOTP+SMS only; Cognito email-OTP MFA is a pool feature/config change with possible Cognito plan cost → **Founder decision, not this batch**. enroll-start(email) → 400 `email_mfa_not_available`; web pages constrain `allowedPaths` to `["totp","sms"]` (prop exists; no "coming soon" strings per Rule 9.4). If Tom later approves email MFA, it's a small additive batch. |
| Q3 | Owner reset of user MFA (ops §13.10)? | **Out of scope → new P2 batch MFA-WIRE-2.** Requires: ECS task-role `cognito-idp:AdminSetUserMFAPreference` IAM grant (Terraform — DevOps), new `mfa_reset_by_owner` notification type + email template seed (MCP-verified absent), new `mfa.reset_other` RBAC key, audit event. Too much surface for this batch (Rule 9.6); escape hatch isn't needed until real users enroll — but it must land before Charter beta → added to plan §2.4. |
| Q4 | MOB-B11 overlap (mobile wizard flesh-out)? | **Split cleanly**: MFA-WIRE-1 Part C wires the skeleton to real APIs with **manual-secret TOTP entry** (copyable secret + otpauth URI) — zero new native deps. MOB-B11 keeps only the QR-image rendering (`react-native-qrcode-svg`, needs Rule 9.8 approval) as P2 polish; it shrinks accordingly. |
| Q5 | Backend login-challenge endpoints (ops §13.5's "backend calls RespondToAuthChallenge")? | **Not built — Amplify-native is the as-built architecture** (FE-B2 `confirmMfaChallenge` → `confirmSignIn`, web+mobile). Dead B13 schemas deleted (§D.5). Ops §13.5 narrative gets a doc correction at batch close (Architect verifies). |
| Q6 | Dev pool has MFA disabled — how do dev/QA test? | `MFA_COGNITO_MOCK=true` everywhere except prod (§B). Dev-pool MFA enablement is **not** requested (avoids SNS spend + churn); prod is the real-wiring verification env (Step 7 smoke). |
| Q7 | Web wizard uses raw `fetch` (§8 violation)? | Pre-existing FE-B12 code; works; converting to `apiClient` needs custom-header support. → **PLAT-DEBT item**, not this batch (Part B only *extends* the existing helper with the access-token header). |
| Q8 | TOTP `cognito_method_id` semantics (Cognito issues no per-method ID)? | Deterministic identifiers: `"totp:software-token"`, `"sms:phone_number"`. Human detail (last-4) in `metadata`. UNIQUE(tenant,user,type) already prevents duplicates. |
| Q9 | Does enabling MFA preference change the Post-Authentication Lambda (PLATFORM-SMS-B2)? | No — it fires post-authentication regardless; MFA challenge precedes it. No interaction. |
| Q10 | `user.mfa_enforced` / `preferred_mfa_channel` columns? | Legacy platform-user guard (`user_platform_mfa_required_chk`) + default channel hint; enrollment does not write them this batch (platform-staff MFA is an ops/INFRA-H1 concern). Noted to avoid engineer confusion. |
| Q11 | **Cognito `SmsConfiguration` missing** (Tom-reported known issue) — doesn't this block the SMS path? | Yes for delivery, no for the batch: §C Step 0 (DevOps pre-flight, ~1h, Terraform-managed role + `sms_configuration` + SNS sandbox check) runs in parallel with Part A and gates only the SMS smoke. Engineering is never blocked (mock seam covers dev/test); TOTP ships independently. Ops §13.2's claim that the SNS role exists is **doc drift** — the ops-doc correction lands at batch close alongside §13.13 (Architect verifies). |
| Q12 | SNS origination strategy for the SMS path (the post-Step 0 blocker: sandboxed account, zero origination numbers, $1 spend cap)? | **Decided 2026-08-17 — ADR-0015: AWS toll-free origination + toll-free verification (2FA/OTP use case)** via the single SNS-production-access Support case (sandbox exit + TFN + `MonthlySpendLimit`=$25). No 10DLC brand/campaign in AWS at OTP-only volume; affirms ADR-0013 Pathway A (MFA OTP = Cognito→SNS, never Telnyx; the Telnyx campaign cannot be imported into AWS — 10DLC registrations bind to the registering connectivity provider). **Contingency**: if the Support case drags >~1 week or is rejected, the designed escape hatch is a **Cognito Custom SMS Sender Lambda → Telnyx** mini-batch (Lambda + KMS decrypt + Terraform + tests; would need a `CXXXXXX` TCR use-case amendment for OTP/2FA and a superseding ADR — it revisits the ADR-0013 pathway boundary). Step 0 Terraform (`sms_configuration` + SNS role) is the production plumbing under the primary path — nothing stranded. |

---

## H. Surface Mockup Reference (Part B web + Part C mobile)

| Surface | Platform | Change | §16 patterns consumed | Designer spec (gate) |
|---|---|---|---|---|
| `/settings/my-account/security/mfa` | web | Method cards (type label, destination, enrolled date, **Remove** w/ confirm + 409 toast); `allowedPaths=["totp","sms"]`; consumes new `methods[]` | optimistic UI (Remove) | `batch-mfa-wire-1-web-ui-design-spec.md` — `pilot-web-ui-designer` — **required, Tom-approved** |
| `/settings/my-account/security/mfa/enroll` (force-flow) | web | Same `allowedPaths` constraint | — | same spec |
| Mobile MFA screen `/(home)/settings/my-account/security/mfa` | mobile | Skeleton steps fleshed: setup-totp (manual secret + copy), setup-sms (masked dest + resend), verify (6-digit), complete (+ recovery codes) | mobile escalation (existing banner) | `batch-mfa-wire-1-mobile-ui-design-spec.md` — `pilot-voice-ui-designer` — **required, Tom-approved** |

No marketing/public surface. No new top-level UX pattern introduced anywhere (Rule 1.5-2 compliant).

## I. Component Manifest

| Component | Path | Establish/Flesh | Notes |
|---|---|---|---|
| `MFAEnrollmentWizard` (mobile) | `packages/ui/src/mfa-enrollment-wizard/mobile/MFAEnrollmentWizard.tsx` | **Flesh in place** (Part C) — same file, same locked props; internals only | Reconciles with voice-ui designer manifest — no orphans |
| Method-card list | surface-scoped inside the existing web `mfa/page.tsx` (or `apps/web/src/features/account-settings/components/` if the designer splits it) | New (Part B) | **Component-existence check**: no existing shared method-card in `packages/ui/src/index.ts` — surface-scoped, not a new `packages/ui` export |
| Web wizard header helper | `packages/ui/src/mfa-enrollment-wizard/web/MFAEnrollmentWizard.tsx` (local `getAuthHeaders`) | Modify (Part B) | Adds `X-Cognito-Access-Token`; `fetch`→`apiClient` migration stays in PLAT-DEBT (§G-Q7) |

---

## Definition of Done (batch level)

1. Web: user enrolls **TOTP** end-to-end against real Cognito (prod smoke) — QR scans into an authenticator; confirm writes `user_mfa_method` only after `VerifySoftwareToken` succeeds.
2. Web: user enrolls **SMS** end-to-end — real SNS-delivered code to the user's phone; confirm writes only after `VerifyUserAttribute` succeeds. **(Gated on §C Step 0 SmsConfiguration pre-flight; until it lands, SMS enroll-start must fail as 503 `sms_delivery_not_configured`, never a silent mock-looking success.)**
3. **Cognito actually challenges at next login** (sign out/in → `SOFTWARE_TOKEN_MFA`/`SMS_MFA` challenge → FE-B2 `MfaChallengeStep` → JWT).
4. Web: enrolled methods render as cards with Remove; Remove disables the Cognito factor + deletes the row; last-method 409 honored when tenant policy is on.
5. Email path returns clean 400 `email_mfa_not_available`; no email option rendered on web/mobile; **no "coming soon" strings**.
6. Mobile: TOTP (manual secret) + SMS enroll end-to-end via the real endpoints; zero placeholder strings.
7. `MFA_COGNITO_MOCK` default true outside prod; `/test` twins and the full unit suite run entirely on the mock.
8. Failure invariant proven by test: any Cognito error ⇒ zero DB writes.
9. Two-phase verification gate passes (unit-only, then full suite) for each engineer per their prompt.
10. Bookkeeping at close: launch-plan flips + Appendix A; ops §13.13/§13.5 doc corrections (Python Engineer appends; Architect verifies); `aws-env-mgmt-ops-plan.md` env-var row (Architect, same change); MFA-WIRE-2 + MOB-B11 shrinkage rows added to plan (Architect).
