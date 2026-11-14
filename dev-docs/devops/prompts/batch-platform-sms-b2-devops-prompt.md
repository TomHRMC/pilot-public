# Implementation Prompt: PLATFORM-SMS-B2 (Part 2) — Post-Authentication Lambda Deploy + Cognito Device-Tracking Wiring

**Mode**: Pilot DevOps Engineer
**Batch**: PLATFORM-SMS-B2 (Part 2 of 2 — deploy + wiring; runs AFTER Part 1)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` _(private)_ §2.4 PLATFORM-SMS-B2
**Design doc**: [`dev-docs/architecture-design/batch-designs/batch-platform-sms-b2-design.md`](../../architecture-design/batch-designs/batch-platform-sms-b2-design.md) ✅ APPROVED 2026-08-16
**Prerequisite**: Part 1 ([`batch-platform-sms-b2-python-engr-prompt.md`](../../implementation-prompts/fe-be-mob-batch-prompts/batch-platform-sms-b2-python-engr-prompt.md)) is **merged and green** — the handler at `backend/lambda/post_authentication/handler.py` exists with passing unit tests. Do not start without it.
**Estimated session**: ~1 hour
**Cost impact**: ~$0/mo (Lambda free tier at our sign-in volume; one log group under existing retention). No new AWS service; the ~$888.87/mo baseline is unchanged (design §J).

---

## ⚠️ MANDATORY STOP: Read These First

- **[`.roo/rules-pilot-devops-engineer/secret-management-policy.md`](../../../.roo/rules-pilot-devops-engineer/secret-management-policy.md)** — runtime secret fetch via IAM roles only; least-privilege ARN scoping (§4) governs the IAM change in Task 2.
- **[`.roo/rules-pilot-devops-engineer/blue-green-constraints.md`](../../../.roo/rules-pilot-devops-engineer/blue-green-constraints.md)** — mostly N/A here (no ECS traffic shift; no `DROP`/`ALTER COLUMN` in Part 1's data-only migration → no pre-deploy snapshot requirement is triggered). S3+DynamoDB state locking already applies.
- **[`aws-ops-runbook.md`](../aws-ops-runbook.md) §14.5** — the Post-Confirmation Lambda build/deploy/wire procedure this prompt mirrors step-for-step.
- **[`aws-cognito-prod-setup.md`](../aws-cognito-prod-setup.md) §11** — the manual-CLI wiring posture: `lambda_config` is in Terraform `ignore_changes` **on purpose**; trigger attachment is CLI-only; `update-user-pool --lambda-config` **overwrites the ENTIRE LambdaConfig block**.
- **The design doc** — §C (execution order steps 7–10), §F.3 (handler contract), §G-1 (whole-block overwrite warning + first-sign-in alert wave).

---

## Pre-Work: Read These Files

```
backend/lambda/post_authentication/handler.py           ← the Part-1 artifact you are packaging (verify it exists + merged)
infrastructure/scripts/build-post-confirmation-lambda.sh ← the build script Task 1 mirrors
infrastructure/terraform/modules/security/main.tf        ← post_confirmation Lambda block (~lines 739–799), lambda_execution role + its secrets inline policy (~lines 342–376), aws_secretsmanager_secret.redis (~line 45)
infrastructure/terraform/modules/security/outputs.tf     ← post_confirmation_lambda_arn output (~line 112) to mirror
infrastructure/terraform/modules/monitoring/main.tf      ← aws_cloudwatch_log_group.lambda_post_confirmation (~line 51) to mirror
infrastructure/terraform/modules/networking/main.tf      ← aws_security_group.sg_redis (~line 303) + sg_lambda (~line 409)
infrastructure/terraform/modules/compute/main.tf         ← line 222: the worker's CELERY_BROKER_URL comes from the redis secret's `broker_url` JSON key (confirms the key name the handler reads at runtime)
```

Also confirm the current live wiring before touching anything:

```bash
aws cognito-idp get-user-pool --user-pool-id <POOL_ID> \
  --query 'UserPool.[LambdaConfig,DeviceConfiguration]'
