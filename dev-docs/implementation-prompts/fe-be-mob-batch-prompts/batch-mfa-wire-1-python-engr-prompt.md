# Implementation Prompt: MFA-WIRE-1 (Part A) — MFA Backend Cognito Wiring

**Mode**: Pilot Python Engineer
**Batch**: MFA-WIRE-1 (Part A of 3 — backend; Part B web + Part C mobile follow, each gated on a Tom-approved designer spec)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.3 MFA-WIRE-1
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-mfa-wire-1-design.md` ✅ APPROVED 2026-08-16 (v1.1)
**Estimated session**: 4–5 hours
**Platform**: Backend only (`backend/`)
**Frontend companion**: Part B (React Engineer, web) + Part C (React Native Engineer, mobile) — both consume your regenerated `openapi.json` via `pnpm sync-api-types`. Your OpenAPI regen + commit is the handoff signal.
**DevOps companion**: Step 0 (Cognito `SmsConfiguration` pre-flight) runs **in parallel** with this batch under `batch-mfa-wire-1-devops-prompt.md`. You do not wait for it; it gates only the production SMS smoke, not any code or test in this prompt.

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document; the 25 hard rules are non-negotiable STOPs
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §8 (Router Design), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; governs all test file structure, domain markers, and fixture rules
- **The design doc** (linked above) — §0 (nine audit findings), §D (endpoint contracts), §F (module interfaces), §G (open questions Q1–Q11). It is the authority for this batch; this prompt paraphrases it but never overrides it.

Critical rules for this batch:

- **Rule 1**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every name before use. If MCP returns an error → **STOP and ask Tom**.
- **Rule 3**: After any endpoint change → run `python export_openapi_json.py` (updates both `openapi.json` and `openapi_schema_map.md`). This batch changes the `mfa-status` response schema — regen is **required** and is the FE handoff signal.
- **Rule 5**: Never use module-level `TestClient` in any test file. Always use the `client` fixture from `conftest.py`.
- **Rule 6**: `db.get()` is permanently banned on tenant-scoped models. Always use tenant-scoped `select()` with an explicit `WHERE tenant_id = :tid` clause.
- **Rule 7**: The `postgres-local` MCP is for **read-only verification only**. Never use it to INSERT, UPDATE, or DELETE data — all data changes go through the application code.
- **Rule 8**: All API error responses MUST follow RFC 7807 Problem Details format. Non-standard error shapes break the frontend `<NotificationBanner>` severity routing.
- **Rule 9**: Every mutation endpoint MUST call `set_audit_context_sync(db, user_id=user.id)` before committing. The existing enroll-confirm / delete impls already do this — preserve it.
- **Rule 11**: If ANY test fails during your work — even one that appears pre-existing — you must fix it before declaring the batch done. **Expect the B13 mock-era MFA tests to fail after your rewiring; reworking them is Task 9, in scope, not "pre-existing breakage."**
- **Rule 12 (sync routes — rules §21)**: This app is **synchronous by design**. Every DB-touching route and `_impl()` is a plain `def`. **Never convert a handler that touches the sync `Session` to `async def`.** The Cognito boto3 calls are blocking too — they belong in the same sync handlers (FastAPI threadpools `def` routes). Do not introduce `async def` anywhere in this batch.
- **Rule 13 (Pydantic v2 — rules §22)**: v2 idioms only — `model_config = ConfigDict(...)`, `@field_validator`, `.model_dump()`. Every route needs `response_model`.
- **Rule 14 (Ruff — rules §23)**: Run ruff **only against the files you changed** — see the Phase 2 gate. Fix ALL errors in those files, including pre-existing ones.
- **Rule 16 (verify, don't assume — rules §25)**: 186 tables exist. Query `information_schema.columns` for every table you touch this session before writing SQL — the Pre-Work MCP queries below are mandatory, not advisory.

Batch-specific security rules (from design §E/§F — treat as hard rules):

- **The Cognito access token is use-in-memory-only.** Never log it, never persist it, never return it in any response. Task 9 includes a `caplog` test that proves this.
- **Fail-loud, never fake success.** Any Cognito failure → mapped RFC 7807 error (design §F.3) with **zero DB writes**. The regression test that kills the mock forever is: Cognito error ⇒ no `user_mfa_method` row.
- **Mock is the default everywhere except prod.** `MFA_COGNITO_MOCK` defaults to `True` in code; only the prod task definition sets `false` (design §B). Never flip the code default.
- **No "coming soon" strings** (Rule 9.4 — architect-level). Email MFA returns a clean 400 `email_mfa_not_available`; nothing user-facing hints at email as an option.

---

## Pre-Work: Establish Regression Baseline

Before touching any file, capture the current **unit-only** test baseline:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**.

> **If any tests are already failing before you start**: Do NOT treat them as "pre-existing" and proceed anyway. Either:
> (a) Confirm with Tom that this is a known, accepted failure with a documented reason before proceeding, OR
> (b) Fix the failure before touching any batch files.
>
> You may NOT start implementation work while tests are in an unexplained failed state.

---

## Pre-Work: Run MCP Verification Queries

> **MCP Usage Rule**: The `postgres-local` MCP is for **read-only verification only**. Use it to confirm table names, column types, and existing data. Never use it to INSERT, UPDATE, or DELETE — all data changes go through the application code, seed scripts, or Alembic migrations. If a query fails or returns an error → STOP and ask Tom before proceeding.
>
> **Two read-only MCP servers exist** (global rule `.roo/rules/02-database-mcp-access.md`): **`postgres-local`** is the default for all verification. **`postgres-prod`** reads production but **requires an SSH tunnel that only Tom controls** — ask Tom to confirm the tunnel is up before your first `postgres-prod` query, and STOP on any connection error (the tunnel is down). This batch needs **`postgres-local` only** — no `postgres-prod` queries.

Run **all** of these via `postgres-local` MCP before writing any code. If any query returns unexpected results → **STOP and ask Tom**. Canonical query patterns: `dev-docs/db-design/postgres-mcp-guide.md`.

```sql
-- 1. user_mfa_method columns (you will write rows here — verify every field name you use)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'user_mfa_method'
ORDER BY ordinal_position;
-- Expect (verified 2026-08-16): mfa_method_id uuid PK, tenant_id, user_id, method_type text,
-- enrolled_at, last_used_at (nullable), cognito_method_id text NOT NULL,
-- verification_status text default 'verified', metadata jsonb,
-- created_at, updated_at, created_by, updated_by

