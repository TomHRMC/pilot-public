# AWS Cognito Production User Pool — Setup Guide

**Created**: June 30, 2026
**Status**: LIVING — pool as-built + ops addenda (Post-Authentication Lambda, device tracking, SMS `SmsConfiguration`/SNS posture, ADR-0015 toll-free path, AWS Support case detail, COGNITO-EMAIL-1 Custom Email Sender — ✅ LIVE 2026-09-03, 2026-09-04 `update-user-pool` config-drift incident + the full-carry rule). Updated whenever the prod pool config or its ops posture changes. Slated to become `aws-cognito-env-setup.md` (QA + prod) in QA-ENV-1 (launch plan §2.4).
**Account**: HotRMC (`owner@example.com` · `000000000000`)  
**Region**: `us-east-1`  
**Reference**: `mvp-arch.md §4.1`

---

## Overview

This document provides step-by-step AWS Console instructions for creating the production Cognito user pool. The production pool is **completely separate** from the dev pool (`pilot-dev` / `us-east-1_XXXXXXXXX`).

Once created, fill in the **Resulting IDs** table at the bottom of this document and update `aws-deployment-plan-v1.md §2.2`.

> **Why console (not Terraform yet)**: The Cognito pool must exist before Terraform infrastructure is written, because the pool ID and app client ID are needed as Terraform variable values. Creating it manually now via console, then importing into Terraform later via `terraform import`, is the correct order of operations for a first deployment.

---

## Step-by-Step: Create the Production User Pool

### Step 1 — Navigate to Cognito

AWS Console (`pilot-admin` credentials) → Search "Cognito" → **Amazon Cognito** → **User pools** → **Create user pool**

---

### Step 2 — Authentication Providers (Page 1)

| Setting | Value | Why |
|---|---|---|
| **Cognito user pool sign-in options** | ☑ **Email** only | Per `mvp-arch.md §4.1`; email is the primary identifier |
| **User name requirements** | Leave unchecked | Do not enable username — email only |

Click **Next**.

---

### Step 3 — Security Requirements (Page 2)

**Password policy:**

| Setting | Value |
|---|---|
| Password policy mode | **Custom** |
| Minimum password length | **12** |
| Contains at least 1 uppercase letter | ☑ Required |
| Contains at least 1 lowercase letter | ☑ Required |
| Contains at least 1 number | ☑ Required |
| Contains at least 1 special character | ☑ Required |
| Temporary password expiration | **7 days** |

**Multi-factor authentication:**

| Setting | Value | Why |
|---|---|---|
| MFA enforcement | **Optional MFA** | Per `mvp-arch.md §4.5`; MFA enforcement is handled per-tenant in the application layer, not at the Cognito pool level |
| MFA methods | ☑ **Authenticator apps (TOTP)** | Primary MFA method |
| MFA methods | ☑ **SMS message** | Secondary MFA method; requires phone number |

> **Note on SMS MFA**: Cognito will prompt you to set up an IAM role for SNS to send SMS messages. Create the role when prompted (AWS will auto-generate it). This is required to support SMS OTP as per `mvp-arch.md §4.5`.

**User account recovery:**

| Setting | Value |
|---|---|
| Self-service account recovery | ☑ **Enable self-service account recovery** |
| Recovery message delivery | **Email only** |

Click **Next**.

---

### Step 4 — Sign-Up Experience (Page 3)

**Self-registration:**

| Setting | Value | Why |
|---|---|---|
| Self-registration | **Disable self-registration** | ☑ Check this box | Per `mvp-arch.md §4.4`; user accounts are created programmatically via our API signup flow, not via the Cognito hosted UI |

**Attribute verification:**

| Setting | Value |
|---|---|
| Cognito-assisted verification and confirmation | **Send email message, verify email address** |
| Attributes to verify | ☑ **Email** |
| Verifying attribute changes | **Keep original attribute value active when an update is pending** |

**Required attributes:**

| Setting | Value | Why |
|---|---|---|
| Required attributes | **email** | Email only — name/phone are stored in our database, not Cognito |

> Do NOT add `name`, `phone_number`, or other standard attributes as required. Our `user` table in RDS stores this data. Keeping Cognito lean reduces sync complexity.

Click **Next**.

---

### Step 5 — Message Delivery (Page 4)

**Email provider:**

| Setting | Value | Why |
|---|---|---|
| Email provider | **Send email with Cognito** | Cognito's built-in email sender; free up to 50 emails/day which is sufficient for MVP onboarding. **Do not configure SES yet** — SES setup is a post-launch optimization |
| FROM email address | `no-reply@verificationemail.com` (Cognito default) | Acceptable for MVP; can customize to `noreply@pilotfortrades.com` via SES later |

**SMS:**

> ⚠️ **Doc drift corrected (MFA-WIRE-1, 2026-08-16)**: The original console-era
> guidance below said to create the SNS role via the Cognito console wizard. **The
> role was never actually created** — the pool shipped without an `SmsConfiguration`,
> so SMS MFA OTPs could never be delivered (Cognito would throw
> `InvalidSmsRole*Exception` on enrollment). The role + `SmsConfiguration` are now
> **Terraform-managed** — see the "MFA-WIRE-1 — Cognito SMS Delivery (SNS Role +
> SmsConfiguration)" section below for the current source of truth.

