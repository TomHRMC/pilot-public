# HIBERNATE-1 Design — Project Hibernation: AWS Deep Teardown + Static Hold Page + DNS Cutover

**Version**: 1.1
**Date**: September 7, 2026
**Author**: Pilot Architect
**Status**: **APPROVED** (Tom, 2026-09-07 — all §G decisions ratified verbatim; **scorched tier elected** (§G-5); designer-gate waiver **granted** (§G-3); all §B.1 preservation artifacts completed by Tom and Architect-verified) — execution gated on Tom go
**v1.1 changes (2026-09-07)**: Tom ratified every §G decision and **elected the scorched tier** — delete all 11 secrets + the KMS CMK + all ECR images (his secrets are externally backed up). Keep-list shrinks to: S3+CloudFront+ACM, TF state backend, Cognito pool ($0), dormant detached Lambdas ($0), empty ECR repo shells ($0) → **sustained AWS ≈ $1–3/mo** (+ $2 AWS End-User-Messaging TFN, §B.4 ⇒ ≤ ~$5 total). New mandatory step: **detach Cognito Lambda triggers (full-carry `update-user-pool`) BEFORE KMS deletion** — the CustomEmailSender decrypts via the CMK (§G-10). Tom's completed artifacts canonized in §B.1: DB backup pair in `dev-docs/db-design/dbbackups/`, Cloudflare zone exports in `dev-docs/devops/godaddy-cloudflare-archive/`, TF state backup `infrastructure/terraform/environments/production/2026.09.07-p4t-prod-data.json`. Watchdog directive: ALL CloudWatch alarms/dashboard/log groups destroyed; a single $0 AWS Budgets alert retained (not a CloudWatch trigger — Tom may strike). End-of-batch checkpoint = Tom's commit + merge to `dev`. Tier election recorded as **ADR-0021**.
**Launch plan**: §1.1 Ord 33 · card §3.33
**Batch type**: DevOps (infrastructure + DNS + one static marketing surface). No backend, no application frontend.
**Prompt (authors next)**: `dev-docs/devops/prompts/batch-hibernate-1-devops-prompt.md`
**Estimate**: ~1 working day of execution + 7-day cost-verification tail

---

## Purpose & Context

Tom is pausing Pilot for Trades development for a few months. The goals, in his words (2026-09-07 session):

1. *"Turn completely off all of the aws stuff"* — originally scoped to `profile-off.sh`, then tightened: *"need another way to get our costs down to single digits for dollars, not the $102/mo as that is way too much for a SPA static site"*.
2. *"We don't need any dev support either, no bastion, no RDS, etc."* and *"yes, we can delete the RDS as our local dev DB we will make a full schema and then data backup"*.
3. *"We don't need anything other than the basics to serve static S3/CloudFront, all else can be removed as it is not needed, and I can recreate it in the future when we restart."*
4. Replace the marketing site with a **single, fully static HTML page** carrying the basic content of the existing Coming Soon page — **no** "become a founder" and **no** "subscribe to our mailing list" capability.
5. Cloudflare DNS: only `pilotfortrades.com` + `www.pilotfortrades.com` resolve (to the static page); `app.`, `api.` (and everything else) resolve **nowhere**.

**Binding outcome**: AWS monthly spend in sustained hibernation ≈ **$1–3** (+ ~$2 AWS EUM TFN ⇒ ≤ ~$5 total), verified via Cost Explorer after 7 days, with a $0 AWS Budgets alert at $10 as the sole standing guard.

**DNS authority note (Tom, this session)**: *"I recently moved all dns management and registration away from godaddy and route53 over to cloudflare."* All DNS for both domains (`pilotfortrades.com`, `p4tsites.com`) is now Cloudflare. Existing docs that describe Route 53 as authoritative for `pilotfortrades.com` (`aws-infrastructure-as-built.md` §Security row, the §17-era cutover narrative, `profile-off.sh` line-19 comment, `aws-pilotfortrades-zone-export.json`) are **stale** and are corrected in this batch (§C Phase 8).

---

## A. Input Read Summary