-- 2. user_mfa_method constraints (the natural key your replay matrix relies on)
SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE connamespace = 'public'::regnamespace
  AND conrelid = 'public.user_mfa_method'::regclass;
-- Expect: uq_user_mfa_method_tenant_user_type UNIQUE (tenant_id, user_id, method_type)

-- 3. mfa_grace_period_tracking columns (enroll-confirm updates enrolled_at here)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'mfa_grace_period_tracking'
ORDER BY ordinal_position;
-- Expect: PK (tenant_id, user_id), grace_started_at, enrolled_at (nullable), enforcement_activated_at

-- 4. user table MFA/phone columns (SMS enroll-start reads phone_number)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'user'
  AND column_name IN ('phone_number', 'mfa_enforced', 'preferred_mfa_channel')
ORDER BY ordinal_position;
-- Expect: phone_number varchar NULLABLE; mfa_enforced bool default false;
--         preferred_mfa_channel text default 'email' (legacy — NOT written this batch, design §G-Q10)

-- 5. platform_setting MFA policy keys (the delete-guard reads tenant_mfa_required)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'platform_setting'
ORDER BY ordinal_position;
-- Then, using the actual key/value column names returned above:
--   SELECT <key_col>, <value_col> FROM public.platform_setting
--   WHERE tenant_id IS NULL AND <key_col> LIKE 'tenant_mfa%';
-- Expect two system-default rows: tenant_mfa_required=false, tenant_mfa_grace_period_days=7
```

> **Independent column verification (MANDATORY)**: If any column name in this prompt does not match what MCP returns → use the MCP-returned name, not the prompt's name, and note the discrepancy in your Completion Summary. The live DB is the only authoritative source.

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
backend/api/routes/account_security.py          ← THE file you rewire. Mock impls at lines 289–398 (_enroll_start_impl 289–339, hardcoded secret 305–316; _enroll_confirm_impl 342–398, mock id at 379); dead MfaLoginChallenge* schemas 94–105; real logic to preserve: _get_mfa_status_impl ~220–267, _delete_mfa_method_impl 449–490 (409 last-method guard), recovery codes 510–602, /test twins throughout
backend/core/auth.py                            ← AuthenticatedUser + get_current_user; you add get_cognito_access_token() here (Task 2)
backend/core/config.py                          ← settings class; TELNYX_10DLC_MOCK precedent at line ~86; you add MFA_COGNITO_MOCK here (Task 1). COGNITO_REGION / COGNITO_USER_POOL_ID already exist
backend/services/telnyx_sms_carrier.py          ← lines ~85–95: the mock-flag + init-WARNING precedent your client seam mirrors (Task 1)
backend/services/setting_resolver.py            ← get_effective_setting() at line 28 (used by the existing 409 last-method guard — do not change it)
backend/app/models/security.py                  ← UserMfaMethod ORM (imported by account_security.py lines 26–33) — field names must match the MCP query 1 results
backend/tests/batch_b13/test_a69_mfa_enrollment.py ← the mock-encoding tests you rework in Task 9 (currently asserts any ≥6-char code passes; email enroll-start expects 200 — both change)
backend/tests/conftest.py                       ← fixtures: client, db_session, test_tenant, test_user, mock_cognito_jwt, autouse mocks
backend/tests/README-adding-tests.md            ← test file structure, domain markers, fixture rules
```

Also run these greps to find related files:

```bash
grep -rn "MfaLoginChallenge" backend/ --include="*.py"
# Expect: ONLY the three dead schema definitions in account_security.py–105.
# If ANY route/import references them → STOP and ask Tom before deleting (Task 7).

grep -rn "enroll-start\|enroll-confirm" backend/tests/ --include="*.py" -l
# Expect: tests/batch_b13/test_a69_mfa_enrollment.py (and possibly recovery-code siblings) — your Task 9 surface.

grep -rn "get_cognito_mfa_client\|cognito_mfa_client" backend/ --include="*.py"
# Expect: zero results (new module).
```

---

## Background / Context

The web MFA page (`/settings/my-account/security/mfa`) renders, but enrollment is fake end-to-end: the B13 backend is mock code (hardcoded TOTP secret `JBSWY3DPEHPK3PXP`; any ≥6-char code passes; `cognito_method_id = "mock-cognito-..."`). This batch wires the three existing enrollment mutation routes to **real AWS Cognito user-scoped MFA APIs** behind a mock/real client seam, extends `mfa-status` with a `methods[]` array (so the web UI can render method cards with Remove), and deletes dead login-challenge schemas.