| Setting | Value |
|---|---|
| SMS role | ~~Create a new IAM role (auto-generated)~~ → **Terraform-managed** (`aws_iam_role.cognito_sns` in `modules/security/main.tf`) |
| IAM role name | `CognitoSNSRole-pilot-production` (now real, Terraform-created 2026-08-16) |

Click **Next**.

---

### Step 6 — Integrate Your App (Page 5)

**User pool name:**

| Setting | Value |
|---|---|
| User pool name | **`pilot-production`** |

**Hosted authentication pages:**

| Setting | Value | Why |
|---|---|---|
| Use the Cognito Hosted UI | **Do NOT check this** | We use AWS Amplify with our own login UI — no hosted UI needed |

**App type:**

| Setting | Value | Why |
|---|---|---|
| App type | **Single-page application (SPA)** | Amplify is a public browser client — cannot store a client secret. "Traditional web application" would generate a secret that Amplify cannot use |

**App client name:**

| Setting | Value |
|---|---|
| App client name | **`pilot-web-prod`** |

**Client secret:**

| Setting | Value |
|---|---|
| Client secret | **(none)** — SPA type automatically creates a public client with no secret |

**Authentication flows** — click "Advanced app client settings" to expand:

| Flow | Enable? | Why |
|---|---|---|
| `ALLOW_USER_SRP_AUTH` | ☑ **Yes** | Web app (Next.js) default auth flow |
| `ALLOW_USER_PASSWORD_AUTH` | ☑ **Yes** | Required for mobile (Expo Go cannot use SRP) |
| `ALLOW_REFRESH_TOKEN_AUTH` | ☑ **Yes** | Required for session refresh |
| `ALLOW_ADMIN_USER_PASSWORD_AUTH` | ☐ No | Server-side only; not needed |
| `ALLOW_CUSTOM_AUTH` | ☐ No | Not needed |

**Token expiration** (expand "Advanced app client settings"):

| Token | Expiration | Unit |
|---|---|---|
| Access token | **60** | minutes |
| ID token | **60** | minutes |
| Refresh token | **30** | days |

> **Why 30-day refresh token**: Mobile app may be offline for up to 72 hours (per `mvp-arch.md §4.6`). A 30-day refresh window means techs returning from extended offline periods (vacation, remote jobs) don't get locked out. Do NOT reduce this below 7 days.

Click **Next**.

---

### Step 7 — Review and Create (Page 6)

Review all settings. Confirm:
- ✅ User pool name: `pilot-production`
- ✅ Sign-in: Email
- ✅ Self-registration: Disabled
- ✅ Password: 12 chars, all four character types required
- ✅ MFA: Optional
- ✅ App type: Single-page application (no secret)
- ✅ App client name: `pilot-web-prod`
- ✅ Auth flows include `ALLOW_USER_SRP_AUTH` + `ALLOW_USER_PASSWORD_AUTH` + `ALLOW_REFRESH_TOKEN_AUTH`
- ✅ Refresh token: 30 days

Click **Create user pool**.

---

## Step 8 — Record the Resulting IDs

After creation, record the Pool ID and App Client ID here and update `aws-deployment-plan-v1.md §2.2`:

| Value | ID |
|---|---|
| **User Pool ID** | `us-east-1_XXXXXXXXX` |
| **App Client ID** | `xxxxxxxxxxxxxxxxxxxxxxxxxx` |
| **JWKS URL** | `https://cognito-idp.us-east-1.amazonaws.com/us-east-1_XXXXXXXXX/.well-known/jwks.json` |

---

## Step 9 — Update Backend Configuration

Once the pool is created, add these values to `pilot/prod/cognito` in AWS Secrets Manager:

```bash
aws secretsmanager create-secret \
  --name "pilot/prod/cognito" \
  --description "Cognito production user pool IDs" \
  --secret-string '{
    "region": "us-east-1",
    "user_pool_id": "us-east-1_XXXXXXXXX",
    "app_client_id": "xxxxxxxxxxxxxxxxxxxxxxxxxx"
  }' \
  --region us-east-1
```

---

## Step 10 — Update Frontend Configuration

These env vars go in the **production environment** of each frontend app. They are public values (not secrets) — the pool ID and client ID are safe to use in frontend code.

**`frontend/apps/web/.env.production`** (or set in App Runner environment variables):
```env
NEXT_PUBLIC_COGNITO_USER_POOL_ID=us-east-1_XXXXXXXXX
NEXT_PUBLIC_COGNITO_APP_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
NEXT_PUBLIC_COGNITO_REGION=us-east-1
```

**`frontend/apps/mobile/.env.production`** (or set via EAS build secrets):
```env
EXPO_PUBLIC_COGNITO_USER_POOL_ID=us-east-1_XXXXXXXXX
EXPO_PUBLIC_COGNITO_APP_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
EXPO_PUBLIC_COGNITO_REGION=us-east-1
```

---

## Step 11 — Post-Confirmation Lambda (SIGNUP-GA-1, ADR-0011)

