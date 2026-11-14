# C-B16-OPS — Tenant-Sites Production Cutover (DevOps Prompt)

**Mode**: `pilot-devops-engineer`
**Batch**: C-B16-OPS (Phase 1, Ord 3)
**Design doc**: `batch-c-b16-design.md` §C steps 0 + 10, §G-1, §G-11, §J
**Binding decisions**: ADR-0014 (Cloudflare registrar + DNS-only wildcard; no Route 53; edge apex redirect) · ADR-0015 (SMS via AWS toll-free — moot contingency, untouched here)
**Launch plan card**: `pilot-launch-plan.md` §3.3
**Estimate**: 0.5–1 day (one off-hours apply window + Cloudflare console + web image rebuild + smoke)
**Platform**: AWS prod (us-east-1, account 000000000000) + Cloudflare console

---

## ⚠️ MANDATORY STOP — Read First

1. `aws-ops-runbook.md` **§19.6** (service sync + canary — the last step of EVERY deploy), **§19.7** (image hygiene check), **§8.1/§8.3** (image build + push)
2. `batch-c-b16-design.md` §C step 0 / step 10, §G-11 (apex edge redirect), §J (cost)
3. ADR-0014 — full entry (Cloudflare posture is binding)
4. `aws-env-mgmt-ops-plan.md` — `TENANT_SITES_BASE_DOMAIN` / `NEXT_PUBLIC_TENANT_SITES_DOMAIN` rows

**Batch-critical rules:**

- **Founder-Period Deploy Policy** (§19.6): off-hours, **one deploy at a time**, announced to Tom; checklist-strict. No exceptions.
- **Plan-gates are STOP conditions**: any `terraform plan` surprise (pool replacement, unexpected resource drift) → STOP, paste the plan, return to Architect.
- **No Route 53 hosted zone** — DNS lives in Cloudflare (ADR-0014). Cloudflare-side records/rules are **manual console steps** (no Cloudflare TF provider in Phase 1).
- **Wildcard is DNS-only (gray cloud)**; only apex/www placeholder records are proxied (solely to power the edge 301). Never orange-cloud the wildcard — it breaks SlowAPI per-IP accuracy and the ISR/Redis cache contract (ADR-0014 context).
- **Cost guardrail**: this batch is zero marginal ALB cost (shared ALB + SNI cert); domain cost +$0.87/mo already approved (ADR-0014). No new billable resources beyond the ACM cert (free) may appear in the plan.

---

## Pre-Work (verification before any change)

1. **Cognito pool ground truth** (drives Step 0 values):

   ```bash
   aws cognito-idp describe-user-pool --user-pool-id us-east-1_XXXXXXXXX --region us-east-1 \
     --query '{auth_session_validity: UserPool.AuthSessionValidity, sms_auth: UserPool.SmsAuthenticationMessage, sms_verification: UserPool.SmsVerificationMessage, email_verification: UserPool.EmailVerificationMessage}'
   ```

   Expected (console-set 2026-08-25, per launch plan §3.13): `auth_session_validity = 5`, `sms_auth = "Your Pilot for Trades authentication code is {####}. It expires in 5 minutes."`, `sms_verification = "Your Pilot for Trades verification code is {####}. It expires in 24 hours."`, email verification message = **default** (intentionally — COGNITO-EMAIL-1 owns it later). **If the live values differ from these, STOP and reconcile with Tom before writing any TF** — the console is truth; TF must match it exactly (including punctuation).
2. Confirm tunnel-free tooling: `terraform -version` (≥ 1.7), AWS CLI session against the HotRMC account, `cd infrastructure/terraform/environments/production && terraform init` already done.
3. Baseline plan: `terraform plan -out=/tmp/cb16ops-before.tfplan` must show **no changes** before you edit anything. If it shows pre-existing drift → STOP, report to Architect.
4. Read the exact TF targets: `modules/security/main.tf` (`aws_cognito_user_pool.prod` ~L693, `aws_acm_certificate.wildcard` ~L535) and `modules/compute/main.tf` (`aws_lb_listener.https` ~L159, `aws_lb_listener_rule.web` ~L815, task defs `api` ~L246 / `worker` ~L308 / `web` ~L850).

---

## Step 0 — Codify the Cognito pool console changes (PREREQUISITE — do not skip)

**Why first**: the new ACM cert lands in `module.security` (existing wildcard pattern) and env-level applies plan `module.security` regardless. The pool's `lifecycle.ignore_changes` does **not** cover `auth_session_validity`, `sms_authentication_message`, or `sms_verification_message` — so the next apply would silently revert Tom's 2026-08-25 console values to provider defaults. Codifying first closes the hazard permanently.

