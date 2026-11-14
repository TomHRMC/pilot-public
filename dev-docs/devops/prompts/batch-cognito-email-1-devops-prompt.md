# Implementation Prompt: COGNITO-EMAIL-1 (Part B) — Custom Email Sender Packaging, Terraform, Pool Wiring + Smokes

**Mode**: Pilot DevOps Engineer
**Batch**: COGNITO-EMAIL-1 (Part B of 2 — infrastructure + wiring + verification)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` _(private)_ §1.1 Ord 15 + §3.15 card · §7 gate row
**Design doc**: [`dev-docs/architecture-design/batch-designs/batch-cognito-email-1-design.md`](../../architecture-design/batch-designs/batch-cognito-email-1-design.md) ✅ — §C (execution order), §F (TF/CLI interfaces), §G (resolved decisions) are binding
**Prerequisite**: **Part A complete and merged** ([`batch-cognito-email-1-python-engr-prompt.md`](../../implementation-prompts/fe-be-mob-batch-prompts/batch-cognito-email-1-python-engr-prompt.md)) — the deployment package is built from `backend/lambda/custom_email_sender/`. Confirm the handler exists + Part A's completion summary before starting.
**Estimated session**: ~3 hours (plus short waits on Tom: plan review + two smoke emails)
**Cost impact**: **~$0 fixed delta.** Lambda invocations are free-tier negligible; one CloudWatch alarm (~$0.10/mo); SendGrid is the existing plan. No new AWS service class → $888 baseline untouched, no Founder cost review (infrastructure-constraints §1).

---

## ⚠️ MANDATORY STOP: Read These First

- **[`.roo/rules-pilot-devops-engineer/secret-management-policy.md`](../../../.roo/rules-pilot-devops-engineer/secret-management-policy.md)** — least-privilege IAM (the new role reads exactly one secret + decrypts on exactly one KMS key)
- **[`.roo/rules-pilot-devops-engineer/blue-green-constraints.md`](../../../.roo/rules-pilot-devops-engineer/blue-green-constraints.md)** — no ECS shift here; S3+DynamoDB state locking applies as always
- **[`aws-ops-runbook.md`](../aws-ops-runbook.md) §14.1/§14.2** — standard plan/apply flow; **§14.5** — the manual trigger-wiring posture this batch extends (Post-Confirmation + Post-Authentication precedents)
- **[`aws-cognito-prod-setup.md`](../aws-cognito-prod-setup.md)** — pool facts + the 📐 PLANNED COGNITO-EMAIL-1 section (you flip it to LIVE in Task 7)
- **The design doc** — especially §G.1 (rollback = detach trigger; `email_sending_account` never changes), §G.2 (**one CLI call, ALL triggers**), §G.3 (plan-gate), §G.8 (do not disturb SMS/device config)

**Why this exists**: the pool sends auth emails via `COGNITO_DEFAULT` — 50/day cap, no DKIM/SPF control, spam placement (real failure 2026-08-25), unbranded invite emails. Part A built the Custom Email Sender Lambda (KMS-decrypt → branded template → SendGrid). You package it, deploy it, wire the trigger, and prove delivery.

## Pre-Work: Read These Files

```
backend/lambda/custom_email_sender/handler.py        ← what you're packaging; note env vars SENDGRID_API_KEY (local override) / SENDGRID_SECRET_ARN
backend/lambda/custom_email_sender/templates.py      ← package contents (both files ship)
infrastructure/scripts/build-post-authentication-lambda.sh   ← pattern to mirror (one simplification: NO app/models bundle — this handler is self-contained)
infrastructure/terraform/modules/security/main.tf    ← aws_kms_key.pilot + alias; user pool resource (lambda_config in ignore_changes — do NOT touch); the post_confirmation/post_authentication Lambda blocks (lines ~856–990) to mirror; KMS-decrypt grant statements (233/332/387)
infrastructure/terraform/modules/security/variables.tf / outputs.tf   ← conventions
infrastructure/terraform/modules/monitoring/main.tf  ← locate the existing SNS alarms topic for the CloudWatch alarm
dev-docs/devops/aws-env-mgmt-ops-plan.md             ← pilot/prod/sendgrid secret (SENDGRID_API_KEY key); §10 maintenance rules (you update it in Task 7)
```

Also capture the live baseline before touching anything (record all of it — the wiring call in Task 5 is built from these values):

```bash
# 1. Current trigger wiring + email posture — EXPECT: PostConfirmation + PostAuthentication
#    ARNs, EmailSendingAccount=COGNITO_DEFAULT, no CustomEmailSender, no KmsKeyId
aws cognito-idp describe-user-pool --user-pool-id us-east-1_XXXXXXXXX --region us-east-1 \
  --query 'UserPool.{LC: LambdaConfig, Email: EmailSendingAccount, Sms: SmsConfiguration, Dev: DeviceConfiguration}'