The Post-Confirmation Lambda trigger is **LIVE** as of SIGNUP-GA-1 (2026-07-30). The deployed function `pilot-production-post-confirmation` is a **3-path router** (not the old placeholder stub):

- **Path 1** — existing/platform user → no-op (idempotent re-fire safety).
- **Path 2** — pending `tenant_user_invite` → create `user`, attach `tenant_user` to the invite's tenant, set `accepted_at`.
- **Path 3** — new owner (self-serve GA) → create `tenant` (placeholder name `"{local}'s Company"`), owner `user`, `tenant_user(owner)`.

The handler never raises to Cognito (all errors are logged + swallowed). It resolves the DB connection at runtime from `DB_SECRET_ARN` via boto3 (no secret in IaC state). See [`backend/lambda/post_confirmation/handler.py`](../../backend/lambda/post_confirmation/handler.py).

### Trigger wiring (manual — lambda_config is in Terraform `ignore_changes`)

`lambda_config` is deliberately kept in the pool's `lifecycle.ignore_changes` so Terraform does not manage the trigger link (avoids forcing pool replacement / clobbering other triggers). The trigger is wired manually via CLI after the Lambda deploys:

> ⚠️ **Superseded command removed 2026-09-04**: the historical PostConfirmation-only wiring command that lived here omitted `--auto-verified-attributes` + `--device-configuration`, and `update-user-pool` RESETS omitted blocks (the full-carry rule — see the 2026-09-04 incident addendum below). For any trigger wiring today, use the canonical full-carry command in [`aws-ops-runbook.md`](aws-ops-runbook.md) **§14.5 Step 5** (all three triggers + `KMSKeyID` + device + auto-verify in ONE call).

> ⚠️ `update-user-pool` overwrites the **entire** `LambdaConfig` block — if other triggers are configured, include them all in the same call. Verify with `aws cognito-idp describe-user-pool --user-pool-id us-east-1_XXXXXXXXX --query 'UserPool.{LC: LambdaConfig, AutoVerified: AutoVerifiedAttributes, Device: DeviceConfiguration}'` before and after — `AutoVerified` must be `["email"]` and `Device` non-null, never just the trigger list.

### Post-Authentication Lambda + Device Tracking (PLATFORM-SMS-B2, ADR-0013)

The Post-Authentication Lambda trigger is **LIVE** as of PLATFORM-SMS-B2 (2026-08-16). The deployed function `pilot-production-post-authentication` fires on every successful Cognito authentication (after MFA) and gates on `event.request.newDeviceUsed` — populated only because device tracking is set to **"Always remember"**. On a new-device sign-in it enqueues the existing B1 task (`send_platform_account_notification_sms`) directly to the Redis broker via a minimal Celery producer (kombu transport), which fans out to all verified+opted-in owner endpoints (Sample 3 — new-device security alert). See [`backend/lambda/post_authentication/handler.py`](../../backend/lambda/post_authentication/handler.py).

**Device tracking posture**: `ChallengeRequiredOnNewDevice=false` (we want the `newDeviceUsed` signal, not an extra challenge), `DeviceOnlyRememberedOnUserPrompt=false` (remember every device automatically).

**⚠️ Whole-block overwrite warning — THREE reset-prone blocks**: `update-user-pool` replaces the ENTIRE `LambdaConfig` and RESETS `--device-configuration` and `--auto-verified-attributes` to empty when omitted (2026-08-16: a device-only call cleared `LambdaConfig`, detaching both triggers; 2026-09-04: a lambda-only call cleared `AutoVerifiedAttributes` — SignUps sent no verification codes for ~19 h). The command below is the current full-carry form (supersedes the original 2-trigger version — the live set since COGNITO-EMAIL-1 is THREE triggers + `KMSKeyID`):

```bash
# ⚠️  ONE call carrying all five elements: auto-verify + device + all triggers + KMSKeyID.
POST_CONFIRM_ARN=$(aws lambda get-function --function-name pilot-production-post-confirmation \
  --query 'Configuration.FunctionArn' --output text)
POST_AUTH_ARN=$(aws lambda get-function --function-name pilot-production-post-authentication \
  --query 'Configuration.FunctionArn' --output text)
CES_ARN="arn:aws:lambda:us-east-1:000000000000:function:pilot-production-custom-email-sender"
KMS_ARN="arn:aws:kms:us-east-1:000000000000:key/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxx1"

aws cognito-idp update-user-pool --user-pool-id us-east-1_XXXXXXXXX \
  --auto-verified-attributes email \
  --device-configuration ChallengeRequiredOnNewDevice=false,DeviceOnlyRememberedOnUserPrompt=false \
  --lambda-config "PostConfirmation=${POST_CONFIRM_ARN},PostAuthentication=${POST_AUTH_ARN},CustomEmailSender={LambdaArn=${CES_ARN},LambdaVersion=V1_0},KMSKeyID=${KMS_ARN}"

# Verify
aws cognito-idp describe-user-pool --user-pool-id us-east-1_XXXXXXXXX \
  --query 'UserPool.{LC: LambdaConfig, Device: DeviceConfiguration, AutoVerified: AutoVerifiedAttributes}'
# Expect: ALL THREE trigger ARNs + KmsKeyId present; DeviceConfiguration shows tracking on,
#         always-remember; AutoVerified ["email"]. Any null → restore (same command) and STOP.
```