1. Edit `modules/security/main.tf` `aws_cognito_user_pool.prod`:
   - Add (values = live console values captured in Pre-Work 1, exactly):
     ```hcl
     auth_session_validity = 5

     # MFA-WIRE-1 tail (2026-08-25): branded SMS templates, set in console and
     # codified here in the same change (C-B16-OPS Step 0). Email verification
     # template intentionally left at Cognito default — COGNITO-EMAIL-1 owns it.
     sms_authentication_message = "Your Pilot for Trades authentication code is {####}. It expires in 5 minutes."
     sms_verification_message   = "Your Pilot for Trades verification code is {####}. It expires in 24 hours."
     ```
   - **Replace the stale comment** at the `sms_configuration` block (currently says *"Do NOT add sms_authentication_message — the AWS default OTP message is fine for beta; branding is a later polish."*) with: `# MFA-WIRE-1 (Step 0): SMS MFA delivery path via SNS role. SMS templates codified above (2026-08-25).` — the "do not add" guidance is void as of 2026-08-25.
2. **Plan-gate**: `terraform plan` must show **0 changes** to `aws_cognito_user_pool.prod` (config now matches the console). A diff on the pool = values mismatch → STOP, recheck Pre-Work 1. Any other resource appearing in this plan (beyond Steps 1–4 below when you add them) → STOP.
3. Apply **only after** Steps 1–4 are also in the plan (one apply session; Step 0 requires no apply of its own — a 0-change plan is the proof).

---

## Step 1 — ACM wildcard cert for `p4tsites.com` (Terraform, security module)

Following the existing `aws_acm_certificate.wildcard` pattern (`modules/security/main.tf` ~L535), add:

```hcl
# C-B16-OPS (ADR-0014): tenant-sites domain cert. apex + wildcard SAN.
# Validation is DNS, records created MANUALLY in Cloudflare (Step 2) —
# no aws_acm_certificate_validation resource (same posture as the wildcard above).
resource "aws_acm_certificate" "p4tsites" {
  domain_name               = "p4tsites.com"
  subject_alternative_names = ["*.p4tsites.com"]
  validation_method         = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name      = "p4tsites-wildcard"
    Component = "tenant-sites"
  }
}

output "p4tsites_certificate_arn" {
  description = "ACM cert ARN for *.p4tsites.com (SNI on shared ALB)"
  value       = aws_acm_certificate.p4tsites.arn
}
```

Plan shows the cert created (PENDING_VALIDATION) + the two validation CNAME options in the output. **Capture the 2 validation records** (`terraform output -json` or the plan text) for Step 2.

## Step 2 — Cloudflare console records (Tom + DevOps, manual — ADR-0014)

In the `p4tsites.com` zone (registrar + DNS: Cloudflare):

1. **2 ACM validation CNAMEs** from Step 1 — **DNS-only (gray cloud)**, exact name/value from AWS.
2. **Wildcard CNAME**: `*` → `<ALB DNS name>` (`aws_lb.api.dns_name` from TF output) — **DNS-only (gray cloud)**. Never proxied.
3. **Apex + www placeholders**: `AAAA` `@` and `AAAA` `www` → `100::` — **proxied (orange)**. These exist only to power the edge redirect.
4. **Redirect Rule** (Rules → Redirect Rules): `hostname in { "p4tsites.com", "www.p4tsites.com" }` → **301** → `https://pilotfortrades.com` (static, preserve query string off).
5. **Mail lockdown**: TXT `@` = `v=spf1 -all`; TXT `_dmarc` = `v=DMARC1; p=reject` (no mail ever from this domain).
6. Wait for ACM status **ISSUED** (`aws acm describe-certificate --certificate-arn <arn>` poll) before Step 3.

## Step 3 — ALB: SNI cert + host-header rule (Terraform, compute module)

In `modules/compute/main.tf`, after `aws_lb_listener_rule.web` (~L815):

```hcl
# C-B16-OPS (ADR-0014): tenant-sites wildcard → pilot-web TG (SNI on shared ALB)
resource "aws_lb_listener_certificate" "p4tsites" {
  listener_arn    = aws_lb_listener.https[0].arn
  certificate_arn = var.p4tsites_certificate_arn
}

resource "aws_lb_listener_rule" "tenant_sites" {
  listener_arn = aws_lb_listener.https[0].arn
  priority     = 15 # after web (10), before any catch-all API rule

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.web.arn
  }

  condition {
    host_header {
      values = ["*.p4tsites.com"]
    }
  }

  tags = {
    Name      = "pilot-${var.environment}-tenant-sites-listener-rule"
    Component = "tenant-sites"
  }
}
```

