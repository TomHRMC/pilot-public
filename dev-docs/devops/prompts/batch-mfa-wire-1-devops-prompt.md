# Implementation Prompt: MFA-WIRE-1 (Step 0) — Cognito `SmsConfiguration` Pre-Flight (SMS MFA Delivery Path)

**Mode**: Pilot DevOps Engineer
**Batch**: MFA-WIRE-1 (Step 0 — infrastructure pre-flight; runs **in parallel** with Part A backend work)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` _(private)_ §2.3 MFA-WIRE-1
**Design doc**: [`dev-docs/architecture-design/batch-designs/batch-mfa-wire-1-design.md`](../../architecture-design/batch-designs/batch-mfa-wire-1-design.md) ✅ APPROVED 2026-08-16 (v1.1) — §0 row 9 (the gap), §C Step 0 (this task), §F.3 (`sms_delivery_not_configured`), §G-Q11
**Prerequisite**: None. Do **not** wait for Part A ([`batch-mfa-wire-1-python-engr-prompt.md`](../../implementation-prompts/fe-be-mob-batch-prompts/batch-mfa-wire-1-python-engr-prompt.md)); Part A does not wait for you either. You gate **only** the production SMS smoke (batch DoD item 2) — TOTP ships independently.
**Estimated session**: ~1 hour (plus two short waits on Tom: phone-verification code + OTP receipt)
**Cost impact**: **$0 fixed delta.** The IAM role is free; SNS SMS is pay-per-use (~$0.00645/SMS segment — at 100 users × ~3 OTPs/mo ≈ $2/mo worst case, inside the variable budget of the ~$888/mo baseline). `MonthlySpendLimit` is a **cap**, not a charge. No new AWS service → no Founder cost review triggered (infrastructure-constraints §1).

---

## ⚠️ MANDATORY STOP: Read These First

- **[`.roo/rules-pilot-devops-engineer/secret-management-policy.md`](../../../.roo/rules-pilot-devops-engineer/secret-management-policy.md)** — least-privilege IAM scoping (§4) governs the new `cognito_sns` role in Task 1. Note: the ExternalId is **configuration, not a secret** — it lives in Terraform, not Secrets Manager.
- **[`.roo/rules-pilot-devops-engineer/blue-green-constraints.md`](../../../.roo/rules-pilot-devops-engineer/blue-green-constraints.md)** — mostly N/A here (no ECS traffic shift, no DB change). S3+DynamoDB state locking applies as always.
- **[`aws-ops-runbook.md`](../aws-ops-runbook.md) §14.1/§14.2** — the standard plan/apply flow for the production environment.
- **[`aws-cognito-prod-setup.md`](../aws-cognito-prod-setup.md)** — prod pool facts (`us-east-1_XXXXXXXXX`, MFA Optional, TOTP+SMS factors). **Doc drift alert**: its console-era guidance references an SNS role `CognitoSNSRole-pilot-production` as if it exists — it does not (design-verified; Terraform `modules/security/` has zero SNS resources). Task 1 makes that name real, Terraform-managed.
- **The design doc** — §0 row 9 (audit evidence), §C Step 0 (scope), §G-Q11 (why this gates only the SMS smoke).

**Why this exists (one paragraph)**: The prod pool was console-created 2026-06-30 and later imported into Terraform. It has `mfa_configuration = OPTIONAL` with TOTP + SMS factors, but **no `SmsConfiguration`** — there is no SNS IAM role, so Cognito cannot deliver SMS MFA OTPs. The Cognito→SNS path has never been exercised (signup uses email codes; PLATFORM-SMS-B2's smoke SMS rode Telnyx, a different pathway). Until this lands, real SMS enrollment in prod would fail at Cognito with `InvalidSmsRole*Exception` (Part A maps that to a diagnosable 503 `sms_delivery_not_configured` — never a silent failure).

---

## Pre-Work: Read These Files

```
infrastructure/terraform/modules/security/main.tf       ← aws_cognito_user_pool.prod (lines 643–711). VERIFY: the lifecycle ignore_changes list is [lambda_config, schema, username_configuration, name, user_pool_add_ons] — sms_configuration is NOT ignored, so Terraform can manage it. mfa_configuration = "OPTIONAL" (line 672) + software_token_mfa_configuration (674–676) already present.
infrastructure/terraform/modules/security/variables.tf  ← where Task 1 adds the external_id variable
infrastructure/terraform/modules/security/outputs.tf    ← output conventions (mirror if you add the role ARN output)
infrastructure/terraform/environments/production/main.tf ← how the security module is invoked
dev-docs/devops/aws-cognito-prod-setup.md               ← pool setup history; console-era SNS-role guidance to be corrected in Task 7
dev-docs/devops/aws-ops-runbook.md §14                  ← deploy flow + the extra-steps table Task 7 extends
dev-docs/devops/aws-infrastructure-as-built.md          ← as-built inventory Task 7 extends
```

Also confirm the current live state before touching anything (baseline capture):

```bash
# 1. The gap itself — expect null / absent
aws cognito-idp describe-user-pool --user-pool-id us-east-1_XXXXXXXXX \
  --query 'UserPool.SmsConfiguration'