| Input | What it contributed |
|---|---|
| `pilot-launch-plan.md` v7.47 | §1.1 table format (next Ord = 33), §3 card format (last card §3.32), ADR-0018 open/close protocol, §2 protocol (no §2 row — this batch carries Tom's steps internally) |
| `profile-off.sh` + `scripts/README.md` | Existing $102/mo cost-floor profile (ECS→0, GPU/bastion stop, site-config `coming_soon`); used as the graceful-shutdown first step; its cost floor is superseded by this batch's deep teardown; its Route 53 comment is stale |
| `aws-infrastructure-as-built.md` §1 | **Validated cost baseline** (~$664–707/mo): NAT ~$35, ALB ~$18, bastion ~$4–7, ECS ~$66, GPU ~$390, RDS ~$28, Redis ~$13, CloudWatch ~$28, GuardDuty ~$12, SecurityHub ~$5, Secrets (11) ~$4, KMS ~$1, R53 ~$1, S3/CloudFront ~$5 |
| `modules/compute/main.tf` | ECR repos ×4 (+lifecycle policy); ECS cluster; **ALB `enable_deletion_protection = true`** (line 95 — destroy blocked until toggled); GPU root 50GB gp3 `delete_on_termination=true` + models 20GB gp3 `delete_on_termination=false` (lines 558–575) |
| `modules/compute/gpu_userdata.sh` | GPU fully reprovisions from userdata (faster-whisper-large-v3 + ollama llama3.1:8b pulled to `/models`; ~15–20 min) → **no AMI/snapshot needed**; models volume deletable |
| `modules/database/main.tf` | RDS `db.t4g.micro` Multi-AZ, 20GB gp2, KMS-encrypted, **`deletion_protection = true`** (line 111), `skip_final_snapshot = false` + fixed `final_snapshot_identifier` (collision risk if a prior final snapshot exists) |
| `modules/networking/main.tf` | `aws_eip.nat` + `aws_nat_gateway.main` (line 85/97); `aws_eip.bastion` (line 504) |
| `modules/monitoring/main.tf` | SNS alarms topic + email sub, 7 log groups, dashboard, 11 alarms — all TF-managed (destroyable); **GuardDuty / Security Hub / AWS Config are NOT in TF** → console/CLI disable steps |
| `ComingSoonPage.tsx` | The approved hold-page content source: logo + wordmark, eyebrow badge, H1, ≤20-word value prop, message line, **mailto-only CTA (already zero forms)**, legal footer (© Example Holdings, LLC) |
| `apps/marketing/next.config.ts` | `output: "export"` static export → S3; the Next.js source stays untouched in git for restart |
| `.github/workflows/deploy-marketing.yml` | Triggers on push to `main` touching `frontend/apps/marketing/**` → would overwrite the hold page; the hold page therefore lives **outside** that path (`infrastructure/marketing-hold/`) and the workflow is disabled in the GitHub UI for the hiatus |
| `.github/workflows/e2e-nightly.yml` | Cron already commented out (line 15) — no scheduled-run spam to fix |
| `pilot-adr-log.md` | Next number ADR-0020; ADR-0014 (Cloudflare registrar/DNS posture) extended by this batch; ADR-0016 (schema-restore provisioning + env-aware seeds) is the restart data-path precedent |
| `aws-env-mgmt-ops-plan.md` §10 | Doc-maintenance rule: this batch updates env-mgmt in the same change (hibernation state = an environment change) |
| Tom's session rulings (2026-09-07) | The four binding quotes in §Purpose; DNS-moved-to-Cloudflare fact |

**MCP verification**: N/A — zero DB schema/data work (Rule 3 gate does not apply). The local dev DB `pg_dump` (Tom, §C Phase 2) is a file operation, not a migration. **Seed Data Rollout (Rule 11.5)**: N/A — no DB data is added or modified.

---

## B. State-Change Plan (infra analogue of the Migration Plan)

No database migrations. This batch mutates **DNS records, AWS resources, and third-party posture**. All mutations are reversible by `terraform apply` + documented console steps (§F Restart Contract).

### B.1 — Pre-teardown preservation (nothing destroys before this completes)

| # | Artifact | Status / How | Stored where |
|---|---|---|---|
| 1 | **Local dev DB full backup** — the system's data source of truth during hibernation (Tom's ruling: *"our local dev DB we will make a full schema and then data backup"*) | ✅ **DONE (Tom, 2026-09-07)** — `backup_20260907_082049.sql` (schema+data) + `schema_dump_20260907_082031.sql` (schema-only); earlier pairs retained. Executor residual gate: confirm both files non-empty and the data backup contains tenant rows before Phase 6 | `dev-docs/db-design/dbbackups/` — committed to Tom's private repo (his call, single-maintainer repo) |
| 2 | **Cloudflare zone exports** — the exact record inventory pre-deletion + the restart recreation reference | ✅ **DONE (Tom, 2026-09-07 12:41–12:42 UTC)** — Architect-verified complete: pilotfortrades.com carries `api`/`app` CNAMEs→ALB (delete targets), apex+`www` CNAMEs→`dxxxxxxxxxxxx2.cloudfront.net` (DNS-only), the `_<validation-name>` ACM-validation CNAME, SendGrid `emXXXX`/`s1._domainkey`/`s2._domainkey`, MX×5 Google, SPF/DKIM/DMARC/site-verification TXT; p4tsites.com carries `*`→ALB (delete target), apex/`www` AAAA `100::` proxied (edge redirect), the `_<validation-name>` ACM-validation CNAME, SPF `-all`/DMARC `reject` lockdown. Both zones: NS = `raina`/`viddy.ns.cloudflare.com` (confirms Cloudflare authoritative ⇒ R53 zone vestigial) | `dev-docs/devops/godaddy-cloudflare-archive/pilotfortrades.com/cloudlflare-pilotfortrades.com.txt` (filename typo `cloudlflare` preserved as-committed) + `dev-docs/devops/godaddy-cloudflare-archive/p4sites.com/cloudflare-p4tsites.com.txt` (folder typo `p4sites.com` preserved as-committed). Supersedes stale `aws-pilotfortrades-zone-export.json`. The archive also documents Tom's defensive typo-domains (`pilot4trade`, `pilot4trades`, `pilotfortrade` — parked; **no batch action**) |
| 3 | **Terraform state backup** | ✅ **DONE (Tom, 2026-09-07)** — `terraform state pull` snapshot. **The TF state backend (S3 state bucket + any lock table) is on the KEEP list — never destroyed** — without it, restart is an import exercise | `infrastructure/terraform/environments/production/2026.09.07-p4t-prod-data.json` + backend intact |
| 4 | Git checkpoint | Tom's directive: **one end-of-batch checkpoint** — commit + merge to `dev` after the full verification board is green (replaces the pre-work tag) | GitHub, at close |

