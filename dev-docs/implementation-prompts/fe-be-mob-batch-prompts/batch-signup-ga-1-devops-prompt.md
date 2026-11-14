# Implementation Prompt: SIGNUP-GA-1 — Cognito Self-Sign-Up + Post-Confirmation Lambda Deploy

**Mode**: Pilot DevOps Engineer
**Batch**: SIGNUP-GA-1 (DevOps half)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.3 row 14a
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-signup-ga-1-design.md` (v2.0) — §C step 2, §F DevOps interface
**ADRs**: `ADR-0011` (self-sign-up → Lambda) + `ADR-0012` (drop tenant-name uniqueness) — both **Accepted**
**Estimated session**: 2–3 hours
**Platform**: Infrastructure (`infrastructure/terraform/`) + AWS Cognito/Lambda
**Backend companion**: `batch-signup-ga-1-python-engr-prompt.md` — **must land first.** The Python Engineer authors the Lambda handler at `backend/lambda/post_confirmation/handler.py`; you package and deploy it.

> **Sequencing gate**: Do NOT start until the Python Engineer confirms (via their Handoff Instructions) that `backend/lambda/post_confirmation/handler.py` + the migration are merged. You are deploying **their** handler code — there is nothing to package before it exists.

---

## ⚠️ MANDATORY STOP: Read These First

Before changing any infrastructure, read:

- **`.roo/rules-pilot-devops-engineer/`** — both rule files: deploy constraints (one service at a time) + secret-management policy (non-negotiable)
- **`dev-docs/devops/aws-infrastructure-as-built.md`** — §5 Security Architecture (Cognito pool, IAM roles, secrets); this is the doc you will **update** on completion (Architect verifies — stewardship §12.1)
- **`dev-docs/devops/aws-cognito-prod-setup.md`** — the pool's as-built console configuration + §11 (Post-Confirmation Lambda was deferred — this batch completes it)
- **`dev-docs/devops/aws-ops-runbook.md`** — deploy/apply procedure, state handling
- **The Terraform you are editing**: `infrastructure/terraform/modules/security/main.tf` (Cognito pool block line 636, Lambda block line 745, `archive_file` placeholder line 729)

### Critical constraints for this batch

- **The pool already exists and is imported.** `us-east-1_XXXXXXXXX` (pool), `xxxxxxxxxxxxxxxxxxxxxxxxxx` (client). The Terraform block has `lifecycle { ignore_changes = [lambda_config, schema, username_configuration, name, user_pool_add_ons] }` (`main.tf`). **Do not remove `lambda_config` from `ignore_changes` casually** — understand why it's there (the trigger is wired after Lambda deploy) before touching it.
- **Cost impact is $0** — no new AWS service; self-sign-up and the Lambda are within the free/existing tiers. No founder cost review needed (design §A Input Read Summary).
- **Secret policy**: the Lambda reads `pilot/prod/db` via `DB_SECRET_ARN` (already injected — `main.tf`). Do not print, log, or hardcode DB credentials. Follow the secret-management-policy rule file.
- **Deploy order**: Cognito pool changes are not ALB traffic shifts, but a broken pool config locks out **all** auth. Stage the change, verify in a controlled way, and have the rollback (`allow_admin_create_user_only = true`) ready.

---

## Background / Context

Today (verified in the repo):
- `admin_create_user_config { allow_admin_create_user_only = true }` (`main.tf`) — **self-registration disabled**. This is what blocks self-serve GA (Gap G1).
- The Post-Confirmation Lambda `pilot-production-post-confirmation` exists as a **placeholder stub** — `data.archive_file.post_confirmation` inlines a no-op `def handler(event, context): return event` (`main.tf`). The real handler has never been deployed.
- IAM role `pilot-production-lambda-execution-role` (VPC access, RDS secret, KMS) and SG `pilot-production-sg-lambda` (egress to RDS on 5432) already exist and are correct.

This batch, per ADR-0011/§C step 2:
1. **Package + deploy** the real handler the Python Engineer authored (`backend/lambda/post_confirmation/handler.py`, 3-path router) — replace the placeholder stub.
2. **Re-enable self-sign-up** (`allow_admin_create_user_only = false`) with email verification retained.
3. **Confirm the Post-Confirmation trigger** is wired to the deployed function.
4. Keep the pool rate-limited + Turnstile-guarded at the `/sign-up` edge (Turnstile secret `pilot/prod/turnstile` already exists — the guard is enforced by the app/edge, not the pool; just confirm it is in place, do not remove it).

---

## Tasks

### Task 1 — Build the Lambda deployment package from the engineer's handler

Replace the inline placeholder `data.archive_file.post_confirmation` (`main.tf`) so it packages the real source at `backend/lambda/post_confirmation/`.

- The handler entry stays `handler.handler`, runtime `python3.12`, matching `aws_lambda_function.post_confirmation`.
- The handler needs Python dependencies (confirm the exact list from the engineer's Handoff — expected `psycopg2-binary` and/or `sqlalchemy`). Because these are non-stdlib, package them properly — **prefer a Lambda layer or a built zip that includes site-packages** over the inline `archive_file` string form. Two acceptable patterns (pick per the ops runbook / existing convention):
  - **(A)** `data.archive_file` pointing at a pre-built `build/` dir populated by a `pip install -t` step (documented in the runbook), or
  - **(B)** a Lambda layer for deps + `archive_file` of just the handler source.
- `psycopg2` on Lambda must be the Linux-compiled wheel (`psycopg2-binary`) or the known Lambda-compatible build — a mac-built wheel will fail at runtime. Build for `manylinux`/Lambda `python3.12`.
- Keep `memory_size = 256`, `timeout = 30`, `tracing_config { mode = "Active" }`, and the existing `vpc_config` (private subnets + `sg_lambda`) as-is — the handler must reach RDS in-VPC.

> **Verify env vars**: the function already injects `ENVIRONMENT`, `DB_SECRET_ARN`, `COGNITO_USER_POOL_ID` (`main.tf`). Confirm the engineer's handler reads exactly these names. If the handler expects a different env var name, reconcile with the engineer — do **not** silently rename.

### Task 2 — Re-enable self-sign-up on the pool

In `main.tf`:
```hcl
  admin_create_user_config {
    allow_admin_create_user_only = false   # ADR-0011: re-enable self-serve SignUp (GA)
  }