# Expect: null. If a configuration IS present → STOP and tell Tom (the design's premise is stale).

# 2. SNS sandbox posture (sandboxed SNS silently drops SMS to unverified numbers)
aws sns get-sms-sandbox-account-status
# Record: IsInSandbox true|false

# 3. SNS SMS spend posture
aws sns get-sms-attributes
# Record: MonthlySpendLimit (may be absent → account default is $1.00, too low)
```

---

## Task 1 — Terraform: Security Module (role + `sms_configuration`)

In [`infrastructure/terraform/modules/security/main.tf`](../../../infrastructure/terraform/modules/security/main.tf), immediately above the `aws_cognito_user_pool.prod` resource, add:

```hcl
# MFA-WIRE-1 (Step 0): Cognito SMS delivery — SNS role + SmsConfiguration.
# The pool was console-created (2026-06-30) without an SNS role, so SMS MFA
# OTPs could never be delivered (design §0 row 9). Terraform-managed from here.

resource "aws_iam_role" "cognito_sns" {
  name = "CognitoSNSRole-pilot-production" # matches the console-era setup-doc name

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowCognitoIdpAssume"
        Effect    = "Allow"
        Principal = { Service = "cognito-idp.amazonaws.com" }
        Action    = "sts:AssumeRole"
        Condition = {
          StringEquals = { "sts:ExternalId" = var.cognito_sms_external_id }
        }
      }
    ]
  })

  tags = {
    Component          = "auth"
    CostAllocation     = "security-monitoring"
    DataClassification = "sensitive"
  }
}

resource "aws_iam_role_policy" "cognito_sns_publish" {
  name = "cognito-sns-sms-publish"
  role = aws_iam_role.cognito_sns.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "AllowSnsPublishForSms"
        Effect   = "Allow"
        Action   = "sns:Publish"
        Resource = "*" # SNS phone-number-targeted SMS publish has no resource-level scoping — AWS's own Cognito SMS role documentation uses "*"
      }
    ]
  })
}
```

In [`infrastructure/terraform/modules/security/variables.tf`](../../../infrastructure/terraform/modules/security/variables.tf), add:

```hcl
variable "cognito_sms_external_id" {
  description = "ExternalId for the Cognito→SNS assume-role trust (MFA-WIRE-1). Configuration value, not a secret."
  type        = string
  default     = "pilot-prod-cognito-sms"
}
```

Inside the `aws_cognito_user_pool.prod` resource (e.g., directly after the `software_token_mfa_configuration` block), add:

```hcl
  sms_configuration {
    external_id    = var.cognito_sms_external_id
    sns_caller_arn = aws_iam_role.cognito_sns.arn
    sns_region     = "us-east-1"
  }