### B.2 — DNS mutations (Cloudflare console, both zones)

**`pilotfortrades.com` zone:**

| Record | Action | Why |
|---|---|---|
| `@` / apex — CNAME → `dxxxxxxxxxxxx2.cloudfront.net` (DNS-only) | **KEEP, verify unchanged** | Serves the hold page |
| `www` — CNAME → `dxxxxxxxxxxxx2.cloudfront.net` (DNS-only) | **KEEP, verify unchanged** | Serves the hold page |
| `api` (→ ALB) | **DELETE** | ALB destroyed; Tom: "goes nowhere" (NXDOMAIN) |
| `app` (→ ALB) | **DELETE** | ALB destroyed; NXDOMAIN |
| `MX` (Google Workspace), `SPF` TXT, Google `DKIM` TXT, `DMARC` TXT | **KEEP — do not touch** | `mailto:` CTA and all email deliverability depend on these |
| SendGrid sender-auth CNAMEs (`em*`, `s1`/`s2`._domainkey) | **KEEP** | Restart-day sending works without re-authentication |
| **ACM validation CNAMEs** (`_acme-*` / `_*` validation records for the wildcard+apex cert) | **KEEP — CRITICAL** | ACM auto-renewal requires them; deleting them kills the marketing site mid-hibernation when the cert lapses |

**`p4tsites.com` zone:**

| Record | Action | Why |
|---|---|---|
| `*` wildcard (→ ALB) | **DELETE** | Tenant sites offline with the ALB destroyed; recreated at restart (C-B16 posture) |
| `@` / `www` AAAA `100::` + edge 301 → `pilotfortrades.com` | **KEEP** | Harmless; preserves the apex-redirect posture (ADR-0014) |
| ACM validation CNAMEs (p4tsites cert) | **KEEP** | Cert stays ISSUED for restart |
| SPF/DMARC lockdown TXT | **KEEP** | Anti-spoof posture (C-B16-OPS) |

### B.3 — AWS resource disposition (single source: `terraform state list` at execution; modules referenced here)

**DESTROY (bill-bearing or Tom-mandated):**