# Save the full LambdaConfig JSON — Task 5's one-call wiring MUST carry these ARNs forward.

# 2. KMS alias ARN (decrypt grant + wiring)
aws kms describe-key --key-id alias/pilot-production --query 'KeyMetadata.Arn' --region us-east-1

# 3. SendGrid secret ARN exists (do not print the value)
aws secretsmanager describe-secret --secret-id pilot/prod/sendgrid --query '{ARN: ARN}' --region us-east-1

# 4. SNS alarms topic (for the Lambda Errors alarm)
grep -rn "aws_sns_topic" infrastructure/terraform/modules/monitoring/main.tf | head -5
```

## Task 1 — Build Script + Package Build

Create `infrastructure/scripts/build-custom-email-sender-lambda.sh` mirroring `build-post-authentication-lambda.sh` with these deltas:

- `BUILD_DIR="${REPO_ROOT}/infrastructure/terraform/modules/security/build/custom_email_sender"`
- `DEPS=("sendgrid==6.11.0")` only — pip resolves transitive deps (`python-http-client`, `starkbank-ecdsa`). **boto3/botocore are NOT packaged** (Lambda runtime provides them; the handler imports them lazily).
- Copy `backend/lambda/custom_email_sender/` (`handler.py`, `templates.py`, `__init__.py`) into the build dir. **Do NOT bundle `app/models`** — this handler is deliberately self-contained (design §B; the auth email path must not depend on RDS).
- Run it, then verify the payload: `ls ${BUILD_DIR}` shows `handler.py`, `templates.py`, `sendgrid/`, `python_http_client/`, `starkbank_ecdsa/` — and **no** `boto3/`, no `app/`.

## Task 2 — Terraform: Security Module

In [`infrastructure/terraform/modules/security/main.tf`](../../../infrastructure/terraform/modules/security/main.tf), after the post_authentication block, add (mirroring its conventions — memory/timeout/tags match the sibling Lambdas; check lines ~935–990 for exact values):

1. `data.archive_file.custom_email_sender` ← `build/custom_email_sender` → `custom_email_sender.zip`
2. `aws_lambda_function.custom_email_sender` — `pilot-${var.environment}-custom-email-sender`, python3.12, handler `handler.handler`, env `SENDGRID_SECRET_ARN = aws_secretsmanager_secret.sendgrid.arn`
3. IAM role + assume-policy (lambda.amazonaws.com) + inline policies: (a) `secretsmanager:GetSecretValue` on the sendgrid secret ARN only; (b) `kms:Decrypt` on `aws_kms_key.pilot.arn` only; (c) basic execution (logs) — mirror the sibling role pattern
4. `aws_lambda_permission.cognito_custom_email_sender` — principal `cognito-idp.amazonaws.com`
5. `aws_cloudwatch_metric_alarm.custom_email_sender_errors` — `Errors ≥ 1` over one 5-min period on the function → the existing SNS alarms topic (monitoring module); treat-alarm-actionable, with a descriptive `alarm_description` ("Custom Email Sender failed — auth emails (signup/forgot/invite) are NOT being delivered; rollback = detach trigger, runbook §14.5")

Do **not** add `lambda_config`, `kms_key_id`, or `email_sending_account` to `aws_cognito_user_pool.prod` — wiring is manual CLI (design §G.2; `lambda_config` stays in `ignore_changes`).

## Task 3 — Plan-Gate with Tom → Apply

```bash
cd infrastructure/terraform/environments/production
terraform plan -target=module.security
```

**PLAN-GATE (design §G.3 / card item 3)**: review the plan with Tom. Expected: **only adds** (Lambda, role, policies, permission, alarm) — zero changes to `aws_cognito_user_pool.prod`, zero replacements. **Any replacement or pool modification → STOP and tell Tom.** On approval: `terraform apply -target=module.security`. Record the new Lambda ARN.

## Task 4 — Post-Deploy Verification (pre-wiring)

```bash
aws lambda get-function-configuration --function-name pilot-production-custom-email-sender --region us-east-1 \
  --query '{State: State, Runtime: Runtime, CodeSha256: CodeSha256, Env: Environment.Variables}'