```

Do **not** touch `mfa_configuration`, `lambda_config`, `user_pool_add_ons`, the client resources, or the `ignore_changes` list. Do **not** add `sms_authentication_message` (default AWS OTP message is fine for beta; branding is a later polish — note it in your summary if you think it's worth a follow-up).

---

## Task 2 — Plan Gate

Run the standard plan flow for the production environment (runbook §14.1/§14.2). The plan MUST show **exactly three deltas**:

1. `+ aws_iam_role.cognito_sns` (create)
2. `+ aws_iam_role_policy.cognito_sns_publish` (create)
3. `~ aws_cognito_user_pool.prod` (update **in-place** — `+ sms_configuration { ... }`)

**If `plan` shows anything else → STOP and ask Tom.** In particular: pool **replacement** is an immediate stop (deletion_protection is ACTIVE; a replace plan means something else is wrong). `lambda_config` diffs must not appear (it is in `ignore_changes`).

---

## Task 3 — Apply + Verify Wiring

Apply per the runbook, then verify:

```bash
aws cognito-idp describe-user-pool --user-pool-id us-east-1_XXXXXXXXX \
  --query 'UserPool.SmsConfiguration.{SnsCallerArn: SnsCallerArn, ExternalId: ExternalId, SnsRegion: SnsRegion}'
# Expect: SnsCallerArn = arn:aws:iam::<acct>:role/CognitoSNSRole-pilot-production
#         ExternalId  = pilot-prod-cognito-sms
#         SnsRegion   = us-east-1
```

---

## Task 4 — SNS SMS Account Posture

Using the Task-3 pre-work baseline:

- **If `IsInSandbox` = true** (likely — this account has never sent production SMS via SNS):
  ```bash
  aws sns list-sms-sandbox-phone-numbers
  # If Tom's number is absent or not Verified:
  aws sns create-sms-sandbox-phone-number --phone-number <TOM_PHONE_E164>
  # → Tom's phone receives a sandbox verification code. ASK TOM for it (wait point), then:
  aws sns verify-sms-sandbox-phone-number --phone-number <TOM_PHONE_E164> --one-time-password <CODE_FROM_TOM>
  ```
  While sandboxed, SNS SMS (and therefore Cognito SMS MFA) delivers **only** to verified sandbox numbers — sufficient for the Step-7 smoke (Tom's phone) but **not** for real beta users. Moving out of the sandbox requires an AWS Support case → **do not open it yourself**; record it in your Completion Summary as a pre-Charter-beta Tom action.
- **`MonthlySpendLimit`**: if absent or < `5.00`:
  ```bash
  aws sns set-sms-attributes --attributes MonthlySpendLimit=25
  ```
  $25/mo is a ceiling, not a charge (≈3,800 OTPs); note the value you set in the summary.
- **If `IsInSandbox` = false**: confirm `MonthlySpendLimit ≥ 5` and move on.

Ask Tom for `<TOM_PHONE_E164>` before this task if you don't already have it.

---

## Task 5 — Smoke A: Direct SNS Delivery (account-posture proof, independent of Cognito)

```bash
aws sns publish --phone-number <TOM_PHONE_E164> \
  --message "Pilot MFA smoke: SNS SMS delivery path OK (MFA-WIRE-1 Step 0)"