**Operational heads-up**: when device tracking flips on, each user's **first** sign-in per device reads as "new" and fires the alert once per owner endpoint; it settles as devices are remembered. Expected — not a defect.

**Rollback** (detach the Post-Authentication trigger, leave the function deployed but inert):

```bash
# ⚠️ Full-carry rule applies to rollbacks too — carry auto-verify + device + every
#    trigger that must STAY attached (here: PostConfirmation + CustomEmailSender + KMSKeyID):
aws cognito-idp update-user-pool --user-pool-id us-east-1_XXXXXXXXX \
  --auto-verified-attributes email \
  --device-configuration ChallengeRequiredOnNewDevice=false,DeviceOnlyRememberedOnUserPrompt=false \
  --lambda-config "PostConfirmation=${POST_CONFIRM_ARN},CustomEmailSender={LambdaArn=${CES_ARN},LambdaVersion=V1_0},KMSKeyID=${KMS_ARN}"
# Optionally also disable tracking (still carry auto-verify + full lambda-config in the same call):
#   --device-configuration ChallengeRequiredOnNewDevice=false,DeviceOnlyRememberedOnUserPrompt=true
```

### MFA-WIRE-1 — Cognito SMS Delivery (SNS Role + SmsConfiguration)

**Status**: ✅ Infrastructure wiring COMPLETE (2026-08-16) · ✅ AWS Support case RESOLVED 2026-08-25 (sandbox exited + $25 monthly quota, us-east-1) · ✅ `MonthlySpendLimit` attribute = 25 verified + default type `transactional` + sender ID `Pilot` (2026-08-25 — sender ID is ignored for US destinations; messages arrive from the TFN) · ✅ TFN **+18445550100** self-provisioned (2026-08-25) · 🔄 toll-free verification form IN PROGRESS → then Tasks 4–6 below

The production pool was console-created on 2026-06-30 with `mfa_configuration = OPTIONAL` and both TOTP + SMS factors enabled, but **no `SmsConfiguration`** — there was no SNS IAM role, so Cognito could not deliver SMS MFA OTPs. Any real SMS enrollment would have failed with `InvalidSmsRole*Exception`. MFA-WIRE-1 (Step 0) closed this gap by making the SNS role + `SmsConfiguration` Terraform-managed.

**Terraform-managed resources** (in [`infrastructure/terraform/modules/security/main.tf`](../../infrastructure/terraform/modules/security/main.tf)):

