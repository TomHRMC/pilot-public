# Batch Design: COGNITO-EMAIL-1 — Cognito Auth Emails via SendGrid Custom Email Sender

**Status**: DRAFT v1.0 — for Tom approval
**Author**: Pilot Architect
**Batch code**: COGNITO-EMAIL-1 (Phase 1, Ord 15 · launch plan §3.15 · §7 gate row)
**Owners**: Part A — Python Engineer (Lambda + tests) → Part B — DevOps Engineer (packaging + Terraform + wiring + smokes). **Sequential: A before B.**
**Prompts**: `batch-cognito-email-1-python-engr-prompt.md` · `batch-cognito-email-1-devops-prompt.md`
**Estimate**: ~0.5–1 day total (A ~2 h; B ~3 h + smoke waits) — matches card
**Cost**: ~$0 marginal (existing SendGrid plan; negligible Lambda invocations) — $888 baseline untouched; no Founder cost review triggered

---

## Problem Statement

The prod user pool sends auth emails via `COGNITO_DEFAULT` (Amazon shared sending): **50 emails/day cap, no DKIM/SPF control, spam placement** — the root cause of the 2026-08-25 prod signup verification-email failure, and unbranded for every founder employee invite (TEAM-INVITE-1/2 now live). Cognito's `DEVELOPER` email mode supports **SES only**, so the SendGrid path (Tom decision 2026-08-25) uses the **Custom Email Sender Lambda trigger** — the email analog of the ADR-0015 custom-SMS-sender pattern: Cognito invokes our Lambda with a KMS-encrypted code → the Lambda decrypts, renders a branded template, and delivers via SendGrid (`noreply@pilotfortrades.com`, verified sender, DKIM already in Cloudflare).

Covered flows: **SignUp** (incl. TEAM-INVITE invitee verification), **ResendCode**, **ForgotPassword**, **VerifyUserAttribute**, **UpdateUserAttribute**, **AdminCreateUser** (future-proofing — current flows are self-`SignUp` per ADR-0011). AccountTakeOverNotification is not enabled. MFA SMS is untouched (ADR-0015 SNS path).

## A. Input Read Summary

| Input | What it contributed |
|---|---|
| Launch plan §3.15 card (full) + §7 gate row | Scope (6 items), plan-gate, rollback posture, cost bound, estimate |
| `pilot-adr-log.md` ADR-0011 / ADR-0015 | Manual trigger-wiring posture (`lambda_config` in `ignore_changes`); custom-sender analog pattern |
| `infrastructure/terraform/modules/security/main.tf` | `aws_kms_key.pilot` + alias (lines 3–20); user pool resource with `ignore_changes = [lambda_config, …]` (lines ~769–803); Lambda zip pattern via `data.archive_file` ← `modules/security/build/<name>` (lines 856–941); `aws_lambda_permission` cognito-idp principal; existing KMS-decrypt grants on Lambda roles (233/332/387) |
| `backend/lambda/post_authentication/handler.py` (full, 323 lines) | Never-raise passive-hook invariant (contrast case for §G.4); env→Secrets-Manager ARN resource resolution; multi-tenant owner fan-out evidence for the SMS triage (§G.7) |
| `backend/lambda/post_confirmation/handler.py` | Lambda package structure (`backend/lambda/<name>/handler.py`); self-contained ORM import discipline |
| `infrastructure/scripts/build-post-authentication-lambda.sh` (lines 1–90) | Packaging pattern: pip cross-install manylinux cp312 wheels → `build/<name>` → TF `archive_file`; boto3 NOT packaged (runtime-provided) |
| `backend/services/email_service.py` | House SendGrid pattern: `SendGridAPIClient(key)`, `Mail(from_email=(addr, name), …)`, 202 = accepted, structured error logging |
| `backend/core/config.py` | `SENDGRID_FROM_EMAIL = "noreply@pilotfortrades.com"`, `SENDGRID_FROM_NAME = "Pilot for Trades"` |
| `aws-env-mgmt-ops-plan.md` | `pilot/prod/sendgrid` secret holds `SENDGRID_API_KEY` (line 79); SendGrid posture per phase (line 56); **no new secrets** for this batch |
| `aws-cognito-prod-setup.md` | Current `COGNITO_DEFAULT` posture (lines 105–110); the 📐 PLANNED COGNITO-EMAIL-1 section (389–395) this batch flips to LIVE |
| `backend/tests/domains/identity_access/test_post_confirmation_router.py` + `test_post_authentication_handler.py` | Lambda test convention: `importlib.import_module("lambda.<name>.handler")`, domain `identity_access` |
| `backend/requirements.txt` | `sendgrid==6.11.0` — the exact pin for the Lambda package |
| `batch-mfa-wire-1-devops-prompt.md` | DevOps prompt house format (baseline captures, HCL blocks, plan-gates, doc tails) |
| Python inclusions (945 lines, re-read per Rule 9.1) | Part A prompt mandatory sections |