```
- Keep `auto_verified_attributes = ["email"]` and the email-verification message flow — a confirmed email is required before the Post-Confirmation trigger fires (this is the gate that makes Path 3 safe).
- Keep the password policy (min 12, upper/lower/number/symbol) unchanged.
- **Because the pool block has `ignore_changes` that historically included pool attributes**, verify whether `admin_create_user_config` is covered by the `ignore_changes` list (`main.tf`). It currently lists `lambda_config, schema, username_configuration, name, user_pool_add_ons` — `admin_create_user_config` is **not** in that list, so Terraform will manage it. Confirm with `terraform plan` that the only pool diff is `allow_admin_create_user_only: true → false`. If the plan shows unexpected force-replacement or additional diffs → **STOP and ask Tom** (a pool replacement would destroy all users).

### Task 3 — Confirm the Post-Confirmation trigger wiring

- The pool's `lambda_config { post_confirmation = aws_lambda_function.post_confirmation.arn }` (`main.tf`) is currently inside `ignore_changes = [lambda_config, ...]` — meaning Terraform is **not** managing the trigger link (it was wired manually per cognito-setup §11, or never wired because the Lambda was a stub).
- After deploying the real function, ensure the trigger is actually attached to `pilot-production-post-confirmation`. If it must be wired manually (console/CLI) because it's in `ignore_changes`, do so and document it; if you choose to let Terraform manage it, removing `lambda_config` from `ignore_changes` is a deliberate change — **confirm the `terraform plan` shows only the trigger attachment and no pool replacement** before applying.
- The `aws_lambda_permission.cognito_post_confirmation` (`main.tf`) already allows Cognito to invoke — verify it survives the plan.

### Task 4 — Apply, verify, and smoke-test

- `terraform plan` → review the diff with Tom before `apply` (Cognito is auth-critical).
- After apply, verify:
  - Lambda updated: `aws lambda get-function --function-name pilot-production-post-confirmation` → confirm the code SHA changed from the placeholder and env vars are present.
  - Pool: `aws cognito-idp describe-user-pool --user-pool-id us-east-1_XXXXXXXXX` → `AllowAdminCreateUserOnly` is `false`; `LambdaConfig.PostConfirmation` points at the function ARN.
- **End-to-end smoke test in a controlled way** (design §I DoD "testable in a non-prod env" — prefer the dev pool `us-east-1_XXXXXXXXX` if you can deploy the same handler there first; otherwise use a disposable test email on prod and clean up):
  1. Perform a Cognito `SignUp` (email + password) → receive the verification code → confirm.
  2. Confirm the Post-Confirmation Lambda fired: CloudWatch log group `/aws/lambda/pilot-production-post-confirmation` shows the run and which **path** it took (should be **Path 3 — new-owner create** for a brand-new email).
  3. Confirm in RDS (read-only) that a `tenant` (placeholder name `"{local}'s Company"`) + owner `user` + `tenant_user(owner)` were created for that email.
  4. **Failure-mode check**: confirm the handler does **not** raise on a duplicate/second confirmation of the same email (Path 1 no-op) — the user must not be stranded.
- Clean up any test tenant/user created on prod.

---

## Rollback Plan

If self-sign-up or the Lambda misbehaves:
1. **Immediate**: set `allow_admin_create_user_only = true` and `terraform apply` (or console toggle) — this re-closes self-registration; existing users/login are unaffected.
2. The placeholder-stub function can be redeployed from the prior `source_code_hash` if the new handler is faulty, but **prefer fixing forward** with the engineer since the stub does nothing (users would confirm but get no RDS row).
3. Document any rollback in the ops runbook incident log.

---

## Definition of Done

- [ ] Read both DevOps rule files + `aws-infrastructure-as-built.md §5` + `aws-cognito-prod-setup.md` + the ops runbook before changes
- [ ] Confirmed backend handler `backend/lambda/post_confirmation/handler.py` is merged (engineer handoff received) before starting
- [ ] `data.archive_file.post_confirmation` now packages the real handler + its deps (Linux-compatible `psycopg2`), replacing the inline stub
- [ ] `aws_lambda_function.post_confirmation` deploys the real code (SHA changed); env vars `DB_SECRET_ARN`, `COGNITO_USER_POOL_ID`, `ENVIRONMENT` confirmed
- [ ] `allow_admin_create_user_only = false` applied; `terraform plan` showed **only** that diff on the pool (no force-replace)
- [ ] Post-Confirmation trigger confirmed attached to the deployed function; `aws_lambda_permission.cognito_post_confirmation` intact
- [ ] Password policy + email verification retained; Turnstile `/sign-up` guard confirmed still in place
- [ ] End-to-end smoke test passed: SignUp → confirm → Path 3 fires → tenant+user+tenant_user in RDS; duplicate confirmation → Path 1 no-op (no strand)
- [ ] Test tenant/user cleaned up
- [ ] Rollback path verified available (`allow_admin_create_user_only = true`)
- [ ] `aws-infrastructure-as-built.md §5` updated: Self-registration `Disabled → Enabled (self-sign-up, ADR-0011)`; Post-Confirmation Lambda `placeholder → deployed (3-path router)`
- [ ] `aws-cognito-prod-setup.md §11` updated to reflect the trigger is now live
- [ ] Completion Summary added to the launch plan §2.3 SIGNUP-GA-1 card

---

## Completion Summary

Add to `pilot-launch-plan.md` §2.3 (SIGNUP-GA-1 card):

```markdown
### SIGNUP-GA-1 (DevOps) — Cognito Self-Sign-Up + Post-Confirmation Lambda Deploy: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot DevOps Engineer

#### What Was Accomplished
- Packaged + deployed the real Post-Confirmation Lambda 3-path router (replaced the placeholder stub)
- Re-enabled Cognito self-sign-up (`allow_admin_create_user_only = false`), email verification retained
- Confirmed Post-Confirmation trigger wiring + Cognito invoke permission
- End-to-end smoke test: SignUp → confirm → Path 3 → tenant+user in RDS

#### Infra Changed
| Resource | Change |
|---|---|
| `aws_cognito_user_pool.prod` | `allow_admin_create_user_only: true → false` |
| `data.archive_file.post_confirmation` | stub → real handler package |
| `aws_lambda_function.post_confirmation` | placeholder → 3-path router code |

#### Docs Updated
- `aws-infrastructure-as-built.md §5` (self-registration + Lambda status)
- `aws-cognito-prod-setup.md §11` (trigger live)
```

---

## After This Task — Next Step

Notify the React Engineer that self-sign-up is live so `SIGNUP-GA-1-FE` (password field + Amplify `SignUp` on web `/sign-up` + mobile) can be smoke-tested end-to-end against prod/dev. The Architect verifies the two infra-doc updates (stewardship §12.1) and confirms Gap G1 can move out of `pilot-founder-onboarding-process.md §10` once the FE half lands.