| Resource | Purpose |
|---|---|
| `aws_iam_role.cognito_sns` | IAM role `CognitoSNSRole-pilot-production` — trust policy allows `cognito-idp.amazonaws.com` to assume it, gated by `sts:ExternalId` = `pilot-prod-cognito-sms` |
| `aws_iam_role_policy.cognito_sns_publish` | Inline policy granting `sns:Publish` (resource `*` — SNS phone-number-targeted SMS has no resource-level scoping; this is AWS's documented form) |
| `aws_cognito_user_pool.prod` → `sms_configuration` block | Wires the role to the pool: `external_id`, `sns_caller_arn`, `sns_region = us-east-1` |
| `variable.cognito_sms_external_id` | The ExternalId — a **configuration value, not a secret** (lives in Terraform, not Secrets Manager per secret-management-policy §1) |

**Plan gate**: `terraform plan -target=module.security` must show **exactly 3 deltas** — `+ aws_iam_role.cognito_sns` (create), `+ aws_iam_role_policy.cognito_sns_publish` (create), `~ aws_cognito_user_pool.prod` (update in-place, `+ sms_configuration`). Anything else → STOP. Pool replacement is an immediate stop (`deletion_protection = ACTIVE`).

**Verify wiring after apply**:

```bash
aws cognito-idp describe-user-pool --user-pool-id us-east-1_XXXXXXXXX \
  --query 'UserPool.SmsConfiguration.{SnsCallerArn: SnsCallerArn, ExternalId: ExternalId, SnsRegion: SnsRegion}'
# Expect: SnsCallerArn = arn:aws:iam::000000000000:role/CognitoSNSRole-pilot-production
#         ExternalId  = pilot-prod-cognito-sms
#         SnsRegion   = us-east-1
```

**Verified live 2026-08-16T21:46Z**: all three fields present and correct.

#### SMS Delivery Smokes — account UNBLOCKED 2026-08-25; pending toll-free number provisioning + verification

> **State table below is as of case time (2026-08-17)** — resolved 2026-08-25: sandbox exited, $25 monthly quota applied (us-east-1). AWS's resolution note: the account-level `MonthlySpendLimit` **attribute** must still be set via the SNS console/API (effective spend = lower of quota vs attribute; the attribute was $1), and US toll-free numbers are **self-provisioned** (Amazon End User Messaging).

The infrastructure wiring is complete. At case time (2026-08-17), **no SMS could be sent from this account**. The SNS SMS account had:

| Posture | Value | Impact |
|---|---|---|
| `IsInSandbox` | `true` | SNS SMS only delivers to verified sandbox numbers |
| Origination numbers | **none** (`list-origination-numbers` → empty) | **No SMS can be sent at all** — even `create-sms-sandbox-phone-number` fails with `No origination entities available to send` |
| `MonthlySpendLimit` | `$1` (account default) | Cannot be raised while sandboxed — AWS rejects any value > 1 with "reach out to support" |

This is a chicken-and-egg: an origination number is required to send the sandbox verification code, but origination numbers cannot be requested while sandboxed. **All three require a single AWS Support case** (SNS SMS production access request).

**The Support case (SUBMITTED 2026-08-17 — account `000000000000`)** requested all three in one case (AWS Console → Support → Create case → Account and billing → Service limit increase, "SNS SMS production access"): (1) move out of the SNS SMS sandbox (production access), (2) provision a **US toll-free origination number** — Tom then completes **toll-free verification** declaring the 2FA/OTP use case, (3) raise `MonthlySpendLimit` to **$25** (a ceiling, not a charge — ≈3,800 OTPs at ~$0.00645/segment; the sandbox caps it at $1).

> **Use case statement (as filed — copy-paste for the toll-free verification form)**: "Pilot for Trades is a SaaS platform for electrical contractors. We use Amazon Cognito for user authentication with SMS MFA (one-time passwords) as a secondary factor. Cognito delivers SMS OTPs via Amazon SNS. We need production SNS SMS access to deliver MFA OTPs to our beta users' mobile phones. Expected volume: ~300 OTPs/month during beta (100 users × ~3 OTPs/month). We request a MonthlySpendLimit of $25 and a US toll-free origination number for 2FA/OTP delivery (we will complete toll-free verification)."
>
> **Answers on file with AWS (2026-08-17)** — opt-in process: user self-enrolled double opt-in (user enables SMS MFA in account security settings → enters own mobile number → must verify with a code before activation; no marketing traffic; self-service Remove). Message templates: Cognito AWS defaults ("Your verification code is {####}." enrollment verification; "Your authentication code is {####}." sign-in OTP). **Reuse the same answers on the toll-free verification form.**

**Next Tom actions (case RESOLVED 2026-08-25 — in order)**: (1) ✅ DONE 2026-08-25 — `MonthlySpendLimit` attribute = 25 verified; default sending type `transactional`; sender ID `Pilot` (ignored for US destinations — messages arrive from the TFN). (2) ✅ DONE 2026-08-25 — TFN **+18445550100** self-provisioned (Amazon End User Messaging, us-east-1; ~$2/mo + ~$0.00645/segment ≈ $4/mo at beta volume). (3) 🔄 IN PROGRESS — submit the **toll-free verification (800-number) form** — final recommended answers below (US carriers block unverified TFN traffic; review can take several business days). (4) ☐ Run Tasks 4–6 below once verification is approved.

> **Toll-free verification form — recommended answers (2026-08-25; annotate "as submitted" after filing)**:
> - **Company name**: the legal entity must match the EIN record exactly. If the form has separate Legal Name + DBA/Brand fields → Legal = `Example Holdings, LLC` (exactly as the IRS record), DBA/Brand = `Pilot for Trades`. If a single field → `Example Holdings, LLC, dba Pilot for Trades` (ties the EIN entity to the public brand reviewers will see). **Website**: `https://pilotfortrades.com` (live; carries `/legal/sms-terms` + privacy pages).
> - **Opt-in process description** (≤500 chars as filed — matches the shipped MFA screens: web `frontend/packages/ui/src/mfa-enrollment-wizard/web/MFAEnrollmentWizard.tsx` + mobile `apps/mobile/.../security/mfa.tsx`, DLC-2; the uploaded screenshot shows the disclosure verbatim on the Set-up screen): "Pilot for Trades is an authenticated SaaS app — no public form collects numbers. A logged-in user opts in at Account → Security → Enable SMS MFA, entering their own number. The screen shows the consent disclosure (see attached screenshot): consent to one-time codes, frequency, msg & data rates, STOP/HELP, privacy link. MFA activates only after the user enters the code sent to that number (double opt-in). Users can disable MFA anytime. Authentication codes only — no marketing." (480 chars)
> - **Use-case statement (≤500 chars as filed 2026-08-25)**: "Pilot for Trades is a SaaS platform for trade-services contractors. We use Amazon Cognito for user authentication with SMS MFA (one-time passcodes) as an optional secondary factor; Cognito delivers these OTPs via Amazon SNS. This US toll-free number is used exclusively to deliver authentication one-time passcodes (enrollment verification and sign-in challenges) to our users' mobile phones, user-initiated, event-driven messages only; no marketing or promotional traffic." — **Volume note**: if the form has a separate monthly-volume field, enter `~300 OTPs/month` there; if not, append "Expected volume: ~300 OTPs/month." to the statement (still ≤500 chars).
> - **Sample messages (as filed 2026-08-25 — submit 2 of the 3 slots; these are the only two message types this number sends)**: the pool's two SMS templates are **customized ✅ 2026-08-25** (console done — both SMS templates; ✅ **Terraform codified 2026-08-26** — C-B16-OPS Step 0; `sms_authentication_message` + `sms_verification_message` now in [`modules/security/main.tf`](../../infrastructure/terraform/modules/security/main.tf) `aws_cognito_user_pool.prod`; the next security-module apply will no longer revert them). **`auth_session_validity` note**: neither the Terraform AWS provider (v5.100.0) nor the AWS CLI `update-user-pool` command expose `auth_session_validity` — it is a **console-only setting**. The live value is `null` (Cognito default = 3 min). The "5" Tom previously set on the app client page was the app client token TTL (a separate setting). To set the pool-level `AuthSessionValidity = 5`, Tom must do it in the AWS Console (User Pool → look for "Authentication flow session duration"). The SMS templates are the codified values; `auth_session_validity` is tracked as a console-only follow-up. The filed samples match the live templates verbatim: **Sample 1 (required)** — sign-in OTP: `Your Pilot for Trades authentication code is {####}. It expires in 5 minutes.` · **Sample 2 (optional slot 1)** — enrollment verification: `Your Pilot for Trades verification code is {####}. It expires in 24 hours.` (Cognito attribute-verification codes are 24h-valid) · **Leave slot 3 empty** — no third message type exists. Rules: samples must match reality; each template must contain `{####}` and stay ≤140 chars. **Email "Verification message" template**: intentionally LEFT AS DEFAULT (2026-08-25) — it becomes dead config once the COGNITO-EMAIL-1 custom sender is active (Cognito stops rendering it; our Lambda's branded template replaces it), and customizing it now would not fix deliverability (spam placement is DKIM/domain-based, not template-based).
> - **Screenshot evidence plan (2026-08-25)**: (1) MFA Set-up screen — disclosure verbatim above **Send code** — uploaded ✅. (2) Signup legal-checkbox page (`frontend/apps/web/src/features/signup/components/LegalCheckboxGroup.tsx`) — shows account-level Terms + Privacy acceptance at signup; covers the T&C-link element. **Do NOT** use the "Stay Informed" marketing-consent screenshot — that is the Telnyx Pathway-C marketing stream, a different use case; mixing streams confuses the review.
> - **Required-elements coverage (help-section list)**: brand ✓ (screen) · privacy link ✓ (screen) · frequency ✓ (screen) · opt-out ✓ (screen) · HELP ✓ (screen) · msg&data rates ✓ (screen) · T&C → signup acceptance (image 2) + public `/legal/terms` · customer care → `support@pilotfortrades.com` + `pilotfortrades.com/contact` (printed on `/legal/sms-terms` + `/legal/privacy`). Marketing-only checklist items (separate marketing checkbox, "consent not a condition of purchase") are N/A — 2FA/OTP-only number; SMS MFA is optional (TOTP always available), so consent is never a condition of use.
> - **Optional cover note** (comments/additional-info field, if present): "SMS MFA is optional (TOTP always available) — consent is never a condition of use. Terms + Privacy are accepted at account signup (second image) and public at pilotfortrades.com/legal/terms, /legal/privacy, /legal/sms-terms. Customer care: support@pilotfortrades.com · pilotfortrades.com/contact. This number sends 2FA/OTP codes only."
> - **If rejected on missing T&C link / care contact on the MFA screen**: apply the logged P3 polish item (launch plan §6c PLAT-DEBT — add Terms link + care contact to the disclosure strings), retake the screenshot, resubmit.