Key architectural facts (design §0/§G — do not re-litigate):

1. **Login challenge is Amplify-native.** Once Cognito has an MFA preference for a user, Cognito issues `SOFTWARE_TOKEN_MFA` / `SMS_MFA` challenges at `InitiateAuth` and the frontend's `AuthProvider.confirmMfaChallenge()` → Amplify `confirmSignIn` handles them (FE-B2, web + mobile). **No backend login-challenge endpoint is built, ever.** The `MfaLoginChallenge*` schemas in `account_security.py–105` are dead code you delete (Task 7).
2. **User-scoped Cognito MFA APIs need the user's ACCESS token, not the ID token** the frontend normally sends. `AssociateSoftwareToken` / `VerifySoftwareToken` / `SetUserMFAPreference` / `GetUserAttributeVerificationCode` / `VerifyUserAttribute` have **no Admin variants**. So the three mutation routes gain a required `X-Cognito-Access-Token` header (Parts B/C will send `session.tokens?.accessToken`).
3. **User-scoped Cognito calls need no IAM credentials** — they authenticate via the access token itself. The ECS task role has zero `cognito-idp` grants (Terraform-verified) and stays that way. The real client is built with `Config(signature_version=UNSIGNED)`.
4. **The dev Cognito pool has MFA Disabled** — real enrollment cannot work locally. Hence the `MFA_COGNITO_MOCK` seam (mirrors the `TELNYX_10DLC_MOCK` precedent): mock is the default outside prod, all unit tests and `/test` twins run on the mock.
5. **Prod pool has TOTP + SMS factors only** — email OTP is not available. `enroll-start(email)` → 400 `email_mfa_not_available` (design §G-Q2).
6. **Cognito SMS delivery depends on the DevOps Step 0 pre-flight** (pool `SmsConfiguration` + SNS posture) running in parallel. Until it lands, real SMS enroll-start in prod may fail at Cognito with `InvalidSmsRoleAccessPolicyException` / `InvalidSmsRoleTrustRelationshipException` — you map those to a distinct **503 `sms_delivery_not_configured`** (design §F.3) so an unfinished pre-flight is a one-read diagnosis, never a silent mock-looking success.
7. **No DB schema changes, no migration, no seed data** (design §B). Every table/column you touch already exists (MCP-verified above).

---

## Task 1 — Cognito MFA Client Seam (`services/cognito_mfa_client.py` + settings)

Create `backend/services/cognito_mfa_client.py` implementing design §F.1 exactly:

**1a. Settings** — in `backend/core/config.py`, next to the `TELNYX_10DLC_MOCK` block (~line 86):

```python
# MFA-WIRE-1: Mock↔real Cognito MFA client toggle. DEFAULT TRUE (mock) —
# fail-safe: real Cognito MFA calls happen only where the env explicitly
# sets MFA_COGNITO_MOCK=false (prod task definition). Dev pool has MFA
# disabled, so real enrollment cannot work outside prod (design §G-Q6).
MFA_COGNITO_MOCK: bool = True
```

**1b. Exceptions** (module-level):

```python
class CognitoMfaError(Exception): ...                # base → 502 cognito_unavailable
class MfaAccessTokenInvalidError(CognitoMfaError): ...  # NotAuthorizedException → 401
class MfaCodeMismatchError(CognitoMfaError): ...        # CodeMismatchException → 400 mfa_code_invalid
class MfaCodeExpiredError(CognitoMfaError): ...         # ExpiredCodeException → 400 mfa_code_expired
class MfaSmsRoleNotConfiguredError(CognitoMfaError): ...
    # InvalidSmsRoleAccessPolicyException / InvalidSmsRoleTrustRelationshipException
    # → 503 sms_delivery_not_configured (design §F.3 — unfinished DevOps Step 0 diagnosis)
```

**1c. Protocol + implementations** (signatures per design §F.1 — `associate_software_token`, `verify_software_token`, `set_phone_number`, `send_phone_verification_code`, `verify_phone_number`, `set_mfa_preference(totp_enabled=None, sms_enabled=None, prefer=None)`):