Wire the new cert ARN through: `modules/compute/variables.tf` gains `variable "p4tsites_certificate_arn" { type = string }`; `environments/production/main.tf` `module "compute"` gains `p4tsites_certificate_arn = module.security.p4tsites_certificate_arn`.

**Do NOT add an apex/www ALB rule** — the apex redirect lives at the Cloudflare edge (§G-11, ADR-0014). Only the wildcard host rule burns an ALB rule slot.

## Step 4 — Task-def env vars (Terraform, compute module)

1. `aws_ecs_task_definition.api` environment list (~L267): add `{ name = "TENANT_SITES_BASE_DOMAIN", value = "p4tsites.com" }`.
2. `aws_ecs_task_definition.worker` environment list (~L323): add the same row (worker builds site URLs in the C-B16 requirements email + profile hook paths).
3. `aws_ecs_task_definition.web` environment list (~L867): add `{ name = "NEXT_PUBLIC_TENANT_SITES_DOMAIN", value = "p4tsites.com" }`.
4. **While in the web task def (folds in the §3.14 DevOps tail)**: verify `{ name = "NEXT_PUBLIC_API_URL", value = "https://api.${var.domain_name}" }` is present in TF (it is, ~L868) **and** confirm after apply + sync that the *running* task def carries it — without it, SSR `generateMetadata` on `/i/[token]` + `/q/[token]` falls back to generic titles (§3.14).
5. Beat task def: **no change** (card scope: api + worker only).

**Apply session**: Steps 0–4 in one `terraform apply` (off-hours, announced). Expected plan: 0 pool changes + cert + listener cert + listener rule + 3 task-def revisions + 1 variable/output wiring. Anything else → STOP.

## Step 5 — Web image rebuild (`NEXT_PUBLIC_*` is build-time inlined)

Per `aws-env-mgmt-ops-plan.md`: `NEXT_PUBLIC_TENANT_SITES_DOMAIN` is inlined at **image build time** (consumed by `src/middleware.ts` host-rewrite) — a task-env change alone is insufficient.

1. `frontend/apps/web/Dockerfile`: add alongside the existing args (~L115):
   ```dockerfile
   ARG NEXT_PUBLIC_TENANT_SITES_DOMAIN=p4tsites.com
   ENV NEXT_PUBLIC_TENANT_SITES_DOMAIN=$NEXT_PUBLIC_TENANT_SITES_DOMAIN
   ```
   and extend the header comment's build-arg documentation block.