> **Origination decision (2026-08-17 — ADR-0015)**: the Support case requests a **US toll-free origination number**; Tom completes **toll-free verification** declaring the 2FA/OTP use case (no 10DLC brand/campaign in AWS at OTP-only volume). Contingency if the case stalls >~1 week or is rejected: Cognito Custom SMS Sender Lambda → Telnyx (see ADR-0015 + design doc §G-Q12). **Contingency MOOT — case resolved 2026-08-25 via the primary path.**

**Once the toll-free number is provisioned and verified**, run the three previously-blocked tasks:
1. **Task 4** — set the `MonthlySpendLimit` attribute to 25 (part of step (1) above; the sandbox-verified-number step is moot — the account is in production mode).
2. **Task 5 (Smoke A)** — `aws sns publish --phone-number +14105550123 --message "Pilot MFA smoke: SNS SMS delivery path OK (MFA-WIRE-1 Step 0)"` → Tom confirms receipt.
3. **Task 6 (Smoke B)** — Cognito→SNS end-to-end OTP via Tom's access token: `update-user-attributes` (phone_number) → `get-user-attribute-verification-code` (phone_number) → Tom reads the code → `verify-user-attribute` → restore phone_number. See the batch prompt for the full command sequence.

> **Rollback note**: Cognito offers no detach for `SmsConfiguration` once set. The configuration is inert unless a user enables SMS MFA. If broken, Part A surfaces a 503 `sms_delivery_not_configured`. Keep the block in Terraform state — removing it causes a perpetual plan diff. Fix forward via Terraform; do not delete the IAM role.

### COGNITO-EMAIL-1 — Custom Email Sender (SendGrid) — ✅ LIVE 2026-09-03