```

Wait point: **Tom confirms receipt.** No receipt → do not proceed to Task 6; diagnose sandbox/number-verification state first.

---

## Task 6 — Smoke B: Cognito→SNS End-to-End OTP (the real pipe)

The `prod_web` app client allows `USER_PASSWORD_AUTH` (verified `modules/security/main.tf`), but the cleanest path needs no new Cognito user: use **Tom's real account** and a short-lived access token.

1. **Ask Tom for a fresh access token** (valid 1h — work promptly): Tom signs in at `app.pilotfortrades.com` → browser devtools → Application → Local Storage → copies the `CognitoIdentityServiceProvider.<clientId>.<username>.accessToken` value and pastes it to you.
2. **Capture current state** (so you can restore it):
   ```bash
   aws cognito-idp get-user --access-token <TOM_ACCESS_TOKEN> \
     --query 'UserAttributes[?Name==`phone_number`].Value' --output text
   # Record the prior value (or empty).
   ```
3. **Trigger the Cognito attribute-verification SMS** (rides the pool's new `SmsConfiguration`):
   ```bash
   aws cognito-idp update-user-attributes --access-token <TOM_ACCESS_TOKEN> \
     --user-attributes Name=phone_number,Value=<TOM_PHONE_E164>
   aws cognito-idp get-user-attribute-verification-code --access-token <TOM_ACCESS_TOKEN> \
     --attribute-name phone_number
   # → Tom's phone receives a real Cognito OTP SMS via SNS. THE MOMENT OF TRUTH.
   ```
   **If this errors with `InvalidSmsRoleAccessPolicyException` / `InvalidSmsRoleTrustRelationshipException`** → the Task-1 Terraform did not apply as expected → STOP, re-check Task 3 output; do not paper over.
4. **Prove both directions** — Tom reads you the code:
   ```bash
   aws cognito-idp verify-user-attribute --access-token <TOM_ACCESS_TOKEN> \
     --attribute-name phone_number --code <CODE_FROM_TOM>
   ```
5. **Restore** Tom's `phone_number` to the value captured in step 2 (or remove it if it was empty: `aws cognito-idp admin-delete-user-attributes` requires admin — instead set it back via `update-user-attributes` to the prior value; if there was no prior value, note it and leave the verified phone in place — harmless, and it pre-stages Tom's SMS MFA enrollment).

> **Fallback (not recommended)**: a throwaway `admin-create-user` + `initiate-auth` USER_PASSWORD_AUTH flow also works, but confirming a new user fires the Post-Confirmation Lambda (RDS provisioning side effects) and requires prod-DB cleanup. Only use it if Tom prefers, and flag the cleanup explicitly.

---

## Task 7 — Doc Updates (same change)

- [`aws-cognito-prod-setup.md`](../aws-cognito-prod-setup.md): replace the console-era SNS-role guidance with the Terraform-managed reality — role `CognitoSNSRole-pilot-production` + `sms_configuration` live in `modules/security/main.tf` (MFA-WIRE-1 Step 0, 2026-08-16), external_id `pilot-prod-cognito-sms`, verification + smoke commands from Tasks 3/5/6.
- [`aws-ops-runbook.md`](../aws-ops-runbook.md): add a "Cognito SmsConfiguration (MFA-WIRE-1)" row to the §14 extra-steps table + a short subsection mirroring the plan-gate/apply/verify procedure, leading with the **three-deltas-only** plan expectation.
- [`aws-infrastructure-as-built.md`](../aws-infrastructure-as-built.md): new IAM role + inline policy, pool `sms_configuration`, SNS posture (sandbox state + `MonthlySpendLimit` value + Tom's verified sandbox number if applicable), smoke evidence date.

---

## Rollback

Cognito offers **no detach** for `SmsConfiguration` once set (CLI/Terraform cannot null it). This is acceptable: the configuration is **inert** unless a user actually enables SMS MFA — and if it is broken, Part A surfaces a one-read 503 `sms_delivery_not_configured`. Removing the block from Terraform after apply would cause a perpetual plan diff — **keep it in state**. If the role/policy is misconfigured, **fix forward via Terraform**; deleting the IAM role would re-break SMS delivery (and be caught by the same 503).

---

## Definition of Done

- [ ] Pre-work baseline captured: `SmsConfiguration` null (or STOP happened), `IsInSandbox` recorded, `MonthlySpendLimit` recorded
- [ ] Terraform: `aws_iam_role.cognito_sns` + `aws_iam_role_policy.cognito_sns_publish` + pool `sms_configuration` + `cognito_sms_external_id` variable — plan showed **ONLY** those three deltas (anything else → stopped and asked Tom)
- [ ] Apply clean; `describe-user-pool` shows `SnsCallerArn` + `ExternalId` + `SnsRegion`
- [ ] SNS posture: sandbox state known; Tom's number verified (if sandboxed); `MonthlySpendLimit` ≥ 5 (value set recorded)
- [ ] Smoke A: direct `sns publish` delivered to Tom's phone (Tom confirmed)
- [ ] Smoke B: real Cognito OTP SMS delivered + `verify-user-attribute` succeeded; Tom's `phone_number` attribute restored/recorded
- [ ] Three doc updates applied (cognito-setup, runbook §14, as-built)
- [ ] Out-of-sandbox AWS Support case flagged to Tom as a pre-Charter-beta action (recorded in summary; not opened by you)
- [ ] Completion Summary added to `pilot-launch-plan.md` _(private)_ Appendix C: `### MFA-WIRE-1 (Step 0) — Cognito SmsConfiguration Pre-Flight (DevOps): Completion Summary` (standard format: Completed / Mode / What Was Accomplished / Infra Changed / Docs Updated / Verification incl. both smoke-test evidences + SNS posture)