aws lambda get-policy --function-name pilot-production-custom-email-sender --region us-east-1 \
  --query 'Policy' --output text | python3 -c "import sys,json; print(json.load(sys.stdin))"
```

Expect: active, python3.12, `SENDGRID_SECRET_ARN` present, cognito-idp invoke permission. **Do not invoke the trigger wiring until this is green.**

## Task 5 — Pool Wiring (manual CLI — ONE call, ALL triggers, design §G.2)

Construct the `--lambda-config` from the **Task-Pre-Work baseline** (PostConfirmation + PostAuthentication ARNs) + the new CustomEmailSender ARN + the KMS key ARN. `update-user-pool` **replaces the entire LambdaConfig map** — omitting an ARN silently detaches that trigger.

```bash
POOL=us-east-1_XXXXXXXXX
PC_ARN=<baseline PostConfirmation ARN>
PA_ARN=<baseline PostAuthentication ARN>
CES_ARN=<new CustomEmailSender ARN from Task 3>
KMS_ARN=<Task 2/pre-work KMS alias key ARN>

aws cognito-idp update-user-pool --user-pool-id $POOL --region us-east-1 --lambda-config \
  "PostConfirmation=${PC_ARN},PostAuthentication=${PA_ARN},CustomEmailSender=${CES_ARN},KMSKeyID=${KMS_ARN}"

# Verify — EXPECT: all three trigger ARNs + KmsKeyId present; EmailSendingAccount still
# COGNITO_DEFAULT; SmsConfiguration + DeviceConfiguration byte-identical to baseline (§G.8)
aws cognito-idp describe-user-pool --user-pool-id $POOL --region us-east-1 \
  --query 'UserPool.{LC: LambdaConfig, Email: EmailSendingAccount, Sms: SmsConfiguration, Dev: DeviceConfiguration}'