# Expect: LambdaConfig contains ONLY PostConfirmation today; DeviceConfiguration absent (tracking off).
```

---

## Task 1 — Build Script

Create `infrastructure/scripts/build-post-authentication-lambda.sh` by mirroring `build-post-confirmation-lambda.sh`:

- Build dir: `infrastructure/terraform/modules/security/build/post_authentication`
- Copy `backend/lambda/post_authentication/handler.py` → build root as `handler.py`; copy the `app/models` tree exactly as the post-confirmation script does (the handler imports `app.models.core` / `app.models.auth`).
- `pip install -t` the same Linux manylinux wheel set **plus `celery`** (the handler's broker producer): `psycopg2-binary sqlalchemy sqlmodel pydantic pgvector celery` — pydantic/pgvector stay because the `app.models` import tree needs them; celery pulls kombu transitively.
- boto3/botocore are **not** packaged (pre-bundled in the Lambda runtime) — same as post-confirmation.
- Update the script's header comments (batch ID, ADR-0013, what it produces). `chmod +x`.

Run it; confirm the build dir populates without error.

---

## Task 2 — Terraform: Security Module

In `infrastructure/terraform/modules/security/main.tf`, mirroring the post-confirmation block:

1. `data "archive_file" "post_authentication"` → `build/post_authentication` → `post_authentication.zip`.
2. `resource "aws_lambda_function" "post_authentication"`:
   - `function_name = "pilot-${var.environment}-post-authentication"`, `role = aws_iam_role.lambda_execution.arn`, `handler = "handler.handler"`, `runtime = "python3.12"`, `timeout = 30`, `memory_size = 256`, `source_code_hash` from the archive data source.
   - `environment.variables`: `ENVIRONMENT`, `DB_SECRET_ARN = aws_secretsmanager_secret.db.arn`, **`REDIS_SECRET_ARN = aws_secretsmanager_secret.redis.arn`** (the handler fetches this secret at runtime and reads its `broker_url` key — Lambda env vars cannot do ECS-style `arn:key::` extraction; this is deliberate), `COGNITO_USER_POOL_ID = var.cognito_user_pool_id`.
   - `vpc_config`: same `var.private_subnet_ids` + `[var.sg_lambda_id]`. `tracing_config { mode = "Active" }`. Tags mirror post-confirmation (`Component = "auth"`, etc.).
3. `resource "aws_lambda_permission" "cognito_post_authentication"`: `principal = "cognito-idp.amazonaws.com"`, `source_arn = aws_cognito_user_pool.prod.arn` (mirrors the post-confirmation permission).
4. **IAM widening (least-privilege, secret-management-policy §4)**: the role's inline secrets policy (`pilot-${var.environment}-lambda-rds`, ~line 366–376) currently allows `secretsmanager:GetSecretValue` on `[aws_secretsmanager_secret.db.arn]` only. Add `aws_secretsmanager_secret.redis.arn` to that `Resource` list. Do **not** rename the policy (rename = recreate) and do **not** wildcard the ARN.
5. `outputs.tf`: add `post_authentication_lambda_arn` mirroring the existing output.

## Task 3 — Terraform: Monitoring Module

In `infrastructure/terraform/modules/monitoring/main.tf`, mirror the post-confirmation group:

```hcl
resource "aws_cloudwatch_log_group" "lambda_post_authentication" {
  name              = "/aws/lambda/pilot-${var.environment}-post-authentication"
  retention_in_days = var.cloudwatch_log_retention_days
  # tags mirror lambda_post_confirmation
}
```

## Task 4 — Terraform: Networking Module

In `infrastructure/terraform/modules/networking/main.tf`, add one ingress rule to `aws_security_group.sg_redis` (~line 303):

```hcl
ingress {
  description     = "Redis from Cognito Lambdas (post-authentication broker enqueue)"
  from_port       = 6379
  to_port         = 6379
  protocol        = "tcp"
  security_groups = [aws_security_group.sg_lambda.id]
}
```

(This is the only networking change — the RDS SG already allows 5432 from `sg_lambda`.)

## Task 5 — Plan + Apply

```bash
./infrastructure/scripts/build-post-authentication-lambda.sh   # populate the build dir FIRST
# then the standard plan flow for the production environment (runbook §14.1/§14.2)
terraform plan
```

**Gate**: the plan must show ONLY — new archive/lambda/permission/log-group resources, the one SG ingress rule, and the IAM inline-policy delta (one ARN added). If `plan` shows anything else (drift, replacements) → **STOP and ask Tom** before applying. Apply per the standard process.

## Task 6 — Cognito Wiring (manual CLI — `lambda_config` stays in `ignore_changes`)

**⚠️ Whole-block overwrite warning (design §G-1)**: `update-user-pool --lambda-config` replaces the ENTIRE LambdaConfig. Omitting `PostConfirmation` silently detaches the live SIGNUP-GA-1 trigger. The command below carries **both**.

```bash
# 1. Enable device tracking — "Always remember" (ChallengeRequiredOnNewDevice=false:
#    we want the newDeviceUsed SIGNAL, not an extra challenge; DeviceOnlyRememberedOnUserPrompt=false
#    = remember every device automatically)
aws cognito-idp update-user-pool --user-pool-id <POOL_ID> \
  --device-configuration ChallengeRequiredOnNewDevice=false,DeviceOnlyRememberedOnUserPrompt=false