| Resource | Monthly saving | Execution caveats |
|---|---|---|
| ECS services ×4 + cluster | ~$0 at 0 tasks (already floored by `profile-off.sh`) | Destroy services before cluster; ECR repos are NOT part of this row |
| **ALB** + listeners + target groups | ~$18 | **`enable_deletion_protection = true` blocks destroy** — first `terraform apply` with it toggled `false` (or CLI), then destroy |
| NAT Gateway + `aws_eip.nat` | ~$35 | Destroy releases the EIP automatically |
| Bastion + `aws_eip.bastion` | ~$4–7 | EIP released on destroy; tunnel doc moves to restart runbook |
| GPU `g4dn.xlarge` | ~$5.6 (stopped EBS) | Terminate via TF. Root 50GB auto-deletes (`delete_on_termination=true`). **Models 20GB volume persists — delete it explicitly** (`delete_on_termination=false`); userdata re-pulls models at restart (~15–20 min, free) |
| **RDS `pilot-production`** | ~$28 | **`deletion_protection = true` blocks destroy** — toggle first. Tom's ruling: local `pg_dump` is the backup → destroy with `skip_final_snapshot = true` (avoids the fixed-name final-snapshot collision AND the ~$2/mo snapshot line). §G-4 covers the keep-snapshot alternative |
| ElastiCache Redis | ~$13 | Pure cache/broker/results — disposable, no backup |
| CloudWatch alarms ×11 + dashboard | ~$1–2 + ingestion tail | TF destroy; log groups KEPT (near-$0, preserve deploy history) |
| GuardDuty | ~$12 | **Not in TF** — console/CLI `disable` (detector) |
| Security Hub | ~$5 | **Not in TF** — console/CLI disable |
| AWS Config recorder | ~$0 | Stop recorder; keep the (empty) config-logs bucket or empty+delete with assets sweep |
| Route 53 hosted zone `ZXXXXXXXXXXXXXXXXXXXX` | ~$1 | Vestigial after Tom's Cloudflare move. **Pre-check**: `dig NS pilotfortrades.com` must return Cloudflare nameservers before deletion |
| S3 assets bucket (tenant audio/photos/PDFs) | ~$2 | Seed-reproducible test data only. **Verify-empty-then-delete**, after the executor confirms no irreplaceable manual uploads (checkpoint in prompt). Versioning enabled → delete must purge versions/delete-markers first |
| **Secrets Manager — all 11 secrets** (scorched, Tom-elected) | ~$4.40 | `delete-secret --force-delete-without-recovery` per secret. Tom: *"I have all of the secrets stored and backed up"* (external store). Restart re-enters values from his backup. **Must complete BEFORE KMS deletion** |
| **KMS CMK `26af6384-…`** (scorched, Tom-elected) | ~$1 | `schedule-key-deletion --pending-window-in-days 7`. **Prerequisites — ALL of: ① Cognito Lambda triggers detached (⚠️ block below), ② all 11 secrets force-deleted, ③ RDS + GPU EBS volumes destroyed** (nothing CMK-encrypted may remain). During the 7-day window the key is unusable and unbilled |
| **ECR images — all 4 repos** (scorched, Tom-elected) | ~$0.50 | `batch-delete-image` every tag (latest + sha + v*). **Repo shells stay** (TF-managed, $0 empty). Restart = rebuild + push all 4 images (+30–60 min, §F) |
| **CloudWatch log groups ×7 + SNS alarms topic** (Tom's watchdog directive) | ~$0.10 | *"Remove all watchdog / cloudwatch triggers so we don't spend any $$$."* History loss accepted — git is the deploy history. Lambdas re-create their log groups on next invoke at restart |

> **⚠️ MANDATORY before any KMS/secret deletion — detach the Cognito Lambda triggers.** The kept ($0) user pool's **CustomEmailSender decrypts via the CMK**; deleting the key with triggers attached permanently breaks pool auth emails, and secrets hold values the Lambdas read. Execute the documented full-carry detach (COGNITO-EMAIL-1 rollback posture + the 2026-09-04 *`UpdateUserPool` resets omitted blocks* incident lesson): `aws cognito-idp update-user-pool --user-pool-id <id> --auto-verified-attributes email --device-configuration ChallengeRequiredOnNewDevice=false,DeviceOnlyRememberedOnUserPrompt=false --lambda-config "{}"` — **omitted blocks are RESET, so the auto-verified + device flags are mandatory even in the detach**. Pool falls back to `COGNITO_DEFAULT` sending; the 3 Lambda functions (PostConfirmation, PostAuthentication, CustomEmailSender) stay deployed, dormant, $0. Re-attach at restart per runbook §14.5 (one-call-all-triggers + KMSKeyID).

**KEEP (the hibernation steady-state — scorched, Tom-elected):**

| Resource | Monthly cost | Rationale |
|---|---|---|
| S3 marketing bucket + CloudFront `EXXXXXXXXXXXX2` + OAC | ~$1–2 | The hold page (Tom's "basics to serve static") |
| ACM certs (pilotfortrades wildcard+apex, us-east-1; p4tsites) | $0 | Free; required by CloudFront; needed at restart |
| **TF state backend (S3 state bucket + lock table)** | ~$0.10 | Without it there is no clean `terraform apply` restart |
| Cognito user pool (triggers detached) | $0 | Free tier; keeps all users; deleting loses the user base — pure downside |
| Lambda functions ×3 (dormant) | $0 | No invocations while detached; re-attached at restart |
| ECR repo shells ×4 (empty) | $0 | TF-managed; images purged per scorched |

**Cost model (sustained hibernation, month 2+):**

| Posture | Monthly | Composition |
|---|---|---|
| Current full prod (as-built §1) | ~$664–707 | — |
| `profile-off.sh` floor (superseded) | ~$102 | RDS+Redis+NAT+ALB+S3/CF+R53+EIP |
| HIBERNATE-1 v1.0 default (superseded by Tom's election) | ~$7–9 | + Secrets $4.40 + KMS $1 |
| **HIBERNATE-1 scorched — ELECTED (ADR-0021)** | **≈ $1–3 AWS** (+ $2 EUM TFN ⇒ ≤ ~$5) | CF/S3 ~$1–2 + TF state bucket ~$0.10 + Cognito/Lambdas/ECR shells $0 |

Month 1 will show prorated teardown charges — set expectations; the $10 Budgets alert governs month 2+.

### B.4 — Third-party posture (not AWS; checkpoint decisions in the prompt)

| Vendor | Idle cost | Recommendation (Tom confirms at execution) |
|---|---|---|
| AWS End User Messaging TFN `+18445550100` | ~$2/mo | **KEEP** — toll-free verification is *in progress*; releasing likely forfeits the application and restarts a weeks-long queue. Fits inside the $9 envelope |
| Telnyx platform + test numbers | ~$1.50/number | Release tenant/test numbers; platform number: keep if ≤$2 (preserves 10DLC campaign `CXXXXXX` association), else release — numbers re-provision fast at restart |
| Telnyx/TCR campaign `CXXXXXX` | verify | Check for monthly campaign fees; suspend if any (sole-prop campaigns are typically ~$1.50/mo via TCR) |
| SendGrid plan | verify | Downgrade to free tier if on a paid plan; keep sender-auth DNS (B.2) |
| Stripe | $0 | Test mode only (env-mgmt §4.1.1) — verify no live mode, no active subscriptions; leave test-mode webhook endpoints to 5xx harmlessly (Stripe disables failing endpoints after repeated failures — re-enable at restart) |
| Google Maps key | $0 idle | Optionally HTTP-referrer/IP-restrict during hiatus |
| **CloudWatch watchdogs** (alarms ×11, dashboard, log groups, SNS topic) | ~$1–2 → $0 | **Tom directive: destroy ALL** — zero monitoring spend. The single **AWS Budgets** `pilot-hibernation-floor` $10 alert is retained: **$0 (Budgets free tier — NOT a CloudWatch trigger)**; Tom may strike it, leaving zero standing monitors |
| GitHub Actions | $0 | Disable `deploy-marketing` + `deploy-production` workflows in the GitHub UI (guards against a stray push overwriting the hold page or deploying to a dead cluster); `e2e-nightly` cron already off |
| Apple Developer / Google Play / Cloudflare registrar ×2 / Google Workspace | existing renewals | **KEEP all** — email (mailto CTA), store presence, and domains must survive the hiatus |

---

## C. Execution Order

| Phase | Step | Owner | Verification gate before proceeding |
|---|---|---|---|
| **1. Pre-flight** | 1.1 `aws sts get-caller-identity` = `000000000000`. 1.2 `dig NS pilotfortrades.com` + `dig NS p4tsites.com` → confirm Cloudflare authoritative (already evidenced by the 2026-09-07 exports: `raina`/`viddy.ns.cloudflare.com` — re-verify live). 1.3 Cost Explorer baseline screenshot (last 30 days). 1.4 ✅ Verify zone exports committed at §B.1-2 paths (DONE — Tom; Architect-verified). 1.5 ✅ Verify TF state backup present at §B.1-3 path (DONE — Tom) | DevOps | NS = Cloudflare on both domains; committed artifacts re-confirmed |
| **2. Data backup** | ✅ **DONE (Tom, 2026-09-07)** — `backup_20260907_082049.sql` + `schema_dump_20260907_082031.sql` committed to `dev-docs/db-design/dbbackups/`. Residual executor gate: both files non-empty; data backup contains tenant/quote/invoice rows (grep spot-check) | ~~Tom~~ → executor spot-check only | **HARD GATE preserved: nothing in Phase 6 runs before the spot-check passes** |
| **3. Hold page** | 3.1 Author `infrastructure/marketing-hold/index.html` per §H (single self-contained file; zero forms; zero JS trackers). 3.2 Tom copy approval (§G-1/2). 3.3 Deploy: `aws s3 sync infrastructure/marketing-hold/ s3://pilot-production-marketing/ --delete` + `aws cloudfront create-invalidation --paths "/*"`. 3.4 CloudFront custom error responses: 403→`/index.html` (200), 404→`/index.html` (200) — every legacy URL renders the hold page. 3.5 Verify: apex 200, www 200, `/pricing` 200 (hold page, not old content), view-source shows no forms/no GA4 | DevOps | curl board green ×4 + Tom visual |
| **4. DNS cutover** | 4.1 Delete `api` + `app` records (pilotfortrades.com). 4.2 Delete `*` wildcard (p4tsites.com). 4.3 Verify `dig` NXDOMAIN ×3. 4.4 Verify keep-list intact against the zone export diff: MX/SPF/DKIM/DMARC/SendGrid/**ACM validation CNAMEs**/apex/www/p4tsites redirect | DevOps (+Tom console) | NXDOMAIN ×3 + zero unintended zone diff |
| **5. Third-party posture** | 5.1 Telnyx numbers/campaign per B.4. 5.2 AWS TFN kept (verify no action). 5.3 SendGrid plan check. 5.4 Stripe test-mode verification. 5.5 Disable the 2 deploy workflows (GitHub UI). 5.6 Optional Maps key restriction | Tom | Each row's disposition recorded in prompt appendix |
| **6. AWS teardown** | 6.1 Run `profile-off.sh` (graceful: ECS→0, GPU+bastion stop). 6.2 Toggle deletion protection OFF (ALB + RDS) via targeted apply. 6.3 Disable GuardDuty / Security Hub / Config recorder (CLI/console). **6.3b Detach Cognito Lambda triggers — full-carry `update-user-pool` per the §B.3 ⚠️ block (MANDATORY before 6.5's KMS/secret deletion; verify pool still shows EmailSendingAccount=COGNITO_DEFAULT after).** 6.4 Destroy RDS with `skip_final_snapshot=true` (Tom ruling; §G-4). 6.5 `terraform destroy -target=…` enumerated from `terraform state list`: module.compute (keep ECR repo shells), module.database (all), module.networking (all — VPC included), module.monitoring (**ALL** — alarms, dashboard, log groups, SNS topic per Tom's watchdog directive), module.security (**ALL** — secrets force-deleted ×11 first, then KMS `schedule-key-deletion` 7-day, IAM OIDC role may go with it), module.storage **except** marketing bucket + CloudFront + OAC (+ empty/delete assets bucket after checkpoint). **6.5b Purge all ECR images** (`batch-delete-image`; shells stay). 6.6 Delete GPU models EBS volume (orphan post-terminate). 6.7 Delete R53 hosted zone. 6.8 Orphan sweep: EC2 console (volumes/snapshots/EIPs), `aws resourcegroupstaggingapi` for `pilot-production` tagged remainders, Cost Explorer next-day sanity | DevOps | `terraform state list` post-destroy = §B.3 keep-list only; zero orphaned EIPs/volumes; 0 secrets; KMS pending-deletion; 0 ECR images |
| **7. Verification board** | 7.1 curl board re-run (site live, subdomains dead). 7.2 AWS Budgets budget `pilot-hibernation-floor` ($10 threshold → Tom email) created (free tier: 2 budgets). 7.3 Day-2 + day-7 Cost Explorer checks ≤ $9 run-rate; results in prompt appendix | DevOps + Tom | Day-7 run-rate ≤ $9 |
| **8. Documentation (same change — Rule 12.3)** | 8.1 `aws-infrastructure-as-built.md`: hibernation banner + state snapshot (what exists vs destroyed, dated). 8.2 `aws-env-mgmt-ops-plan.md`: hibernation section per its §10 rules. 8.3 `aws-ops-runbook.md`: new §17.2 (Cloudflare zone inventories + what was removed + recreation steps) and new §21 (Restart Runbook per §F). 8.4 `infrastructure/scripts/README.md` + `profile-off.sh` comments: hibernation note; fix stale Route 53 line → Cloudflare. 8.5 Supersede `aws-pilotfortrades-zone-export.json` (stale R53 export) with the Cloudflare exports at §B.1-2. 8.6 `pilot-docs-list.md` registry rows. 8.7 ADR-0020 + ADR-0021 (logged at design time). 8.8 Launch plan close artifacts at batch close. **8.9 Tom's end-of-batch checkpoint: commit + merge to `dev` once the verification board is green (his directive — the freeze point for the hiatus)** | DevOps (docs) → Tom (8.9) | All 9 land; checkpoint commit hash recorded in prompt appendix |

**Explicitly out of scope**: any application code change; any change under `frontend/apps/marketing/**` (the Next.js site stays frozen for restart — the hold page bypasses it entirely); Cognito/Lambda changes; Stripe object changes; new AWS services.

---

## D. New API Endpoints

**None.** This batch ships no backend work. The marketing `/api/v1/marketing/*` form endpoints die with the API (intended — the hold page has no forms).

---

## E. Pattern Reuse Decisions

- **§16 platform patterns**: N/A — no application UI ships. The hold page is static HTML and composes none of the locked patterns (no optimistic UI, no 409, no preview-before-send).
- **ADR-0016 (schema-restore provisioning + env-aware seeds)** is the restart data-path pattern: the post-hiatus DB is rebuilt by `provision_schema.py` + Alembic + seed orchestrators against a fresh RDS, with Tom's local `pg_dump` available for targeted data resurrection — rather than restoring an RDS snapshot. This is why skipping the RDS final snapshot is safe.
- **Profile-script model**: `profile-off.sh` is reused as the graceful-shutdown step (6.1), then the profile system is intentionally frozen; `generate-infra-state.sh` re-runs at restart to repopulate `.infra-state.env`.
- **Rule 10.8 / env-mgmt §10**: all secrets/env/vendor posture changes land in `aws-env-mgmt-ops-plan.md` in the same change.
- **Infrastructure-constraints compliance**: this batch *decreases* spend; the temporary suspension of mandated running posture (Multi-AZ RDS, Fargate-first, GPU presence) is recorded in ADR-0020 with explicit restart-restores wording. No guardrail is amended.

---

## F. Shared Module Interfaces — Restart Contract (the reactivation spec the runbook §21 operationalizes)

Post-hiatus restart must re-establish, in this order (est. one working day):

1. `terraform apply` (full) — VPC/NAT/ALB/ECS/RDS (fresh, new random password)/Redis/monitoring/security groups/KMS (**NEW CMK ⇒ new ARN** — TF rewires all references; nothing encrypted with the old key survives, by design). **RDS comes back EMPTY by design** (ADR-0016 model).
2. Secrets: TF re-creates the 11 secret containers (values empty) → **Tom re-enters all values from his external backup** (incl. new DB password wiring if TF-managed); the SendGrid API key may need rotation if his backup lacks it.
3. **ECR: rebuild + push all 4 images** (`pilot/api`, `pilot/worker`, `pilot/beat`, `pilot/web` — repo shells survived; builds per runbook §19 with the `cd`-anchored paths; **+30–60 min**) — ECS services cannot start until images land.
4. Data: `provision_schema.py` → Alembic head → `seed_prod_db.py --mode seed --stripe-mode test` (Groups A+B) → optional targeted restore from Tom's `dbbackups/` pair.
5. GPU: start (userdata re-pulls Whisper/Ollama to a fresh `/models`; ~20 min) → update `pilot/prod/gpu` URLs if the private IP changes.
6. **Cognito: re-attach the 3 Lambda triggers** — one-call full-carry `update-user-pool` (PostConfirmation + PostAuthentication + CustomEmailSender + KMSKeyID=new CMK ARN + `--auto-verified-attributes email` + `--device-configuration …`) per runbook §14.5; branded-email smoke (ForgotPassword) + DKIM/SPF check.
7. `generate-infra-state.sh` → `profile-b-app.sh light` smoke → `profile-c-full.sh`.
8. DNS: recreate `api` + `app` CNAMEs (→ new ALB DNS name) and `*.p4tsites.com` from the committed §B.1-2 zone exports; verify ACM certs still ISSUED.
9. Marketing: either keep the hold page (default until relaunch) or redeploy the Next.js export (`pnpm --filter marketing build` → `aws s3 sync out/ … --delete` + invalidation) and remove the CloudFront error-response mapping; re-enable deploy workflows.
10. Third-party: Telnyx numbers re-provision + campaign re-association; Stripe webhook endpoints re-enable; Maps key un-restrict.
11. Smoke: §19.6 deploy canary + founder-path smoke; Cost Explorer week-1 check against the ~$888 MVP baseline.

---

## G. Open Questions Resolved

| # | Question | Resolution |
|---|---|---|
| 1 | Hold-page copy — keep launch-imminent language? | **Neutralized.** Default copy (Tom approves at Phase 3.2): eyebrow "AI-Powered Tools for Electrical Contractors" · H1 "Pilot for Trades" · value prop "Voice-controlled quoting, dispatch, and job tracking — built for the field." · message *"We are not accepting new customers right now. For questions, reach us any time."* No countdowns, no "first in line", no founder/waitlist language |
| 2 | Keep the `mailto:sales@pilotfortrades.com` CTA? | **Keep** (Architect recommendation — it is a contact link, not a subscription form; Google Workspace stays live regardless). Tom may strike it at Phase 3.2, leaving a pure brand page |
| 3 | Designer gate (Rule 1.5) for the hold page? | **Tom waiver requested.** §H carries the complete content spec — a verbatim port of the already-approved `ComingSoonPage` (itself form-free by design) with §G-1 copy neutralization. No new UX, no new components. If Tom declines the waiver, `pilot-marketing-ui-designer` authors `mkt-hibernate-1-design-spec.md` first and Phase 3 waits |
| 4 | RDS final snapshot — keep the ~$2 safety net? | **Skip** per Tom's ruling (local `pg_dump` is the backup; restart follows ADR-0016 provisioning). Destroy uses `skip_final_snapshot=true`, which also dodges the fixed-identifier collision risk. If Tom flips this at execution: let TF create `pilot-production-final-snapshot` and add ~$2/mo to the keep-list |
| 5 | Scorched tier (delete 11 secrets + KMS + ECR images → ~$2–3/mo)? | **Not recommended as default** (SendGrid key is unrecoverable → rotation chore; $4.40 buys a zero-friction restart). Documented as an option; if elected, secrets are exported to Tom's local encrypted store (1Password/age) **before** deletion and KMS deletion is scheduled (7-day window) after secrets are gone |
| 6 | Why not Cloudflare Pages (free) instead of S3+CloudFront? | Rejected — abandons the TF-managed, profile-script-integrated hosting the restart depends on, for <$2/mo. New migration surface for zero functional gain |
| 7 | Delete Cognito too (Tom: "all else can be removed")? | **No** — $0/mo, and deletion destroys all users + the CustomEmailSender/PostConfirmation/PostAuthentication wiring that COGNITO-EMAIL-1/PLATFORM-SMS-B2 built. "Recreate later" is disproportionately expensive here. Same logic keeps ECR repos (~$0.50) |
| 8 | `site-config.json` / `SiteModeGate` interplay? | None — the hold page replaces the bucket content wholesale; the gate config is irrelevant until the Next.js site is redeployed at restart. `profile-off.sh` step 5 remains harmless |
| 9 | Status page / uptime monitoring for the hold page? | None configured today and none added (Tom: agree) — the $0 Budgets alert is the only standing guard |

### G.v1.1 — Tom's ratification (2026-09-07, verbatim)

| # | Answer |
|---|---|
| 1 | **Agree** (neutralized copy) |
| 2 | **Agree** — contact link only |
| 3 | **Waiver GRANTED** — no designer spec; §H is the build spec |
| 4 | **Agree — skip RDS snapshot**; backups already taken ×2 → `dev-docs/db-design/dbbackups/` (committed to his private repo; he is the sole accessor) |
| 5 | **SCORCHED ELECTED** — *"I have all of the secrets stored and backed up, so we can delete all secrets, kms and ecr images"* |
| 6 | Agree — direct S3 push stays the approach (Pages maybe later) |
| 7 | Agree — keep Cognito |
| 8 | Agree |
| 9 | Agree — no status page/uptime monitoring |

**G-10 (new, resolved at ratification)**: Deleting the KMS CMK breaks the kept Cognito pool's CustomEmailSender (decrypts via the CMK) and the Lambdas' secret reads → **mandatory trigger detach (full-carry `update-user-pool`, §B.3 ⚠️) before any KMS/secret deletion**; re-attach at restart per runbook §14.5. Folded into Phase 6.3b + §F-6.

**Standing directives (Tom, same message)**: ① destroy ALL CloudWatch watchdogs (alarms/dashboard/log groups/SNS topic) — zero monitoring spend; the single AWS Budgets $10 alert survives because it is **free-tier and not a CloudWatch trigger** (Tom may strike). ② Zone exports + TF state backup + DB backups committed at the §B.1 paths (Architect-verified 2026-09-07). ③ End-of-batch checkpoint = Tom's commit + merge to `dev` after the verification board is green.

---

## H. Surface Mockup Reference (hold page content spec)

**Surface**: `https://pilotfortrades.com` + `https://www.pilotfortrades.com` (+ all legacy paths via CloudFront error mapping) · **Platform scope**: web marketing only · **File**: `infrastructure/marketing-hold/index.html` (single self-contained file; **deliberately outside** `frontend/apps/marketing/**` so `deploy-marketing.yml` cannot trigger on it).

**Content blueprint** (port of `ComingSoonPage.tsx` to dependency-free HTML):

- **Layout**: single viewport-fit screen, vertically centered, `max-width 34rem`, works 375px→1440px; brand gradient background (135°, brand-600→brand-900) inlined from `apps/marketing/src/app/globals.css` token values; system font stack (no webfont fetch); the same inline check-badge SVG + "Pilot for Trades" wordmark.
- **Copy deck** (§G-1): eyebrow badge → H1 → ≤20-word value prop → neutral message → `mailto:` pill CTA (white pill on blue, §G-2) → footer: `© 2026 Example Holdings, LLC. All rights reserved.`
- **Hard exclusions**: no forms of any kind (no founder/charter application, no newsletter, no contact form), no JS trackers (GA4/GTM dropped — analytics intentionally dark), no links into legacy routes, no `site-config.json` dependency, no external assets except inline SVG.
- **SEO/meta**: `<title>Pilot for Trades</title>`, meta description from the value prop, `og:` minimal set; `robots.txt` left allowing (keeps the domain indexed over the hiatus); `sitemap` removed (single page).
- **Accessibility** (WCAG 2.2 AA, matching the source component): `aria-labelledby` on `<main>` → H1; contrast ≥ 4.5:1 for all text on the gradient (white/white-85/white-55 tokens already satisfy); CTA ≥ 24×24px target with visible `:focus-visible` ring; `prefers-reduced-motion` trivially satisfied (no animation); color-independent (no status semantics present).
- **Behavior**: CloudFront 403/404 → `/index.html` (200) means every bookmarked legacy URL (`/pricing`, `/blog/…`, `/charter`) renders the hold page instead of an error.

## I. Component Manifest

**Zero components.** One static file; nothing enters `packages/ui/`, `apps/web/`, `apps/mobile/`, or `apps/marketing/`. The Next.js `ComingSoonPage` component remains the canonical source for restart and is untouched.

---

## Verification Board (batch exit criteria)

| # | Check | Pass condition |
|---|---|---|
| 1 | `curl -sI https://pilotfortrades.com` and `/www.` | 200, hold-page content, no forms in source |
| 2 | `curl -sI https://pilotfortrades.com/pricing` (legacy deep link) | 200, hold-page content |
| 3 | `dig api.pilotfortrades.com` / `dig app.pilotfortrades.com` / `dig x.p4tsites.com` | NXDOMAIN ×3 |
| 4 | Zone diff vs export (both domains) | Only the intended deletions; MX/DKIM/SPF/DMARC/SendGrid/ACM-validation intact |
| 5 | `terraform state list` + console spot-checks | §B.3 scorched keep-list only; 0 secrets; KMS `PendingDeletion`; 0 ECR images; 0 CloudWatch alarms/log groups |
| 6 | Orphan sweep | 0 unattached EIPs, 0 leftover EBS volumes/snapshots, 0 R53 zones |
| 7 | AWS Budgets `pilot-hibernation-floor` | Active, $10, Tom's email, $0 (free tier) |
| 8 | Cost Explorer day-7 run-rate | ≈ $1–3/mo AWS (+ $2 TFN) — ≤ ~$5 total |
| 9 | Restart runbook (runbook §21) | Reviewed by Tom against §F — every step reproducible from committed docs alone |
| 10 | Docs landed (§C Phase 8, 8.1–8.7) | All present in one PR |