**Status**: ✅ LIVE 2026-09-03 — Phase 1 batch (launch plan §3.15) · **Decision 2026-08-25 (Tom)**: SendGrid custom sender chosen over SES (avoids the SES production-access support-case wait; consolidates on the existing SendGrid vendor; branded auth/invite emails).

**Mechanism**: Cognito invokes the Custom Email Sender Lambda trigger (`CustomEmailSender`, `LambdaVersion=V1_0`) **instead of** sending its own auth emails. The Lambda (`pilot-production-custom-email-sender`) decrypts the KMS-encrypted code via the **AWS Encryption SDK** (envelope encryption — NOT raw `kms:Decrypt`; Cognito uses the Encryption SDK to encrypt, so the SDK is required to decrypt), renders a branded template (inline styles, Pilot brand, tracking-free), and sends via SendGrid (`noreply@pilotfortrades.com`, verified sender, DKIM in Cloudflare). `email_sending_account` stays `COGNITO_DEFAULT` — the CustomEmailSender trigger bypasses it; it is not changed.

**Triggers wired** (one CLI call, all three + KMSKeyID — ADR-0011 posture, `lambda_config` in `ignore_changes`):
- `PostConfirmation` = `arn:aws:lambda:us-east-1:000000000000:function:pilot-production-post-confirmation`
- `PostAuthentication` = `arn:aws:lambda:us-east-1:000000000000:function:pilot-production-post-authentication`
- `CustomEmailSender` = `{LambdaVersion=V1_0, LambdaArn=arn:aws:lambda:us-east-1:000000000000:function:pilot-production-custom-email-sender}`
- `KMSKeyID` = `arn:aws:kms:us-east-1:000000000000:key/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxx1` (alias `alias/pilot-production`)

**Lambda**: `pilot-production-custom-email-sender` · python3.12 · 512 MB · 30s timeout · no VPC (no RDS access — self-contained, design §B) · dedicated IAM role (least-privilege: `secretsmanager:GetSecretValue` on `pilot/prod/sendgrid` only; `kms:Decrypt` on `aws_kms_key.pilot` only; CloudWatch Logs). Env vars: `SENDGRID_SECRET_ARN`, `KMS_KEY_ARN`.

**Packaging**: [`infrastructure/scripts/build-custom-email-sender-lambda.sh`](../../infrastructure/scripts/build-custom-email-sender-lambda.sh) — `sendgrid==6.11.0` + `aws-encryption-sdk==4.0.6` + `aws-cryptographic-material-providers==1.11.3` (+ transitive: python-http-client, starkbank-ecdsa/ellipticcurve, cryptography, attrs, wrapt, DafnyRuntimePython, pytz, aws-cryptography-internal-*). boto3/botocore/s3transfer/urllib3/jmespath/python-dateutil/six are NOT packaged (runtime-provided — stripped after pip install).

**Alarm**: `pilot-production-custom-email-sender-errors` — CloudWatch `Errors ≥ 1` over 5 min → SNS alarms topic. Alarm description includes rollback instructions.

**Smoke evidence (2026-09-03)**: ForgotPassword to `owner@example.com` — branded email arrived in inbox (not spam). Gmail headers: `DKIM: PASS header.i=@pilotfortrades.com`, `SPF: PASS`, `DMARC: PASS`. Second account (tech under same tenant) SignUp also confirmed working. Alarm in OK state.

**⚠️ Key implementation note**: Cognito encrypts the auth code using the **AWS Encryption SDK** (envelope encryption format), NOT raw `kms:Encrypt`. The handler must use `aws_encryption_sdk.EncryptionSDKClient` with `commitment_policy=CommitmentPolicy.REQUIRE_ENCRYPT_ALLOW_DECRYPT` (Cognito uses Algorithm ID 888 — uncommitted messages; the SDK v4.x default `REQUIRE_ENCRYPT_REQUIRE_DECRYPT` rejects them). The SendGrid secret uses JSON key `api_key` (not `SENDGRID_API_KEY`).

**Rollback** (config-only, <1 min): `aws cognito-idp update-user-pool --auto-verified-attributes email --device-configuration ChallengeRequiredOnNewDevice=false,DeviceOnlyRememberedOnUserPrompt=false --lambda-config "PostConfirmation=<arn>,PostAuthentication=<arn>"` — Cognito instantly falls back to `COGNITO_DEFAULT` sending. The Lambda stays deployed, dormant. (The auto-verify + device flags are mandatory even in rollback — omitting them silently wipes both, per the 2026-09-04 incident addendum below.) **SES remains the documented no-code fallback** (SES production-access case + Easy DKIM into Cloudflare DNS) if the custom sender is ever abandoned.

### Build + deploy procedure

**Post-Confirmation / Post-Authentication**: See [`infrastructure/scripts/build-post-confirmation-lambda.sh`](../../infrastructure/scripts/build-post-confirmation-lambda.sh) / [`build-post-authentication-lambda.sh`](../../infrastructure/scripts/build-post-authentication-lambda.sh) — run before `terraform plan`/`apply` on the security module. They `pip install -t` Linux manylinux wheels (psycopg2-binary, sqlalchemy, sqlmodel, pydantic, pgvector, celery) + copy the handler source + `app/models` tree. boto3/botocore are NOT packaged (pre-bundled in the Lambda runtime).