## B. Migration Plan

**None — zero DB changes.** No tables, columns, migrations, seed rows, or OpenAPI delta. Auth-email templates are **inline in the Lambda package** (not DB `email_template` rows) by deliberate design: the auth-critical delivery path must not depend on RDS availability, and Cognito auth emails are platform-owned (not tenant-branded, not tenant-editable). `pnpm sync-api-types` is a no-op for this batch.

## C. Execution Order

| # | Step | Owner | Output |
|---|---|---|---|
| 1 | Lambda package: `backend/lambda/custom_email_sender/` (`handler.py` + `templates.py`) | Python | Self-contained handler (no `app.*` imports, no DB) |
| 2 | Unit tests: `backend/tests/domains/identity_access/test_custom_email_sender_handler.py` | Python | Event fixtures per trigger source; KMS + SendGrid mocked |
| 3 | Build script: `infrastructure/scripts/build-custom-email-sender-lambda.sh` | DevOps | Populates `modules/security/build/custom_email_sender/` |
| 4 | Terraform: Lambda fn + IAM role (Secrets `pilot/prod/sendgrid` read; KMS decrypt on `aws_kms_key.pilot`) + `aws_lambda_permission` + CloudWatch alarm → SNS alarms topic | DevOps | `terraform plan` review with Tom → apply |
| 5 | Pool wiring (**manual CLI per ADR-0011 posture**): ONE `update-user-pool` call carrying **all three** trigger ARNs + `KMSKeyID` | DevOps | `describe-user-pool` verification |
| 6 | Smokes (Tom-assisted): signup code + forgot-password code to external Gmail → inbox placement + DKIM/SPF pass in headers; resend-code | DevOps + Tom | Evidence in completion summary |
| 7 | Docs: cognito-prod-setup 📐→LIVE; env-mgmt secrets note; runbook §14.5 addendum (incl. rollback); as-built | DevOps | Master-doc updates per §12.3 |

## D. New API Endpoints

**None.** New AWS surface instead: one Lambda function (`pilot-production-custom-email-sender`), one Cognito `CustomEmailSender` trigger wiring (`lambda_version = "V1_0"`), one CloudWatch alarm. No FastAPI routes; no `openapi.json` change.

## E. Pattern Reuse Decisions

| Pattern | Application |
|---|---|
| Custom-sender analog (ADR-0015 SMS) | Cognito trigger → vendor delivery, keeping the vendor key in Secrets Manager and Cognito in `COGNITO_DEFAULT` fallback posture |
| Manual trigger wiring (ADR-0011) | `lambda_config` stays in `ignore_changes`; wiring is a documented CLI ceremony (§G.2), exactly like PostConfirmation/PostAuthentication |
| Resource resolution (post-auth handler) | env var first (`SENDGRID_API_KEY` for local/tests) → else `SENDGRID_SECRET_ARN` via boto3 Secrets Manager (lazy import; boto3 not packaged) |
| Zip packaging (build-post-*-lambda.sh) | pip `--platform manylinux2014_x86_64 --implementation cp --python-version 3.12 --only-binary=:all:` → TF `data.archive_file` |
| Lambda test convention | `importlib.import_module("lambda.custom_email_sender.handler")`, `pytestmark = [domain_identity_access, unit]` |
| §16 platform patterns | None — no app surface |

## F. Shared Module Interfaces

**Cognito event contract (V1_0)** — fields the handler consumes:

```python
event["triggerSource"]                # CustomEmailSender_{SignUp|ResendCode|ForgotPassword|
                                      #   UpdateUserAttribute|VerifyUserAttribute|AdminCreateUser}
event["userPoolId"]
event["userName"]
event["callerContext"]["clientId"]
event["request"]["userAttributes"]["email"]
event["request"]["code"]              # base64 KMS-encrypted blob (the OTP / temp password)
event["request"]["clientMetadata"]    # may be absent
# Response: return event (unmodified).
```

**`backend/lambda/custom_email_sender/handler.py`**:

```python
def handler(event: dict, context) -> dict: ...
    # route by triggerSource → flow; decrypt; render; send; return event.
    # Unknown triggerSource → log + RAISE (§G.4 loud-failure posture).

def _decrypt_code(event: dict) -> str: ...
    # base64-decode request.code → kms.decrypt(CiphertextBlob=…,
    #   EncryptionContext={"userpool-id": event["userPoolId"],
    #                      "client-id":  event["callerContext"]["clientId"]})
    # (exact context-key casing verified against the AWS doc page — Part A Pre-Work)

def _render(flow: Flow, code: str, email: str) -> RenderedEmail: ...  # (subject, html, text)

def _send(to_email: str, rendered: RenderedEmail) -> None: ...
    # sendgrid 6.11.0; FROM ("noreply@pilotfortrades.com", "Pilot for Trades");
    # click + open tracking DISABLED (auth emails); non-202 → raise.

def _resolve_sendgrid_key() -> str: ...
    # env SENDGRID_API_KEY → else SENDGRID_SECRET_ARN JSON key "SENDGRID_API_KEY".
```

**`templates.py`** — three flows, each HTML + plaintext (Pilot brand, inline styles only, code prominent ≥28 px letter-spaced, no external images, no links except `https://pilotfortrades.com` footer):

| Flow | Trigger sources | Subject |
|---|---|---|
| `verification_code` | SignUp, ResendCode, VerifyUserAttribute, UpdateUserAttribute | `Your Pilot for Trades verification code` |
| `forgot_password` | ForgotPassword | `Reset your Pilot for Trades password` |
| `admin_invite` | AdminCreateUser (future) | `You've been invited to Pilot for Trades` (temp password = code) |

**Terraform (security module)**: `data.archive_file.custom_email_sender` ← `build/custom_email_sender`; `aws_lambda_function.custom_email_sender` (`pilot-${var.environment}-custom-email-sender`, python3.12, handler `handler.handler`, 256 MB / 30 s, env `SENDGRID_SECRET_ARN`); IAM role + inline policies (`secretsmanager:GetSecretValue` on the sendgrid secret ARN; `kms:Decrypt` on `aws_kms_key.pilot.arn`); `aws_lambda_permission` (principal `cognito-idp.amazonaws.com`); `aws_cloudwatch_metric_alarm` on the function's `Errors` (≥1 in 5 min) → existing SNS alarms topic.

**CLI wiring (Part B, manual)**: one call —
`aws cognito-idp update-user-pool --user-pool-id <id> --lambda-config "PostConfirmation=<arn>,PostAuthentication=<arn>,CustomEmailSender=<arn>,KMSKeyID=<kms-arn>"` — the API **replaces the entire LambdaConfig map**, so omitting an existing ARN silently detaches that trigger (§G.2).

## G. Open Questions Resolved

**G.1 — `email_sending_account` never leaves `COGNITO_DEFAULT`.** With `CustomEmailSender` wired, Cognito invokes the Lambda *instead of* sending — the provider setting is bypassed, not changed. **Rollback = detach the trigger** (one CLI call restoring the prior two-trigger LambdaConfig; the Lambda stays deployed, dormant). This amends the card's "Terraform flip `email_sending_account`" wording — config-only rollback preserved, mechanism corrected. SES remains the documented no-code fallback (cognito-prod-setup §389).

**G.2 — Trigger wiring is manual CLI, one call, ALL triggers.** The pool's `lambda_config` is deliberately in `ignore_changes` (ADR-0011 posture, TF lines 783–803). `update-user-pool --lambda-config` **replaces the whole map** — the Part B call must carry `PostConfirmation` + `PostAuthentication` + `CustomEmailSender` + `KMSKeyID` together (the runbook §14.5 "one call, both flags" precedent). Terraform owns the Lambda/role/permission/alarm only — never `lambda_config`.

**G.3 — Pool `KMSKeyID`**: the custom sender encrypts `request.code` with the pool's KMS key. Set via the same one CLI call (`KMSKeyID` is a LambdaConfig field). `aws_kms_key.pilot` (alias `alias/pilot-production`) is the key; the Lambda role gets `kms:Decrypt` on it in TF. The card's plan-gate stands verbatim: **update-in-place on the pool only — any planned replacement = STOP and tell Tom.**