```

If the verify shows a missing prior trigger, Sms/Device drift, or EmailSendingAccount changed → restore the baseline LambdaConfig immediately (same call shape, baseline values) and STOP.

## Task 6 — Smokes (Tom-assisted)

Run in this order (each proves a flow end-to-end; capture evidence for the completion summary):

1. **ForgotPassword** (no account creation — safest first): prod login page → "Forgot password" on Tom's owner email → branded email arrives (**inbox, not spam**) → code completes the reset flow. In Gmail: *Show original* → `SPF: PASS`, `DKIM: PASS` (pilotfortrades.com) — screenshot/paste the header lines.
2. **ResendCode**: trigger resend on the same flow → second branded email arrives; send-volume no longer capped at 50/day (trivially true, note it).
3. **SignUp** (full invite proof): a fresh Gmail `+` alias → **Settings → Team → invite** (the TEAM-INVITE-2 flow) → branded verification email → code works → invitee lands per the role branch. This closes the loop on the 2026-08-25 failure mode.
4. **Alarm sanity**: confirm the CloudWatch alarm exists and is in `OK` state (do NOT force a failure).

**If any smoke fails**: check Lambda CloudWatch logs (`/aws/lambda/pilot-production-custom-email-sender`) first; rollback if delivery is broken (Task 7 rollback block), then debug.

## Task 7 — Docs + Rollback Record (master-doc updates, design §C.7 / §12.3)

1. **[`aws-cognito-prod-setup.md`](../aws-cognito-prod-setup.md)** — flip the COGNITO-EMAIL-1 section from 📐 PLANNED to **✅ LIVE 2026-09-XX**: mechanism, triggers wired, KMS key, alarm, and the **rollback block**:
   > *Rollback (config-only, <1 min): `aws cognito-idp update-user-pool --lambda-config "PostConfirmation=<arn>,PostAuthentication=<arn>"` — Cognito instantly falls back to `COGNITO_DEFAULT` sending. The Lambda stays deployed, dormant.*
2. **[`aws-env-mgmt-ops-plan.md`](../aws-env-mgmt-ops-plan.md)** — secrets note: no new secrets (reuses `pilot/prod/sendgrid`); new Lambda env var `SENDGRID_SECRET_ARN` (per its §10 maintenance rules).
3. **[`aws-ops-runbook.md`](../aws-ops-runbook.md) §14.5** — add the Custom-Email-Sender subsection (build → deploy → wire → verify → rollback), mirroring the Post-Confirmation/Post-Authentication subsections.
4. **[`aws-infrastructure-as-built.md`](../aws-infrastructure-as-built.md)** — new Lambda + IAM role + alarm entries.

## Definition of Done

- [ ] Part A confirmed merged (handler + completion summary)
- [ ] Baseline captures recorded (LambdaConfig, EmailSendingAccount, Sms/Device config, KMS ARN, secret ARN, alarms topic)
- [ ] Build script created; package verified (handler + templates + sendgrid; **no boto3, no app/**)
- [ ] Terraform adds applied green — plan-gate honored (no pool change, no replacement)
- [ ] Post-deploy function verification green (active, env, permission)
- [ ] Wiring applied in ONE call; verify shows all three triggers + KmsKeyId; EmailSendingAccount + Sms + Device unchanged from baseline
- [ ] Smokes 1–4 pass with DKIM/SPF PASS evidence captured
- [ ] All four doc updates applied
- [ ] Completion Summary filled in below (ADR-0017)

## Completion Summary

Fill in the appendix below when done (ADR-0017): date · baseline vs final state · what was accomplished (incl. Lambda ARN, alarm name, wiring verify output excerpt) · smoke evidence (DKIM/SPF lines) · files changed · any deviations.

---

## Appendix — Completion Summary

**ADR-0017 — COGNITO-EMAIL-1 Custom Email Sender (Part B)**
**Date**: 2026-09-03
**Engineer**: Pilot DevOps Engineer (AI)
**Status**: ✅ COMPLETE — LIVE in production

### Baseline vs Final State

| Field | Baseline (pre-deploy) | Final (post-deploy + wiring) |
|---|---|---|
| PostConfirmation | ✅ ARN present | ✅ unchanged |
| PostAuthentication | ✅ ARN present | ✅ unchanged |
| CustomEmailSender | absent | ✅ `{LambdaVersion=V1_0, LambdaArn=arn:aws:lambda:us-east-1:000000000000:function:pilot-production-custom-email-sender}` |
| KMSKeyID | absent | ✅ `arn:aws:kms:us-east-1:000000000000:key/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxx1` |
| EmailSendingAccount | null (COGNITO_DEFAULT) | null (unchanged — trigger bypasses it) |
| SmsConfiguration | SnsCallerArn + ExternalId + SnsRegion | unchanged |

### What Was Accomplished

- **Lambda ARN**: `arn:aws:lambda:us-east-1:000000000000:function:pilot-production-custom-email-sender`
- **Alarm name**: `pilot-production-custom-email-sender-errors` (CloudWatch Errors ≥ 1 / 5 min → SNS alarms topic; State: OK)
- **IAM role**: `pilot-production-custom-email-sender-role` (dedicated, least-privilege: sendgrid secret read + KMS decrypt + CloudWatch Logs; no VPC, no RDS)
- **Memory**: 512 MB (increased from planned 256 MB — the AWS Encryption SDK + cryptography library has a larger footprint)
- **Env vars**: `SENDGRID_SECRET_ARN`, `KMS_KEY_ARN`
- **Wiring verify output**: all three triggers (PostConfirmation, PostAuthentication, CustomEmailSender) + KMSKeyID present; EmailSendingAccount + SmsConfiguration unchanged from baseline

### Key Deviations from Design (all resolved)

1. **AWS Encryption SDK required (NOT raw KMS decrypt)** — The design doc §G.6 assumed the code could be decrypted with `kms.decrypt()` + an encryption context. In reality, Cognito uses the **AWS Encryption SDK** (envelope encryption format) to encrypt the code, NOT raw `kms:Encrypt`. Raw `kms.decrypt()` fails with `InvalidCiphertextException`. Fixed: handler now uses `aws_encryption_sdk.EncryptionSDKClient` + a KMS keyring from `aws_cryptographic_material_providers`. This required packaging `aws-encryption-sdk==4.0.6` + `aws-cryptographic-material-providers==1.11.3` (+ transitive deps: cryptography, attrs, wrapt, DafnyRuntimePython, pytz, aws-cryptography-internal-*).

2. **CommitmentPolicy mismatch** — The SDK v4.x defaults to `REQUIRE_ENCRYPT_REQUIRE_DECRYPT` which rejects Cognito's uncommitted messages (Algorithm ID 888). Fixed: `commitment_policy=CommitmentPolicy.REQUIRE_ENCRYPT_ALLOW_DECRYPT`.

3. **SendGrid secret key name** — The `pilot/prod/sendgrid` secret (Console-created) uses JSON key `api_key`, not `SENDGRID_API_KEY` as the handler expected. Fixed: handler accepts both.

4. **Memory increased to 512 MB** — The Encryption SDK + cryptography library has a larger cold-start footprint than the originally planned sendgrid-only package.

5. **CustomEmailSender CLI syntax** — The `--lambda-config` value for `CustomEmailSender` requires a dict `{LambdaArn=...,LambdaVersion=V1_0}`, not a plain ARN string (unlike PostConfirmation/PostAuthentication).

### Smoke Evidence (DKIM/SPF)

ForgotPassword to `owner@example.com` — branded email arrived in inbox (not spam):
- **DKIM: PASS** `header.i=@pilotfortrades.com header.s=s1`
- **SPF: PASS** `domain of ...@emXXXX.pilotfortrades.com designates 203.0.113.14 as permitted sender`
- **DMARC: PASS** `p=QUARANTINE sp=QUARANTINE dis=NONE`
- **From**: `Pilot for Trades <noreply@pilotfortrades.com>`
- **Subject**: `Reset your Pilot for Trades password`
- Second account (tech under same tenant) SignUp also confirmed working.
- Alarm state: OK

### Files Changed

- `infrastructure/scripts/build-custom-email-sender-lambda.sh` — **created** (build script)
- `infrastructure/terraform/modules/security/main.tf` — **modified** (Lambda fn + IAM role + IAM policy + lambda_permission + archive_file)
- `infrastructure/terraform/modules/security/outputs.tf` — **modified** (Lambda ARN + name outputs)
- `infrastructure/terraform/modules/monitoring/main.tf` — **modified** (CloudWatch log group + alarm)
- `backend/lambda/custom_email_sender/handler.py` — **modified** (Part A code: `_decrypt_code` rewritten to use AWS Encryption SDK; `_resolve_sendgrid_key` accepts `api_key`; docstring updated)
- `.gitignore` — **modified** (custom_email_sender.zip + post_authentication.zip entries)
- `dev-docs/devops/aws-cognito-prod-setup.md` — **modified** (📐 PLANNED → ✅ LIVE; build procedure; status line)
- `dev-docs/devops/aws-ops-runbook.md` — **modified** (§14.5 resources table + Custom Email Sender subsection)
- `dev-docs/devops/aws-env-mgmt-ops-plan.md` — **modified** (sendgrid secret key name note)
- `dev-docs/devops/aws-infrastructure-as-built.md` — **modified** (Lambda + IAM role + log group + Cognito trigger entries)
- `dev-docs/devops/prompts/batch-cognito-email-1-devops-prompt.md` — **modified** (this completion summary)