**Custom Email Sender (COGNITO-EMAIL-1)**: See [`infrastructure/scripts/build-custom-email-sender-lambda.sh`](../../infrastructure/scripts/build-custom-email-sender-lambda.sh) — run before `terraform plan`/`apply` on the security module. It `pip install -t` `sendgrid==6.11.0` + `aws-encryption-sdk==4.0.6` + `aws-cryptographic-material-providers==1.11.3` (+ transitive deps) + copies `handler.py` + `templates.py`. Self-contained — NO `app/models` bundle (design §B). boto3/botocore and other runtime-provided packages are stripped after install. See [`aws-ops-runbook.md`](aws-ops-runbook.md) §14.5 for the full build → deploy → wire → verify → rollback procedure.

### ⚠️ 2026-09-04 — `update-user-pool` config-drift incident (resolved same day)

**What happened**: The COGNITO-EMAIL-1 trigger wiring on 2026-09-03 used `update-user-pool` carrying only `--lambda-config` (final of three `pilot-admin` calls, 17:26 EDT per CloudTrail). `UpdateUserPool` RESETS omitted blocks — long known for `lambda_config`/`device_configuration` (the 2026-08-16 incident), but **`auto_verified_attributes` resets on omission too** (newly confirmed by this incident). The call silently set `AutoVerifiedAttributes = []` and `DeviceConfiguration = null`. The smoke evidence above predates the final wiring call, so the drift went unnoticed overnight.

**Impact window** (2026-09-03 ~17:26 EDT → 2026-09-04 ~16:55 UTC):
- Cognito `SignUp` created users but sent **no verification code at all** (nothing in SendGrid, nothing in spam — nothing was ever sent); `ResendConfirmationCode` failed with `InvalidParameterException: Cannot resend codes. Auto verification not turned on.` Found during TEAM-INVITE-1 prod testing — the first SignUp after the drift. One UNCONFIRMED user resulted; recovered via resend after the restore (no teardown needed).
- Device tracking was off → the Post-Authentication new-device SMS alert (`newDeviceUsed` gate) could not fire. No alert backlog; tracking restored with the same call.
- NOT affected: `LambdaConfig` (all 3 triggers + `KMSKeyID`), `SmsConfiguration`, `MfaConfiguration`, password `Policies` — all survived omission.

**Restore**: ONE full-carry call — `--auto-verified-attributes email` + `--device-configuration ChallengeRequiredOnNewDevice=false,DeviceOnlyRememberedOnUserPrompt=false` + `--lambda-config` (all three triggers + `KMSKeyID`). Verified via describe; branded code delivered on resend; the invite accept completed end-to-end. Terraform already declared `auto_verified_attributes = ["email"]`, so the CLI restore also re-aligned live state with config (next `terraform plan` clean).

**The full-carry rule (binding for every future `update-user-pool` call on this pool)**: `lambda_config`, `device_configuration`, and `auto_verified_attributes` are the three reset-prone blocks — omitting any of them resets it to empty. Every wiring **and rollback** command must carry all three at their live values, with every live trigger inside `--lambda-config`. Post-update verify must check `AutoVerifiedAttributes == ["email"]` + `DeviceConfiguration` non-null + full `LambdaConfig` — never just the trigger list (the trigger-only verify was the blind spot that hid this for ~19 h). Canonical command + verify: [`aws-ops-runbook.md`](aws-ops-runbook.md) §14.5 Step 5.

---

## Differences from Dev Pool (`pilot-dev`)

| Setting | Dev Pool (`pilot-dev`) | Prod Pool (`pilot-production`) |
|---|---|---|
| Self-registration | Disabled | **Enabled (self-sign-up, ADR-0011)** — prod-only; dev stays admin-only |
| MFA | Disabled | Optional ✅ production-correct |
| Temp password expiry | 7 days | 7 days ✅ same |
| App type | SPA | SPA ✅ same |
| Auth flows | SRP + Password + Refresh | SRP + Password + Refresh ✅ same |
| Post-Confirmation Lambda | Not configured | **Deployed (3-path router, SIGNUP-GA-1)** — wired via CLI |
| Test users | `dev@pilot.local`, `tech@pilot.local`, `office@pilot.local` | None initially — real tenants only |

---

## Lessons Learned (from dev pool setup in `aws-cognito-setup.md`)

1. **App type must be SPA** — "Traditional web application" creates a client secret; Amplify cannot use it. Error: `Client X is configured with secret but SECRET_HASH was not received`

2. **Both SRP and Password auth must be enabled** — Mobile Expo Go requires `USER_PASSWORD_AUTH`; web uses `USER_SRP_AUTH`. Both must be on the same app client.

3. **Disable self-registration** — Our signup flow creates users programmatically via the API. Cognito self-registration bypasses our onboarding state machine (`mvp-arch.md §4.7`).

4. **Do not add a hosted UI** — We control the login UI via Amplify. The hosted UI is unnecessary overhead.