**G.4 — RETHROW on failure (the opposite invariant from our passive hooks).** Post-Confirmation/Post-Authentication must never raise (they're passive — raising blocks sign-in for a side effect). The custom email sender is **the delivery path itself**: if it swallows a KMS/SendGrid failure, Cognito believes the email sent and the user has no code and no error — an unrecoverable silent hole. So: structured log + **raise** → Cognito surfaces a clean failure to the user, who can retry (ResendCode hits the same path) → and the CloudWatch `Errors` alarm fires. Unknown `triggerSource` also raises (loud > silent when config drifts).

**G.5 — Templates are inline, platform-branded, tracking-free.** Three flows per §F (AdminCreateUser included for completeness — no current flow exercises it; ADR-0011 self-`SignUp` covers founders and invitees). SendGrid click/open tracking **disabled** on these sends (wrapped links break code-visibility and deliverability). Brand tokens mirror the `team_invite` template (Arial stack, `#5B3FF0`).

**G.6 — KMS decrypt encryption context**: `{"userpool-id": <userPoolId>, "client-id": <clientId>}` per the AWS custom-email-sender doc. The exact context-key casing is **verified by the Part A engineer against the AWS doc page** (cited in the prompt) before implementation — a wrong context yields `InvalidCiphertextException` at first decrypt, which the unit tests simulate.

**G.7 — SMS-to-owner finding (Tom's tracker, 2026-09-03): BY DESIGN, copy gap logged separately.** The new-device SMS fans out to verified+opted-in **owner** endpoints per tenant — PLATFORM-SMS-B2 design §G-7 (owner is the tenant's security contact; an employee's first sign-in from a new device is exactly what an owner should see). The real gap: the Sample 3 body is **static** ("…sign-in to **your** account…") and doesn't name the sign-in email — confusing when the device was an employee's. Disposition: **NOT this batch** — a future micro-fix parameterizes `platform_security_new_device` with the sign-in email (touches the Celery task + template + the verbatim-guardrail test `test_platform_sms_b2_verbatim_guardrail.py`). Logged to PLAT-DEBT via the launch-plan open script; Tom dispositions at triage.

**G.8 — MFA SMS untouched.** `SmsConfiguration`/SNS (ADR-0015) is orthogonal; this batch changes no SMS path. The `update-user-pool` call in Part B must not alter `SmsConfiguration` or `DeviceConfiguration` (the CLI call targets `--lambda-config` only; verification step confirms both are unchanged).

**G.9 — No new secrets; vendor-suite call.** Reuses `pilot/prod/sendgrid` (`SENDGRID_API_KEY` JSON key) and `aws_kms_key.pilot`. New Lambda env var: `SENDGRID_SECRET_ARN` (recorded in env-mgmt per its §10 maintenance rules). The Part A batch's code is SendGrid-*adjacent* but the handler is fully unit-mocked — the `requires_sendgrid` vendor suite is **not** triggered; the live SendGrid proof is Part B's Gmail smoke (explicit Phase 2 inclusion-call in the Python prompt).

---

---

## Post-Implementation Note (2026-09-04 — batch closed LIVE)

Part B surfaced five implementation realities that **supersede §G.6 and the §F package assumptions** — recorded here so no future reader trusts the original text (full detail: DevOps prompt appendix):

1. **Cognito encrypts the code with the AWS Encryption SDK envelope format — not raw `kms:Encrypt`.** Raw `kms.decrypt()` fails with `InvalidCiphertextException`. The handler uses `aws_encryption_sdk.EncryptionSDKClient` + a KMS keyring (`aws-cryptographic-material-providers`), with `commitment_policy=CommitmentPolicy.REQUIRE_ENCRYPT_ALLOW_DECRYPT` (SDK v4 defaults reject Cognito's uncommitted Algorithm-888 messages). The §G.6 encryption-context keys (`userpool-id`, `client-id`) remain correct — they are passed as the Encryption SDK encryption context.
2. **SendGrid secret JSON key is `api_key`** (Console-created `pilot/prod/sendgrid`), not `SENDGRID_API_KEY` — the handler accepts both. Env-mgmt plan updated by the engineer.
3. **Lambda memory is 512 MB** (not 256) — Encryption SDK + `cryptography` cold-start footprint. Package deps grew accordingly (`aws-encryption-sdk==4.0.6`, `aws-cryptographic-material-providers==1.11.3` + transitive).
4. **CLI syntax**: `CustomEmailSender` in `--lambda-config` takes a dict `{LambdaArn=...,LambdaVersion=V1_0}` — unlike the plain-ARN forms of the other triggers.
5. Env var `KMS_KEY_ARN` was added alongside `SENDGRID_SECRET_ARN`.

All §G decisions (G.1–G.5, G.7–G.9) held as designed; the raise-on-failure posture, one-call-all-triggers wiring, and rollback-by-detach all verified live. Smoke evidence: DKIM/SPF/DMARC PASS, inbox placement, branded ForgotPassword + SignUp. §7 gate row ✅ 2026-09-03.

*Design v1.0 — changes require Architect review + Tom approval. Post-implementation note appended by the Architect at close (§12.3 stewardship).*