2. Build + push per §8.3 with `--build-arg NEXT_PUBLIC_TENANT_SITES_DOMAIN=p4tsites.com` added to the documented command (Cognito args unchanged).
3. **§19.7 image hygiene check** on the fresh image **before push**: `docker run --rm --entrypoint sh <image> -c 'ls /app/.env'` must 404.
4. Backend images (`pilot/api`, `pilot/worker`): no rebuild needed — `TENANT_SITES_BASE_DOMAIN` is a runtime env var. (A same-SHA rebuild is acceptable but not required; do not skip Step 6's digest-parity canary either way.)

## Step 6 — §19.6 service sync + deploy canary (non-skippable)

Run the §19.6 flow end-to-end:

1. Migration verify (§9.2/§9.7): tunnel → `alembic current` == repo head (`58c3ad26129f` per INT-BUG-1 close 2026-08-25). This batch ships **no migration** — verify only.
2. §19.6 Step 1 sync script (one-at-a-time order `pilot-celery-worker` → `pilot-celery-beat` → `pilot-api` → `pilot-web`), revision parity + **image-digest parity** (`:latest` caveat — fresh web image pushed in Step 5 is what makes the web sync real).
3. Canary 5-check block, including: `curl -s https://api.pilotfortrades.com/api/health` 200; `curl -s -H "Host: anything.p4tsites.com" https://<ALB-DNS>/api/health` 200 (ALB host rule live); auth login smoke (Cognito untouched — Step 0 was 0-change).

## Step 7 — Tom smoke (founder path)

1. In the web app (Lang Electric Co. tenant): Settings → Website → publish the tenant site (draft already configurable; publish per design §D-4).
2. Browse `https://<slug>.p4tsites.com` → landing page renders (SSR, tenant-branded, "Hosted by Pilot for Trades" footer); `/privacy` + `/terms` render; unknown slug → 404 state.
3. `https://p4tsites.com` + `https://www.p4tsites.com` → 301 to `https://pilotfortrades.com` (Cloudflare edge).
4. Cert check: browser padlock shows the `*.p4tsites.com` ACM cert (not the pilotfortrades wildcard).

## Step 8 — Documentation (same change set, Rule 12.3)

1. `aws-infrastructure-as-built.md`: cert ARN, ALB rule, Cloudflare records table, env vars, cutover date.
2. `aws-env-mgmt-ops-plan.md`: mark the two env-var rows live in prod; note the web Dockerfile build-arg addition.
3. `aws-cognito-prod-setup.md` §"MFA-WIRE-1 — Cognito SMS Delivery": record that the pool SMS templates + `auth_session_validity` were **codified in Terraform** on this date (closes the §3.13 "Terraform codification PENDING" flag; the §3.13 card gets its note at batch close).
4. `aws-ops-runbook.md`: add the p4tsites Cloudflare console steps (Step 2 above) to the DNS/ops section so the manual side is runbook-backed (ADR-0014 consequence).

---

## Definition of Done

- [ ] Step 0 plan-gate passed: 0 changes on `aws_cognito_user_pool.prod`; console SMS templates + session validity now in TF; stale "do not add" comment removed
- [ ] ACM cert ISSUED for `p4tsites.com` + `*.p4tsites.com`; validation records in Cloudflare (DNS-only)
- [ ] Wildcard CNAME live (DNS-only); apex/www 301 at Cloudflare edge; SPF/DMARC lockdown records present
- [ ] ALB SNI cert + priority-15 host rule live; `curl -H "Host: x.p4tsites.com"` health check 200
- [ ] 3 task defs carry the new env vars; web task def confirmed carrying `NEXT_PUBLIC_API_URL` (§3.14 tail closed)
- [ ] Web image rebuilt with the new build-arg; §19.7 hygiene passed; §19.6 sync + digest-parity canary green on all 4 services
- [ ] Tom smoke: published slug renders over HTTPS; apex/www redirect; correct cert presented
- [ ] 4 doc updates landed (as-built, env-mgmt plan, cognito-prod-setup, ops runbook)
- [ ] Completion Summary appended below

## Appendix — Completion Summary

**Batch**: C-B16-OPS · **Date**: 2026-08-26 · **Engineer**: DevOps (pilot-devops-engineer)

### What was done

**Step 0 — Cognito SMS templates codified in Terraform**: Added `sms_authentication_message` + `sms_verification_message` to `aws_cognito_user_pool.prod` in `modules/security/main.tf`. Replaced the stale "do not add" comment on the `sms_configuration` block. Plan-gate confirmed 0 changes on the pool for the SMS templates (codified = live). **`auth_session_validity` deviation**: neither the Terraform AWS provider (v5.100.0) nor the AWS CLI `update-user-pool` command expose `auth_session_validity` — it is a **console-only setting**. The live value is `null` (Cognito default = 3 min). The "5" Tom previously set on the app client page was the app client token TTL (a separate setting). To set the pool-level `AuthSessionValidity = 5`, Tom must do it in the AWS Console. Tracked as a console-only follow-up.

**Step 1 — ACM wildcard cert for p4tsites.com**: Created `aws_acm_certificate.p4tsites` (apex + `*.p4tsites.com` SAN, DNS validation). Cert ARN: `arn:aws:acm:us-east-1:000000000000:certificate/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`. Status: ✅ ISSUED (validated via Cloudflare DNS CNAME). Output `p4tsites_certificate_arn` added to `modules/security/outputs.tf`.

**Step 2 — Cloudflare console records (manual, Tom + DevOps)**: ACM validation CNAME (DNS-only), wildcard CNAME `*` → ALB DNS (DNS-only), apex + www AAAA `100::` (proxied), Redirect Rule (apex/www → 301 → pilotfortrades.com), SPF/DMARC mail lockdown. All records created in the Cloudflare `p4tsites.com` zone. Cert validated within minutes.

**Step 3 — ALB SNI cert + host-header rule**: Created `aws_lb_listener_certificate.p4tsites` (SNI on shared ALB) + `aws_lb_listener_rule.tenant_sites` (priority 15, `Host: *.p4tsites.com` → pilot-web TG). Wired `p4tsites_certificate_arn` through `modules/compute/variables.tf` + `environments/production/main.tf`. Initial apply failed (cert PENDING_VALIDATION — expected); re-applied after cert ISSUED → cert attached successfully.

**Step 4 — Task-def env vars**: Added `TENANT_SITES_BASE_DOMAIN=p4tsites.com` to `pilot-api` (rev 8) + `pilot-celery-worker` (rev 5); added `NEXT_PUBLIC_TENANT_SITES_DOMAIN=p4tsites.com` to `pilot-web` (rev 6). Beat task def unchanged (card scope: api + worker only). `NEXT_PUBLIC_API_URL` confirmed present in the web task def (§3.14 tail closed).

**Step 5 — Web image rebuild**: Added `ARG NEXT_PUBLIC_TENANT_SITES_DOMAIN=p4tsites.com` + `ENV` to `frontend/apps/web/Dockerfile`. Built with `--build-arg NEXT_PUBLIC_TENANT_SITES_DOMAIN=p4tsites.com`. §19.7 hygiene check passed (no `.env` in image). Pushed to ECR (`pilot/web:latest`, digest `sha256:a9405eba...`).

**Step 6 — §19.6 service sync + deploy canary**: Synced all 4 services in one-at-a-time order (worker → beat → api → web). All 5 canary checks passed: (1) revision + digest parity ✅, (2) API health 200 ✅, (3) OpenAPI sentinels present ✅, (4) migration parity `58c3ad26129f` ✅, (5) image hygiene ✅. C-B16 ALB host-rule canary: `curl -k -H "Host: anything.p4tsites.com"` → 200 `{"status":"ok","service":"pilot-web"}` ✅.

**Step 7 — Tom smoke**: Pending Tom's founder-path smoke (publish a tenant site, browse `https://<slug>.p4tsites.com`, verify apex redirect, cert padlock).

**Step 8 — Documentation**: Updated `aws-infrastructure-as-built.md` (cert ARN, ALB rule, Cloudflare records, env vars, cutover date), `aws-env-mgmt-ops-plan.md` (env-var rows marked live), `aws-cognito-prod-setup.md` (SMS templates codified flag closed), `aws-ops-runbook.md` (§17.1 p4tsites Cloudflare console steps + §19.6 quick-verify scripts added per Tom's request).

### Deviations from the prompt

1. **`auth_session_validity` not codified in TF or CLI**: neither the AWS provider v5.100.0 nor the AWS CLI `update-user-pool` command expose `auth_session_validity` — it is a **console-only setting**. The SMS templates (the primary Step 0 goal) are codified and show 0 plan changes. `auth_session_validity` remains a console-only setting (live = `null` = 3 min default). To set it to 5, Tom must use the AWS Console. Tom approved this approach.
2. **Pre-existing baseline drift (5 items)**: ECS desired_count 1→2 (profile-script drift), S3 bucket policies (manually-applied, unrelated). Tom approved proceeding with the apply; he will run `profile-b-app.sh light` afterward to scale back down.
3. **ALB listener cert attach required two applies**: the first apply created the cert (PENDING_VALIDATION) but couldn't attach it to the ALB (ACM rejects PENDING_VALIDATION certs for ALB). After the Cloudflare validation CNAME propagated and the cert flipped to ISSUED, the re-apply attached it successfully. This matches the prompt's Step 2 instruction ("Wait for ACM status ISSUED before Step 3").

### Files changed

| File | Change |
|---|---|
| `infrastructure/terraform/modules/security/main.tf` | Step 0: SMS templates codified + stale comment replaced; Step 1: `aws_acm_certificate.p4tsites` added |
| `infrastructure/terraform/modules/security/outputs.tf` | `p4tsites_certificate_arn` output added |
| `infrastructure/terraform/modules/compute/variables.tf` | `p4tsites_certificate_arn` variable added |
| `infrastructure/terraform/modules/compute/main.tf` | Step 3: `aws_lb_listener_certificate.p4tsites` + `aws_lb_listener_rule.tenant_sites`; Step 4: env vars on api/worker/web task defs |
| `infrastructure/terraform/environments/production/main.tf` | `p4tsites_certificate_arn` wiring in `module "compute"` |
| `frontend/apps/web/Dockerfile` | Step 5: `ARG NEXT_PUBLIC_TENANT_SITES_DOMAIN` + `ENV` + header comment |
| `dev-docs/devops/aws-infrastructure-as-built.md` | §7: p4tsites cert ARN, ALB rule, Cloudflare records, env vars, cutover date |
| `dev-docs/devops/aws-env-mgmt-ops-plan.md` | Env-var rows marked live in prod |
| `dev-docs/devops/aws-cognito-prod-setup.md` | MFA-WIRE-1: SMS templates codified flag closed |
| `dev-docs/devops/aws-ops-runbook.md` | §17.1: p4tsites Cloudflare console steps; §19.6: quick-verify scripts |