- `RealCognitoMfaClient` — module-level boto3 client:
  ```python
  import boto3
  from botocore import UNSIGNED
  from botocore.config import Config
  from botocore.exceptions import ClientError

  _client = boto3.client(
      "cognito-idp",
      region_name=settings.COGNITO_REGION,
      config=Config(signature_version=UNSIGNED),  # user-scoped calls auth via the token — no IAM creds
  )
  ```
  Call mapping: `associate_software_token(AccessToken=t)` → `resp["SecretCode"]` · `verify_software_token(AccessToken=t, UserCode=code)` → require `Status == "SUCCESS"` else raise `MfaCodeMismatchError` · `set_phone_number` → `update_user_attributes(AccessToken=t, UserAttributes=[{"Name": "phone_number", "Value": e164}])` · `send_phone_verification_code` → `get_user_attribute_verification_code(AccessToken=t, AttributeName="phone_number")` → `resp["CodeDeliveryDetails"]["Destination"]` · `verify_phone_number` → `verify_user_attribute(AccessToken=t, AttributeName="phone_number", Code=code)` · `set_mfa_preference` → `set_user_mfa_preference(AccessToken=t, SoftwareTokenMfaSettings={...}, SMSMfaSettings={...})` (build each settings dict only from non-`None` args; `prefer` maps to `PreferredMfa: True` on that factor's settings).
  Translate `ClientError` by `e.response["Error"]["Code"]` → the Task-1b exceptions (both `InvalidSmsRole*` codes → `MfaSmsRoleNotConfiguredError`; any other code → `CognitoMfaError`). **Never log the access token or include it in exception messages.**
- `MockCognitoMfaClient` — deterministic, in-memory, for dev/tests:
  - `associate_software_token` → fixed base32 secret (e.g. `"MFAW1MOCKSECRETBASE32AAAAAAA"` — valid base32, obviously mock).
  - `verify_software_token` / `verify_phone_number`: any 6-digit code passes **except** `"000000"` → raise `MfaCodeMismatchError` and `"999999"` → raise `MfaCodeExpiredError` (both error paths stay unit-testable without AWS).
  - `set_phone_number` records the E.164 per access-token in an instance dict; `send_phone_verification_code` → `"***-***-" + last4` of the recorded phone (or a fixed mask if none set).
  - `set_mfa_preference` records enabled/preferred factors per token in the instance dict (delete-wiring tests assert against this state).
  - On init, log a WARNING mirroring the Telnyx precedent (`telnyx_sms_carrier.py` ~lines 92–95): `"CognitoMfaClient running with MFA_COGNITO_MOCK=true — no real Cognito MFA calls will be made"`.
- `get_cognito_mfa_client() -> CognitoMfaClient` — returns the cached singleton; mock when `settings.MFA_COGNITO_MOCK` else real. Read the setting **at call time** (not import time) so tests can monkeypatch it; expose a `reset_cognito_mfa_client()` (or use `functools.lru_cache` + `.cache_clear()`) for test isolation.

Intermediate run:

```bash
cd <repo>/backend && source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task 2 — Access-Token Header Helper (`core/auth.py`)

Add to `backend/core/auth.py` (design §F.2):

```python
from fastapi import Request

def get_cognito_access_token(request: Request) -> str:
    """Extract the X-Cognito-Access-Token header required by user-scoped Cognito
    MFA APIs. 400 mfa_access_token_required (RFC 7807) if absent.
    NEVER log this value — it is use-in-memory-only (design §E)."""
```

Behavior: missing/empty header → `HTTPException(400, detail={...RFC 7807 dict..., "code": "mfa_access_token_required"})`. Follow the existing RFC 7807 dict shape used elsewhere in the codebase (see Rule 8 / Task 8). The header name constant: `X-Cognito-Access-Token`.

---

## Task 3 — Rewire `_enroll_start_impl` (account_security.py)

Replace the mock body (lines 289–339). The impl signature gains `access_token: str`:

- **Real routes** (`enroll_start`): add `access_token: str = Depends(get_cognito_access_token)` and pass it through. Auth/RBAC unchanged (`mfa.enroll_self`).
- **`/test` twins**: pass the sentinel literal `"test-mock-access-token"` — they run on the mock client (default setting) and must NOT require the header (keeps the unauthenticated test pattern intact).
- `method_type == "totp"`: `client.associate_software_token(access_token)` → real `SecretCode`; build `otpauth://totp/PilotForTrades:{user_email}?secret={secret}&issuer=PilotForTrades` (look up the user's email with a tenant+user-scoped `select()` — verify the email column via your MCP results / the `User` model; do not assume). Response shape unchanged: `{ method_type, qr_code_uri, secret }`.
- `method_type == "sms"`: load the user's `phone_number` (tenant+user-scoped select); NULL → 400 `phone_number_required`; else normalize with `_normalize_phone_e164()` (Task 4 below — add it in this file as a module-level helper per design §F.4: strip formatting; 10 digits → `+1` prefix; already-`+` passthrough; anything else → raise → 400 `phone_number_invalid`). Then `client.set_phone_number(access_token, e164)` → `client.send_phone_verification_code(access_token)` → response `{ method_type, destination_masked }` (use Cognito's masked `Destination` when real; the mock returns its own mask).
- `method_type == "email"`: **400 `email_mfa_not_available`** immediately (before any client call) — design §G-Q2.
- Invalid method: preserve the existing 400 behavior.
- Re-enrollment on an already-enrolled type is allowed (re-associates / resends) — do not add a guard.
- Missing header on real routes → the Task-2 400. Cognito exceptions → Task-8 mapping (502/503/etc. — **zero DB writes on any failure**).

---

## Task 4 — Rewire `_enroll_confirm_impl` (the anti-mock guarantee)

Replace the mock body (lines 342–398). Design §D.2 contract:

1. **Replay short-circuit first**: tenant+user-scoped select for an existing `verification_status="verified"` row with this `method_type`. If found → idempotently call `client.set_mfa_preference(access_token, <factor>_enabled=True, prefer=...)` (prefer only if this is the user's sole verified method) → return **200** with the existing `method_id` / `enrolled_at`. (Safe mobile double-tap / retry — design §D.2 replay matrix. The UNIQUE(tenant_id, user_id, method_type) constraint you verified in MCP query 2 backs this.)
2. Otherwise verify with Cognito:
   - TOTP: `client.verify_software_token(access_token, code)` → `client.set_mfa_preference(access_token, totp_enabled=True, prefer="totp" if first method)` → **only then** upsert the `user_mfa_method` row (`cognito_method_id="totp:software-token"`, `verification_status="verified"`) + preserve the existing grace-tracking `enrolled_at` update (current lines ~387–396) → **201** `{ method_id, enrolled_at }`.
   - SMS: `client.verify_phone_number(access_token, code)` → `set_mfa_preference(sms_enabled=True, ...)` → upsert (`cognito_method_id="sms:phone_number"`, `metadata={"destination_last4": last4}` — last4 from the phone number you set at enroll-start; re-read the user row) → 201.
3. **Failure invariant**: any exception from the client → Task-8 mapping; **zero DB writes** (no row insert/update, no grace-tracking touch). Preserve `set_audit_context_sync()` ahead of the DB writes exactly as the current code does.
4. Keep the existing `response_model` and route decorators; real routes gain `Depends(get_cognito_access_token)`; `/test` twins pass the sentinel.

Checkpoint run after Tasks 3–4:

```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
# Expect B13 MFA failures at this point — they assert mock behavior. They get reworked in Task 9.
# All OTHER tests must still pass. Investigate anything else before continuing.
```

---

## Task 5 — Wire `_delete_mfa_method_impl` to Cognito

Modify (lines 449–490), keeping the contract and guards intact (design §D.3):

1. Keep: tenant+user-scoped lookup → 404 if absent; **409 `last_method_required`** guard via `get_effective_setting("tenant_mfa_required", ...)` exactly as today.
2. New, after the guard: `client.set_mfa_preference(access_token, <factor>_enabled=False)` for the row's `method_type`. If another verified method remains for the user, follow with `set_mfa_preference(prefer=<remaining>)` so Cognito always has a preferred factor.
3. Then delete the row → 204.
4. Cognito failure → Task-8 mapping (502/503) and the row is **retained** (never strand a Cognito factor without a DB row). No partial states: Cognito call first, DB delete second.
5. Real route gains `Depends(get_cognito_access_token)`; `/test` twin passes the sentinel.

---

## Task 6 — `mfa-status` Additive `methods[]` Extension

Modify `MfaStatusResponse` + `_get_mfa_status_impl` (lines ~56–61 and ~220–267) per design §D.4:

- New Pydantic model (this file, v2 idioms):
  ```python
  class MfaMethodInfo(BaseModel):
      method_id: uuid.UUID
      method_type: str
      enrolled_at: datetime
      last_used_at: datetime | None   # stays null this batch — Cognito owns challenge telemetry
      destination_masked: str | None  # "***-***-1234" from metadata.destination_last4; null for totp
  ```
- `MfaStatusResponse` gains `methods: list[MfaMethodInfo]`; **keep `enrolled_methods: list[str]` unchanged** (mobile `useMfaStatus` consumes it — backward compat).
- Populate from the same tenant+user-scoped query already in the impl. `destination_masked` is built from `metadata["destination_last4"]` when present.

This changes the response schema → **OpenAPI regen is mandatory** (Regeneration section below).

---

## Task 7 — Delete Dead `MfaLoginChallenge*` Schemas

Delete `MfaLoginChallengeInitiateResponse`, `MfaLoginChallengeVerifyRequest`, `MfaLoginChallengeVerifyResponse` (`account_security.py–105`). Your pre-work grep confirmed zero route/import references — re-run it after deletion to confirm zero remaining hits:

```bash
grep -rn "MfaLoginChallenge" backend/ --include="*.py"   # expect: no output
```

Login challenge is Amplify-native (design §0-2); these schemas were never wired to a route. No OpenAPI impact (unreferenced schemas).

---

## Task 8 — RFC 7807 Error-Mapping Helper

Add a single mapping helper in `account_security.py` and use it in all three rewired impls (design §F.3 — exact table):

| Condition / Exception | HTTP | `code` |
|---|---|---|
| Missing `X-Cognito-Access-Token` (from Task 2 helper) | 400 | `mfa_access_token_required` |
| `MfaAccessTokenInvalidError` | 401 | `mfa_access_token_invalid` |
| `MfaCodeMismatchError` | 400 | `mfa_code_invalid` |
| `MfaCodeExpiredError` | 400 | `mfa_code_expired` |
| email enroll-start | 400 | `email_mfa_not_available` |
| missing / unparseable phone | 400 | `phone_number_required` / `phone_number_invalid` |
| `MfaSmsRoleNotConfiguredError` | 503 | `sms_delivery_not_configured` |
| `CognitoMfaError` (any other) | 502 | `cognito_unavailable` |

Every `HTTPException.detail` is the RFC 7807 Problem Details dict (`type` / `title` / `status` / `detail` + the `code` field) — Rule 8. Plain-string `detail` is banned. Check how existing routes in this file (or a neighbor like `api/routes/settings.py`) embed `code` in the problem dict and follow that exact convention. Return 404 (not 403) for tenant-scoped misses, as today.

---

## Task 9 — Tests

Per `backend/tests/README-adding-tests.md` and the Test Requirements section below. All new files: `pytestmark = [pytest.mark.domain_identity_access, pytest.mark.unit]` (MFA → `identity_access` domain), `client` fixture only, scope assertions by inserted IDs, never assert total row counts.

**9a. Rework `backend/tests/batch_b13/test_a69_mfa_enrollment.py`** onto mock semantics:

- Add the `pytestmark` declaration (currently absent).
- `test_email_returns_destination_masked` → now expects **400 `email_mfa_not_available`** (rename accordingly).
- `test_sms_returns_destination_masked` → first set the test-context user's `phone_number` (e.g. `"+15551234567"`) via `db_session` in the same transaction (the `client` fixture shares `db_session`; rollback cleans it). Assert mask shape.
- New: SMS enroll-start with `phone_number` NULL → 400 `phone_number_required`.
- Confirm tests: `"123456"` → 201 + row written with `cognito_method_id == "totp:software-token"`; keep the no-duplicate test (two confirms → one row; second is 200 per the replay matrix — update assertions).
- Add: `{"code": "000000"}` → 400 `mfa_code_invalid`; `{"code": "999999"}` → 400 `mfa_code_expired`.
- Keep the 409 last-method guard test (it uses a tenant-scoped `PlatformSetting` row — preserve its insert-scoped pattern).

**9b. New folder `backend/tests/batch_mfa_wire_1/`** (remember `__init__.py` only if sibling batch folders use one — check first):

| File | Coverage |
|---|---|
| `test_cognito_mfa_client.py` | Mock semantics (fixed secret; code matrix incl. `000000`/`999999`; masked destination from recorded phone; preference state recording). Factory: monkeypatch `settings.MFA_COGNITO_MOCK` True/False → Mock/Real instance + mock-init WARNING via `caplog` (mirror `tests/batch_b11/test_a59_sms_carrier_adapter.py` `TestTelnyx10DlcMockFlag` pattern). Real client via botocore `Stubber`: success paths + each `ClientError` code → correct exception (all five §F.3-relevant codes + generic → `CognitoMfaError`). |
| `test_mfa_enroll_wiring.py` | `/test`-twin end-to-end on the mock: TOTP enroll-start returns `otpauth://` URI + secret; confirm 201 writes row **with `cognito_method_id="totp:software-token"`**; SMS full path with phone set; **no-DB-write invariant**: force a client failure (monkeypatch the client method to raise `CognitoMfaError` or use code `000000`) → assert **zero** `user_mfa_method` rows for the test user (scoped select, not a count-all); replay: second confirm → 200 same `method_id`, still exactly one row for (tenant, user, type). |
| `test_mfa_error_mapping.py` | Every §F.3 row asserted through the `/test` twins by monkeypatching the mock client to raise each exception: 401 `mfa_access_token_invalid`, 400 `mfa_code_invalid`, 400 `mfa_code_expired`, 503 `sms_delivery_not_configured`, 502 `cognito_unavailable`; plus 400 `email_mfa_not_available` and both phone 400s. Assert the RFC 7807 dict shape (keys `type`/`title`/`status`/`detail`/`code`), not just the status. |
| `test_mfa_status_methods.py` | `methods[]` array present with `method_id`/`method_type`/`enrolled_at`/`last_used_at`/`destination_masked`; `enrolled_methods` still present and consistent; empty state (no methods for an isolated user — use `second_tenant` pattern if needed). |
| `test_mfa_delete_wiring.py` | Delete disables the factor on the mock (assert the mock's recorded preference state); remaining-method prefer-shift; Cognito failure (monkeypatched raise) → 502 **and row retained**; 409 last-method guard still fires before any client call. |
| `test_mfa_token_not_logged.py` | `caplog` over a full enroll-start→confirm→delete cycle: assert the access-token sentinel string appears in **zero** log records. |

Existing status/recovery/session/export tests must keep passing untouched — if one breaks, that break is yours to diagnose (Rule 11).

---

## Verification Checkpoints

- **After Tasks 1–2**: `pytest -m unit --tb=short -q | tail -5` — green (no route behavior changed yet).
- **After Tasks 3–5**: targeted `pytest tests/batch_b13/test_a69_mfa_enrollment.py -m unit --tb=short -q` — expect failures here only (reworked in Task 9); full unit run otherwise green.
- **After Tasks 6–8**: `pytest -m unit --tb=short -q | tail -5` — green except known B13 MFA failures.
- **After Task 9**: full Phase 1 green, then Phase 2 gate below.

---

## Regeneration Steps

### Regenerate OpenAPI (REQUIRED — `mfa-status` response schema changed)

After all tests pass (and after the changed-files ruff gate):

```bash
cd <repo>/backend
source .venv/bin/activate
python export_openapi_json.py
```

This generates **two files**: `backend/openapi.json` (consumed by `pnpm sync-api-types` — the Part B/C handoff signal) and `backend/openapi_schema_map.md`. Verify:

```bash
grep -B 2 -A 8 "mfa-status" backend/openapi_schema_map.md
```

### Regenerate Import Map (REQUIRED — new test files added)

```bash
python generate_app_import_map.py tests > app_model_imports.md
```

### Explicitly NOT required this batch (design §B — do not run/invent work here)

- **No Alembic migration** — zero schema changes.
- **No `schema_manager.py`** — JSON schema untouched.
- **No `generate_db_model_map.py`** — no SQLModel class added or modified.
- **No new entity → no new `/test` endpoint pattern work** — `/test` twins already exist; you only change how they obtain the token (sentinel).
- **No Celery** — no new tasks; `mfa_grace_reminders` untouched.

---

## Seed Data Rollout (Core + Scenario)

**Not applicable — this batch adds or modifies zero database data** (no migration, no lookup rows, no seed changes; design §B). §11.5/§20 is satisfied by this explicit statement. Do not touch any `seed_*.py` script or `README-seed-data.md`.

---

## Final Verification

### Phase 1 — Unit Tests Only (run after each task group during development)

```bash
cd <repo>/backend
source .venv/bin/activate

# Unit tests only — fast feedback loop during implementation
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

All unit tests must pass before moving to the next task. Fix any unit failure — including failures that appear to be caused by code outside your batch — before proceeding.

### Phase 2 — Lint (changed files only) + Full Suite, Vendor-Deselected (run once, at the very end, before DoD sign-off)

```bash
cd <repo>/backend
source .venv/bin/activate

# Lint + format gate (rules §23) — CHANGED FILES ONLY, not the whole codebase
# The sed strips the "backend/" prefix because git diff returns repo-root-relative paths
# but ruff runs from inside backend/ and needs backend/-relative paths
CHANGED_PY=$(git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||')

if [ -n "$CHANGED_PY" ]; then
    ruff check --fix $CHANGED_PY     # lint + isort (I) + pyupgrade (UP) autofix
    ruff format $CHANGED_PY          # format (line-length 88)
    ruff check $CHANGED_PY           # re-check: any remaining errors need manual fixing
fi

# Full suite — vendor/live-service suites deselected (Tom's standing instruction 2026-08-16;
# they add 9+ min: Telnyx/Stripe/SendGrid vendor APIs, Redis-dependent, e2e).
# Inclusion rule: this batch touches Cognito/auth code only — NO Telnyx/Stripe/SendGrid/Redis-covered
# code — so no vendor marker suite is required. (If a batch modifies code those suites cover, also run
# the affected `-m requires_<vendor>` suite before sign-off and record it in the Completion Summary.)
python -m pytest -m "not integration and not requires_telnyx and not requires_stripe and not requires_sendgrid and not requires_redis and not e2e" --tb=short -q 2>&1 | tail -15

# Batch-specific spot checks
python -m pytest tests/batch_mfa_wire_1/ tests/batch_b13/test_a69_mfa_enrollment.py -v 2>&1 | tail -30
grep -B 2 -A 8 "mfa-status" backend/openapi_schema_map.md

echo "=== MFA-WIRE-1 PART A FINAL VERIFICATION COMPLETE ==="
```

> **Warning-clean is part of done.** `ruff` must report no remaining issues **in your changed files** (no unjustified `# noqa`), and the pytest run must be free of `DeprecationWarning` noise. **Do not run `ruff check .` against the entire codebase** — scope to changed files only (rules §23).

> **Any failure in either phase — unit or the vendor-deselected full suite — must be fixed before the batch is declared done.** There is no "pre-existing failure" exception without explicit written confirmation from Tom. If you cannot identify the root cause of a failing test → STOP and ask Tom before proceeding.

---

## Test Requirements

Per `backend/tests/README-adding-tests.md`:

**Every new test file MUST:**
- Declare `pytestmark` with both domain marker and `pytest.mark.unit`:
  ```python
  pytestmark = [
      pytest.mark.domain_identity_access,
      pytest.mark.unit,
  ]
  ```
- Use the `client` fixture (never module-level `TestClient`)
- Use `test_tenant` and `test_user` fixtures (never hardcoded UUIDs)
- Scope assertions by inserted IDs — never `assert len(all_rows) == N` (seed data makes total counts unpredictable)
- Live in `backend/tests/batch_mfa_wire_1/` (batch folder convention; domain marker above keeps domain reporting correct)

**Test Resilience Rule (MANDATORY):** tests run against a shared DB with persistent seed data.

- **Never UPDATE or DELETE rows you did not INSERT** in the current test. Exception this batch: setting `phone_number` on the shared test-context user is permitted **only** inside the `db_session` transaction so it rolls back (the `client` fixture shares `db_session`). Never commit that mutation from test code.
- **Never assert on total row counts** — filter by the specific ID(s) you inserted.
- **Never assume a table is empty** — use `second_tenant` for "empty state" behavior.
- **The `db_session` fixture is the isolation mechanism** — transaction rollback is the cleanup; no manual deletes except rows you inserted (scoped by exact ID).

**Autouse fixtures (already active — do not re-declare):**

| Autouse Fixture | What it does | Opt-out marker |
|---|---|---|
| `mock_cognito_jwks` | Patches AWS Cognito JWKS — no real AWS call | None needed |
| `mock_ai_services` | Patches all Ollama + Whisper HTTP calls | `@pytest.mark.requires_ollama` / `@pytest.mark.requires_whisper` |
| `mock_entitlement_allowed` | Bypasses subscription entitlement checks | `@pytest.mark.skip_mock_entitlement_allowed` |

MFA enrollment is **not** entitlement-gated — no opt-outs needed this batch. The mock Cognito MFA client is your seam; never let a unit test make a real AWS call (the `MFA_COGNITO_MOCK` default-True setting guarantees this; your factory test monkeypatches it explicitly).

---

## Definition of Done

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting work (or confirmed with Tom)
- [ ] All 5 MCP pre-work queries run — every touched table verified via `information_schema.columns`; constraint query confirms `uq_user_mfa_method_tenant_user_type`; results match design §A expectations
- [ ] All mandatory source files read before writing any code (including `core/config.py` and the B13 test file)
- [ ] Task 1: `services/cognito_mfa_client.py` created (exceptions, Protocol, Real w/ `Config(signature_version=UNSIGNED)`, deterministic Mock, factory); `MFA_COGNITO_MOCK: bool = True` added to `core/config.py`; mock-init WARNING present
- [ ] Task 2: `get_cognito_access_token()` in `core/auth.py`; 400 `mfa_access_token_required`; token never logged
- [ ] Task 3: enroll-start rewired (TOTP real secret + `PilotForTrades` otpauth URI; SMS phone-required/E.164/set+send; email 400 `email_mfa_not_available`); `/test` twins use the sentinel token
- [ ] Task 4: enroll-confirm rewired (verify → preference → DB write **only on Cognito success**; replay short-circuit → 200 existing `method_id`; grace-tracking update preserved; audit context preserved)
- [ ] Task 5: delete wired (factor disable → prefer-shift → row delete; 409 guard intact; failure → 502/503 with row retained)
- [ ] Task 6: `methods[]` additive on mfa-status; `enrolled_methods` unchanged
- [ ] Task 7: `MfaLoginChallenge*` schemas deleted; post-delete grep returns zero hits
- [ ] Task 8: single error-mapping helper; all nine §F.3 rows implemented as RFC 7807 dicts
- [ ] Task 9: B13 file reworked + six new test files in `tests/batch_mfa_wire_1/`; no-DB-write invariant + token-not-logged tests included
- [ ] All DB-touching routes/`_impl()`/service functions are sync `def` — no `async def` anywhere (rules §21)
- [ ] Only Pydantic v2 idioms; every route keeps `response_model` (rules §22)
- [ ] `set_audit_context_sync()` preserved ahead of every DB write in the mutation impls
- [ ] All new API errors follow RFC 7807 Problem Details format
- [ ] All new test files use `pytestmark` with `domain_identity_access` + `unit`
- [ ] No module-level `TestClient`; no hardcoded UUIDs; assertions scoped by inserted IDs
- [ ] `python export_openapi_json.py` run — `openapi.json` + `openapi_schema_map.md` updated and committed
- [ ] `python generate_app_import_map.py tests > app_model_imports.md` run (new test files)
- [ ] No Alembic migration, no `schema_manager.py`, no `db_models_map.md` regen, no seed changes (explicit N/A confirmed)
- [ ] `ruff check --fix && ruff format` run **on changed files only** — zero remaining issues in those files (including pre-existing), no unjustified `# noqa` (rules §23)
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`) — zero failures
- [ ] **Phase 2**: Full suite (vendor-deselected) passes — `pytest -m "not integration and not requires_telnyx and not requires_stripe and not requires_sendgrid and not requires_redis and not e2e"` — zero failures, warning-clean (no vendor marker suite required: batch touches no Telnyx/Stripe/SendGrid/Redis-covered code)
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to launch plan Appendix C + ops-doc updates below
- [ ] **Handoff**: committed `openapi.json` bump + Completion Summary posted → notify that Part B/C may begin once their designer specs are Tom-approved (they run `pnpm sync-api-types` first)

---

## Completion Summary

After all Definition of Done items are complete:

1. Add a **Completion Summary** subsection to `dev-docs/analysis/pilot-launch-plan.md` **Appendix C** titled `### MFA-WIRE-1 (Part A) — MFA Backend Cognito Wiring: Completion Summary` using the format below.
2. **Ops-doc updates (you are Responsible for `pilot-operations.md` per the master-doc RACI; the Architect verifies):**
   - `dev-docs/pilot-operations.md` **§13.13** — refresh the implementation-status table: enroll/confirm/delete now real-Cognito-wired (Part A date), login challenge Amplify-native (as-built), email MFA descoped (400), `SmsConfiguration` pre-flight status (cross-reference the DevOps Step 0 completion), mock-seam env var.
   - **§13.5** — add a correction note: the "backend calls RespondToAuthChallenge" narrative is superseded — the login challenge is Amplify-native via FE-B2 `confirmMfaChallenge()` → `confirmSignIn`; no backend challenge endpoints exist (design §G-Q5).
   - **§13.2** — correct the claim that the SNS role exists: it did not prior to MFA-WIRE-1 Step 0 (design §0 row 9); record the Terraform-managed end state once the DevOps completion confirms it.
3. If any MCP-verified column name differed from this prompt, list the discrepancy in the summary.

```markdown
### MFA-WIRE-1 (Part A) — MFA Backend Cognito Wiring: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished

- [Client seam + settings toggle]
- [Access-token header helper]
- [enroll-start / enroll-confirm / delete rewired; replay matrix; zero-DB-write invariant]
- [mfa-status methods[] additive extension; dead schema cleanup]
- [Error mapping incl. 503 sms_delivery_not_configured]

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/services/cognito_mfa_client.py` | Created — mock/real seam (design §F.1) |
| `backend/core/config.py` | Updated — `MFA_COGNITO_MOCK` setting |
| `backend/core/auth.py` | Updated — `get_cognito_access_token()` |
| `backend/api/routes/account_security.py` | Updated — Tasks 3–8 |
| ... | ... |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/batch_mfa_wire_1/test_cognito_mfa_client.py` | `identity_access` | N | ✅ |
| ... | ... | ... | ... |

#### Verification

- Phase 1 unit + Phase 2 full-suite results (counts)
- OpenAPI regen confirmed (`grep` evidence)
- MCP-vs-prompt discrepancies (or "none")
```

---

## After This Task — Next Step

Part A closes the backend half of MFA-WIRE-1. The batch continues with:

1. **DevOps Step 0** (parallel — may already be done): Cognito `SmsConfiguration` pre-flight per `batch-mfa-wire-1-devops-prompt.md`. It gates only the production SMS smoke (batch DoD item 2), not your work.
2. **Part B (web)** and **Part C (mobile)** — gated on Tom-approved designer specs (`batch-mfa-wire-1-web-ui-design-spec.md` / `batch-mfa-wire-1-mobile-ui-design-spec.md` per Rule 1.5). The React/RN engineers run `pnpm sync-api-types` first — your committed `openapi.json` is their contract.
3. **Production smoke (Tom)** — design §C Step 7: TOTP enroll → sign out/in → Cognito challenge; SMS smoke gated on Step 0; tenant-policy force-flow.

Do not start Part B/C work from this prompt — it is backend-only.