# 2. Wire BOTH triggers in one LambdaConfig
POST_CONFIRM_ARN=$(aws lambda get-function --function-name pilot-production-post-confirmation \
  --query 'Configuration.FunctionArn' --output text)
POST_AUTH_ARN=$(aws lambda get-function --function-name pilot-production-post-authentication \
  --query 'Configuration.FunctionArn' --output text)

aws cognito-idp update-user-pool --user-pool-id <POOL_ID> \
  --lambda-config PostConfirmation=$POST_CONFIRM_ARN,PostAuthentication=$POST_AUTH_ARN

# 3. Verify
aws cognito-idp get-user-pool --user-pool-id <POOL_ID> \
  --query 'UserPool.[LambdaConfig,DeviceConfiguration]'
# Expect: BOTH trigger ARNs present; DeviceConfiguration shows tracking on, always-remember.
```

**Operational heads-up (design §G-11)**: when device tracking flips on, each user's **first** sign-in per device reads as "new" and will fire the alert once per owner endpoint; it settles as devices are remembered. Expected — not a defect.

## Task 7 — Smoke Test

1. Precondition: a test owner whose `user_endpoint` sms row is `consent_status='opted_in'` + `verification_status='verified'` (Tom's account in the target environment).
2. Sign in from a **new device context** (fresh incognito window / new browser profile) via the normal web login (complete MFA if enrolled).
3. Within ~1 minute: the owner's phone receives the Sample 3 SMS — verbatim: `Pilot for Trades: New sign-in to your account from a new device. If this wasn't you, secure your account now. Reply STOP to opt out.`
4. Confirm the trail: `/aws/lambda/pilot-production-post-authentication` shows the `newDeviceUsed` gate pass + enqueue line; the Celery worker logs show the `send_platform_account_notification_sms` send.
5. **Negative**: sign in again from the same browser → no SMS (device now remembered; Lambda logs show the gate returning early).

If the SMS doesn't arrive: check the Lambda log first (gate vs lookup vs enqueue), then the worker log, then that the endpoint row is verified+opted-in. Do not "fix" by editing the template body — it is campaign-locked.

## Task 8 — Doc Updates (same change)

- [`aws-cognito-prod-setup.md`](../aws-cognito-prod-setup.md) §11: device tracking = Always remember + Post-Authentication trigger wired (date, function name, dual-trigger LambdaConfig note).
- [`aws-ops-runbook.md`](../aws-ops-runbook.md) §14.5: add a "Post-Authentication Lambda (PLATFORM-SMS-B2)" row to the extra-steps table + a short subsection mirroring the build/deploy/wire procedure, leading with the **both-triggers** overwrite warning.
- [`aws-infrastructure-as-built.md`](../aws-infrastructure-as-built.md): new Lambda function, the Redis SG ingress rule, the IAM policy delta, the log group.

---

## Rollback

Detach the trigger (leave the function deployed but inert):

```bash
aws cognito-idp update-user-pool --user-pool-id <POOL_ID> \
  --lambda-config PostConfirmation=$POST_CONFIRM_ARN
# Optionally also disable tracking:
# aws cognito-idp update-user-pool --user-pool-id <POOL_ID> --device-configuration ChallengeRequiredOnNewDevice=false,DeviceOnlyRememberedOnUserPrompt=true
```

## Definition of Done

- [ ] Part 1 confirmed merged + green (handler exists; unit tests pass)
- [ ] Pre-work `get-user-pool` baseline captured (LambdaConfig = PostConfirmation only)
- [ ] Build script created, executable, populates `build/post_authentication` cleanly (incl. celery)
- [ ] Terraform: function + permission + output + log group + SG ingress + IAM ARN widening — plan shows ONLY those deltas (anything else → stopped and asked Tom)
- [ ] Device tracking enabled (Always remember) and **both** trigger ARNs verified via `get-user-pool`
- [ ] Smoke test: new-device sign-in → Sample 3 SMS received verbatim; Lambda + worker logs confirm; second sign-in → no SMS
- [ ] Three doc updates applied (cognito-setup §11, runbook §14.5, as-built)
- [ ] Rollback command validated syntactically (not executed)
- [ ] Completion Summary added to `pilot-launch-plan.md` _(private)_ Appendix C: `### PLATFORM-SMS-B2 (Part 2) — Post-Authentication Lambda Deploy + Cognito Wiring (DevOps): Completion Summary` (standard format: Completed / Mode / What Was Accomplished / Infra Changed / Docs Updated / Verification incl. smoke-test evidence)
