# Implementation Prompt: HIBERNATE-1 — Project Hibernation: AWS Deep Teardown + Static Hold Page + Cloudflare DNS Cutover

**Mode**: Pilot DevOps Engineer
**Batch**: HIBERNATE-1 (single part — infrastructure, DNS, static surface, vendor posture, docs)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` _(private)_ §1.1 Ord 33 + §3.33 card
**Design doc**: [`dev-docs/architecture-design/batch-designs/batch-hibernate-1-design.md`](../../architecture-design/batch-designs/batch-hibernate-1-design.md) **v1.1 APPROVED** — §B (destroy/keep lists, ⚠️ Cognito-detach block), §C (execution order), §F (restart contract), §G.v1.1 (Tom's ratifications), §H (hold-page build spec) are **binding**
**ADRs**: [`ADR-0020`](../../architecture-design/pilot-adr-log.md#adr-0020--project-hibernation--deep-aws-teardown-to-a-single-digit-cost-floor-all-dns-canonized-at-cloudflare) (hibernation posture) + [`ADR-0021`](../../architecture-design/pilot-adr-log.md#adr-0021--hibernation-tier-selection--scorched-elected-secretskmsecr-destroyed-cognito-lambda-detach-gates-kms-deletion) (scorched tier + detach gate)
**Prerequisites (all ✅ DONE by Tom 2026-09-07, Architect-verified — your job is to re-confirm, not redo)**:
- DB backup pair committed: `dev-docs/db-design/dbbackups/backup_20260907_082049.sql` + `schema_dump_20260907_082031.sql`
- Cloudflare zone exports committed: `dev-docs/devops/godaddy-cloudflare-archive/pilotfortrades.com/cloudlflare-pilotfortrades.com.txt` (typo as-committed) + `dev-docs/devops/godaddy-cloudflare-archive/p4sites.com/cloudflare-p4tsites.com.txt` (folder typo as-committed)
- Terraform state pull committed: `infrastructure/terraform/environments/production/2026.09.07-p4t-prod-data.json`
**Estimated session**: ~1 working day of execution + a day-2 and day-7 cost-verification tail
**Cost impact**: **~$664–707/mo → ≈ $1–3/mo AWS** (+ $2 EUM TFN ⇒ ≤ ~$5 total). This is a *decrease* — no Founder cost review required (infrastructure-constraints §1), but the posture suspension is governed by ADR-0020/0021.

---

## ⚠️ MANDATORY STOP: Read These First

- **The design doc in full.** The destroy/keep lists (§B.3), the ⚠️ detach block, and the execution order (§C) are the contract. Where this prompt and the design disagree, **stop and ask Tom** — do not improvise.
- **[`.roo/rules-pilot-devops-engineer/`](../../../.roo/rules-pilot-devops-engineer/)** — secret-management policy (you will be *deleting* secrets this time — only after the Cognito detach, and only the 11 `pilot/prod/*` entries) and state-locking rules (S3+DynamoDB backend — **the TF state backend is on the KEEP list; never target it**).
- **[`aws-ops-runbook.md`](../aws-ops-runbook.md) §14.5** — the full-carry `update-user-pool` posture (the 2026-09-04 incident: **omitted blocks are RESET** — `--auto-verified-attributes` and `--device-configuration` are mandatory on EVERY call, including the detach).
- **[`aws-cognito-prod-setup.md`](../aws-cognito-prod-setup.md)** — pool facts + the documented COGNITO-EMAIL-1 rollback posture (detach → `COGNITO_DEFAULT` fallback).

**Five hard rules for this batch (violations are unrecoverable-class mistakes):**

1. **Account guard**: every CLI session starts with `aws sts get-caller-identity` → must be account `000000000000` (`pilot-admin`). Anything else → abort.
2. **Backup gate**: nothing destructive (Task 6 onward) runs before the §Pre-Work artifact checks pass (Tom's three committed backups re-confirmed present + non-empty + the data backup greps tenant rows).
3. **Detach before delete**: the Cognito Lambda triggers are detached (Task 7) **before** any secret or KMS deletion (Task 10). The CustomEmailSender decrypts via the CMK — deleting KMS with triggers attached permanently bricks pool auth emails (ADR-0021).
4. **Deletion protection first**: ALB (`enable_deletion_protection`, compute module) and RDS (`deletion_protection`, database module) are TF-`true` — toggled `false` via targeted apply (Task 6) before any destroy.
5. **Point of no return is explicit**: Task 9 (RDS deletion) and Task 10 (secrets force-delete + KMS schedule) are the irreversible steps. Both carry a **Tom GO checkpoint** in-session. `terraform plan -destroy` output for Task 10 is reviewed with Tom **before** the destroy runs.

**Why this exists**: Tom is pausing the project for a few months (no customers live; prod holds seed/test data only). The public requirement during the hiatus is exactly one static hold page on apex+www; everything else goes to NXDOMAIN and the AWS bill drops to the static-serving floor. Restart (~1 day) is specified in design §F and lands as runbook §21 in Task 14.

---

## Pre-Work: Read These Files

```
dev-docs/architecture-design/batch-designs/batch-hibernate-1-design.md   ← the contract (read IN FULL)
dev-docs/devops/godaddy-cloudflare-archive/pilotfortrades.com/cloudlflare-pilotfortrades.com.txt   ← DNS delete/keep inventory (delete: api, app; keep: everything else)
dev-docs/devops/godaddy-cloudflare-archive/p4sites.com/cloudflare-p4tsites.com.txt                  ← delete: * wildcard; keep: apex/www AAAA + ACM-validation + SPF/DMARC
infrastructure/scripts/profile-off.sh + infrastructure/scripts/README.md ← Task 5 (graceful stop) + its staleness note for Task 14
infrastructure/terraform/environments/production/main.tf + variables.tf + terraform.tfvars          ← module wiring + var values
infrastructure/terraform/modules/compute/main.tf       ← ALB deletion-protection (line ~95); ECR repos (KEEP shells); GPU EBS blocks (lines ~558–575)
infrastructure/terraform/modules/database/main.tf      ← RDS deletion-protection + final-snapshot config (lines ~108–113)
infrastructure/terraform/modules/networking/main.tf    ← NAT+EIP (~85), bastion+EIP (~504)
infrastructure/terraform/modules/monitoring/main.tf    ← log groups, dashboard, alarms, SNS topic (ALL destroyed)
infrastructure/terraform/modules/security/main.tf      ← KMS key, 11 secrets, IAM OIDC role, Cognito pool, 3 Lambdas
infrastructure/terraform/modules/storage/main.tf       ← marketing bucket + CloudFront + OAC (KEEP) vs assets bucket + config-logs bucket (destroy)
frontend/apps/marketing/src/components/ComingSoonPage.tsx  ← §H content source (logo SVG, structure, footer string)
frontend/apps/marketing/src/app/globals.css            ← brand-600/brand-900 token values for the hold-page gradient
```

## Pre-Work: Live Baseline Captures (record ALL outputs in the Appendix)

```bash
# 0. Account guard
aws sts get-caller-identity --region us-east-1   # EXPECT "Account": "000000000000"

# 1. Backup gate — artifacts present + sane
ls -la dev-docs/db-design/dbbackups/backup_20260907_082049.sql dev-docs/db-design/dbbackups/schema_dump_20260907_082031.sql
grep -c "tenant" dev-docs/db-design/dbbackups/backup_20260907_082049.sql   # EXPECT > 0
ls -la "dev-docs/devops/godaddy-cloudflare-archive/pilotfortrades.com/cloudlflare-pilotfortrades.com.txt" \
       "dev-docs/devops/godaddy-cloudflare-archive/p4sites.com/cloudflare-p4tsites.com.txt" \
       infrastructure/terraform/environments/production/2026.09.07-p4t-prod-data.json

# 2. DNS authority — EXPECT both domains answer raina/viddy.ns.cloudflare.com (Cloudflare; R53 vestigial)
dig NS pilotfortrades.com +short
dig NS p4tsites.com +short

# 3. Site baseline (for before/after comparison)
curl -sI https://pilotfortrades.com | head -5
curl -sI https://api.pilotfortrades.com/api/v1/health | head -3 || true

# 4. Cognito pool baseline — save the FULL LambdaConfig JSON (Task 7 verify compares against it)
aws cognito-idp list-user-pools --max-results 10 --region us-east-1 --query 'UserPools[*].{Id:Id,Name:Name}'
POOL=<id from above; expected us-east-1_XXXXXXXXX — VERIFY, do not assume>
aws cognito-idp describe-user-pool --user-pool-id $POOL --region us-east-1 \
  --query 'UserPool.{LC: LambdaConfig, Email: EmailSendingAccount, Sms: SmsConfiguration, Dev: DeviceConfiguration, AVA: AutoVerifiedAttributes}'

# 5. Terraform inventory — the destroy enumeration source
cd infrastructure/terraform/environments/production
terraform state list | sort > /tmp/p4t-state-before.txt   # attach to Appendix

# 6. Cost baseline — console screenshot (Cost Explorer, last 30 days, daily granularity)
```

---

## Task 1 — Author the Hold Page (`infrastructure/marketing-hold/index.html`)

Create the directory + single self-contained file per design **§H** (build spec). Requirements recap (§H is binding — this is the summary):

- **Zero dependencies**: one HTML file, inline `<style>`, inline SVG logo (copy the check-badge SVG from `ComingSoonPage.tsx`), system font stack. No JS, no GA4/GTM, no webfonts, no external assets, no `site-config.json`, **no forms of any kind**.
- **Gradient**: `135deg` brand-600 → brand-900 — pull the exact token values from `frontend/apps/marketing/src/app/globals.css`.
- **Copy deck** (§G-1/§G-2 — Tom ratified; present verbatim at the approval gate):
  - Eyebrow badge: `AI-Powered Tools for Electrical Contractors`
  - H1: `Pilot for Trades`
  - Value prop: `Voice-controlled quoting, dispatch, and job tracking — built for the field.`
  - Message: `We are not accepting new customers right now. For questions, reach us any time.`
  - CTA (white pill, mailto only): `Contact us` → `mailto:sales@pilotfortrades.com`
  - Footer: `© 2026 Example Holdings, LLC. All rights reserved.`
- **Layout/a11y**: single viewport-fit screen, centered, `max-width 34rem`, 375px→1440px; `<main aria-labelledby>` → the H1; contrast ≥ 4.5:1 on the gradient; CTA ≥ 24×24px with `:focus-visible` ring; no animation.
- **Meta**: `<title>Pilot for Trades</title>` + meta description from the value prop + minimal `og:` set. Also add a minimal `robots.txt` (allow all) in the same folder.

**TOM GATE ① — copy approval**: show Tom the rendered page (open the file locally) before any deploy. Adjust copy to his edits; record final copy in the Appendix.

## Task 2 — Deploy Hold Page + CloudFront Error Mapping

```bash
aws s3 sync infrastructure/marketing-hold/ s3://pilot-production-marketing/ --delete --region us-east-1
aws cloudfront create-invalidation --distribution-id EXXXXXXXXXXXX2 --paths "/*" --region us-east-1
```

Then add Custom Error Responses so every legacy URL renders the hold page (S3-OAC returns **403** for missing keys; map both):

```bash
# Get current config, add CustomErrorResponses: 403→/index.html (200), 404→/index.html (200)
aws cloudfront get-distribution-config --id EXXXXXXXXXXXX2 --region us-east-1 > /tmp/cf-config.json
# Edit /tmp/cf-config.json: CustomErrorResponses.Items += two entries (ErrorCode, ResponsePagePath=/index.html, ResponseCode=200, ErrorCachingMinTTL=60)
aws cloudfront update-distribution --id EXXXXXXXXXXXX2 --distribution-config file:///tmp/cf-config.json --if-match <ETag from get> --region us-east-1
```

**Curl board (all must pass before Task 3)**:

```bash
curl -s https://pilotfortrades.com | grep -c "We are not accepting new customers"     # EXPECT 1
curl -sI https://www.pilotfortrades.com | head -1                                       # EXPECT 200
curl -s https://pilotfortrades.com/pricing | grep -c "Pilot for Trades"                 # EXPECT ≥1 (hold page, NOT old pricing)
curl -s https://pilotfortrades.com | grep -ci "<form\|ga4\|gtag\|turnstile"             # EXPECT 0
```

Also verify with Tom visually (incognito window) — his visual pass is part of the board.

## Task 3 — DNS Cutover (Cloudflare console — Tom's seat or paired)

In the `pilotfortrades.com` zone: **delete** the `api` and `app` CNAME records (both → `pilot-production-alb-…elb.amazonaws.com`). In the `p4tsites.com` zone: **delete** the `*` wildcard CNAME. **Touch nothing else** — specifically preserve: apex + `www` CNAMEs (CloudFront), all MX, the SPF/DKIM/DMARC/site-verification TXT, the SendGrid `emXXXX`/`s1._domainkey`/`s2._domainkey` CNAMEs, and **both ACM-validation CNAMEs** (`_<validation-name-1>`, `_<validation-name-2>` — cert renewal depends on them), plus the p4tsites apex/`www` AAAA placeholders + the edge Redirect Rule.

```bash
# Verify (propagation ~1–5 min on Cloudflare)
dig api.pilotfortrades.com +short    # EXPECT: empty (NXDOMAIN)
dig app.pilotfortrades.com +short    # EXPECT: empty (NXDOMAIN)
dig anything.p4tsites.com +short     # EXPECT: empty (NXDOMAIN)
curl -sI https://pilotfortrades.com | head -1   # EXPECT: still 200
```

Diff each zone against its committed export (§B.1-2) — the ONLY deltas allowed are the three deletions. Record the diff in the Appendix.

## Task 4 — Third-Party Posture (Tom checkpoints; record each disposition)

1. **AWS EUM toll-free `+18445550100`**: KEEP (per design §B.4 — verification in progress). No action; verify no pending changes.
2. **Telnyx** (console, Tom): release tenant/test numbers; platform number keep-if-≤$2 else release; check campaign `CXXXXXX` for monthly TCR fees → suspend if any. **TOM GATE ②**: dispositions recorded verbatim in the Appendix.
3. **SendGrid**: confirm plan tier; downgrade to free if paid. Sender-auth DNS stays (Task 3 preserved it).
4. **Stripe** (dashboard): confirm no real payments and zero active subscriptions (live-mode keys remain configured but unused). Leave test webhook endpoints to fail naturally (note: Stripe auto-disables failing endpoints — re-enable at restart, design §F-10).
5. **GitHub UI** (Tom): disable `deploy-marketing` + `deploy-production` workflows (Actions → workflow → ⋯ → Disable). Guards the hold page from a stray push. `e2e-nightly` cron already commented — confirm.
6. **Google Maps** (optional, Tom): HTTP-referrer/IP-restrict the key in Google Cloud console.

## Task 5 — Graceful App Shutdown

```bash
cd infrastructure/scripts && ./profile-off.sh
./profile-status.sh   # EXPECT: all ECS 0/0, GPU stopping/stopped, bastion stopped (alarms may show red — they die in Task 10)
```

Note: `.infra-state.env` and the profile scripts become stale from this point — do NOT regenerate; Task 14 documents this and design §F-7 regenerates at restart.

## Task 6 — Deletion-Protection Toggles (targeted apply)

Edit `infrastructure/terraform/modules/compute/main.tf` (`enable_deletion_protection = true` → `false` on `aws_lb.api`) and `infrastructure/terraform/modules/database/main.tf` (`deletion_protection = true` → `false` on `aws_db_instance.postgres`). **Also** in the database module set `skip_final_snapshot = true` (Tom's ruling — the `dbbackups/` pair is the data backup; avoids the fixed-name final-snapshot collision).

```bash
cd infrastructure/terraform/environments/production
terraform plan -target=module.compute.aws_lb.api -target=module.database.aws_db_instance.postgres
# EXPECT: in-place updates only (two ~ changes), zero replacements. Review with Tom, then:
terraform apply -target=module.compute.aws_lb.api -target=module.database.aws_db_instance.postgres
```

(Leave the flags `false` in the working tree — the Task-14 commit records the hibernation state; restart PR restores `true`.)

## Task 7 — ⚠️ Cognito Lambda Detach (BEFORE any secret/KMS deletion — ADR-0021)

Full-carry call — `--auto-verified-attributes` + `--device-configuration` are **mandatory** (the API resets omitted blocks — 2026-09-04 incident):

```bash
aws cognito-idp update-user-pool --user-pool-id $POOL --region us-east-1 \
  --auto-verified-attributes email \
  --device-configuration ChallengeRequiredOnNewDevice=false,DeviceOnlyRememberedOnUserPrompt=false \
  --lambda-config "{}"

# Verify: LambdaConfig EMPTY, EmailSendingAccount=COGNITO_DEFAULT, SmsConfiguration UNCHANGED, device config UNCHANGED
aws cognito-idp describe-user-pool --user-pool-id $POOL --region us-east-1 \
  --query 'UserPool.{LC: LambdaConfig, Email: EmailSendingAccount, Sms: SmsConfiguration, Dev: DeviceConfiguration}'
```

The 3 Lambda functions themselves are **not touched** (dormant, $0). Pool users untouched. Restart re-attaches per runbook §14.5.

## Task 8 — Console Service Disables (not in Terraform)

```bash
# GuardDuty (~$12/mo)
aws guardduty list-detectors --region us-east-1 --query 'DetectorIds' --output text | \
  xargs -I{} aws guardduty update-detector --detector-id {} --no-enable --region us-east-1
# Security Hub (~$5/mo)
aws securityhub disable-security-hub --region us-east-1 || true
# AWS Config recorder
aws configservice stop-configuration-recorder --configuration-recorder-name default --region us-east-1 || \
  aws configservice describe-configuration-recorders --region us-east-1   # get exact name, then stop
```

Verify each shows disabled/stopped in the console; record states in the Appendix.

## Task 9 — RDS Deletion — **TOM GATE ③ (POINT OF NO RETURN #1)**

Confirm with Tom in-session: *"The prod database is deleted now. Recovery = the `dbbackups/` pair + ADR-0016 re-provisioning. GO?"*

```bash
aws rds delete-db-instance --db-instance-identifier pilot-production --skip-final-snapshot --region us-east-1
aws rds wait db-instance-deleted --db-instance-identifier pilot-production --region us-east-1
# Reconcile TF state so the module destroy (Task 10) doesn't choke on the gone instance:
cd infrastructure/terraform/environments/production
terraform state rm module.database.aws_db_instance.postgres
```

Then `terraform destroy -target=module.database` (subnet group, parameter group, random_password) — review the plan first; EXPECT: only database-module resources, zero other modules.

## Task 10 — Terraform Targeted Destroys — **TOM GATE ④ (plan review + POINT OF NO RETURN #2: secrets/KMS)**

Enumerate exact addresses from `/tmp/p4t-state-before.txt`. Destroy in this order (review EACH `plan -destroy` with Tom before applying; the secrets/KMS step is irreversible):

```bash
# 10.1 Compute minus ECR repo shells (ECS services/cluster, ALB, TGs, listeners, GPU instance, autoscaling)
terraform destroy -target=module.compute  # if ECR repos live in this module, EXCLUDE them:
#   use per-resource -target list instead, omitting aws_ecr_repository.repos[*] + aws_ecr_lifecycle_policy.repos[*]

# 10.2 Networking (VPC, subnets, NAT+EIP, bastion+EIP, route tables, IGW, SGs if defined here)
terraform destroy -target=module.networking

# 10.3 Monitoring — ALL (alarms ×11, dashboard, log groups ×7, SNS topic + subscription)
terraform destroy -target=module.monitoring

# 10.4 Storage EXCEPT marketing bucket + CloudFront + OAC (+ cert if defined here)
#   FIRST: TOM GATE ④a — assets-bucket content check (aws s3 ls s3://pilot-production-assets --recursive | head)
#   Tom confirms "nothing irreplaceable" → empty incl. versions, then destroy:
aws s3 rm s3://pilot-production-assets --recursive --region us-east-1
aws s3api list-object-versions --bucket pilot-production-assets --query '{V: Versions[].{K:Key,I:VersionId}, D: DeleteMarkers[].{K:Key,I:VersionId}}' --region us-east-1
#   (delete every version + delete-marker, then:)
terraform destroy -target=module.storage.aws_s3_bucket.assets -target=module.storage.aws_s3_bucket.config_logs  # exact addresses from state list

# 10.5 Security — secrets + KMS LAST, in this exact order (detach already done in Task 7):
aws secretsmanager list-secrets --region us-east-1 --query 'SecretList[?starts_with(Name, `pilot/`)].Name' --output text
#   EXPECT exactly the 11 known secrets → force-delete each (NO recovery window):
for s in $(aws secretsmanager list-secrets --region us-east-1 --query 'SecretList[?starts_with(Name, `pilot/`)].Name' --output text); do
  aws secretsmanager delete-secret --secret-id "$s" --force-delete-without-recovery --region us-east-1
done
aws kms describe-key --key-id alias/pilot-production --region us-east-1 --query 'KeyMetadata.KeyId' --output text
aws kms schedule-key-deletion --key-id <KeyId> --pending-window-in-days 7 --region us-east-1
#   THEN destroy the rest of the module (OIDC role, SGs defined here, alias, Lambdas stay if TF-managed — they are $0 keep:
#   if the 3 Lambda functions + Cognito pool are in this module, EXCLUDE them via per-resource targets)
terraform destroy <per-resource targets for module.security minus aws_cognito_user_pool.prod, the 3 aws_lambda_function.*, and their log/permission resources>
```

**Note on the state backend**: if the TF state bucket / lock table appears in `terraform state list` (it normally does NOT — backends aren't self-managed), it is **excluded from every target list**. Verify before each destroy.

## Task 11 — ECR Purge + GPU Volume + R53 + Orphan Sweep

```bash
# ECR images (shells stay)
for repo in pilot/api pilot/worker pilot/beat pilot/web; do
  aws ecr list-images --repository-name $repo --region us-east-1 --query 'imageIds[*]' --output json > /tmp/imgs.json
  [ "$(cat /tmp/imgs.json)" != "[]" ] && aws ecr batch-delete-image --repository-name $repo --region us-east-1 --image-ids file:///tmp/imgs.json
done

# GPU models volume (orphaned at terminate — 20GB gp3, delete_on_termination=false)
aws ec2 describe-volumes --region us-east-1 --filters Name=status,Values=available Name=tag:Name,Values=*gpu* \
  --query 'Volumes[].{Id:VolumeId,Size:Size}'
aws ec2 delete-volume --volume-id <id> --region us-east-1

# Route 53 hosted zone (vestigial — NS is Cloudflare, verified Pre-Work)
aws route53 list-resource-record-sets --hosted-zone-id ZXXXXXXXXXXXXXXXXXXXX --region us-east-1
# delete all non-NS/SOA records via change-batch, then:
aws route53 delete-hosted-zone --id ZXXXXXXXXXXXXXXXXXXXX --region us-east-1

# Orphan sweep — EXPECT all empty:
aws ec2 describe-addresses --region us-east-1 --query 'Addresses[?AssociationId==null]'
aws ec2 describe-volumes --region us-east-1 --query 'Volumes[?State==`available`]'
aws ec2 describe-snapshots --region us-east-1 --owner-ids self --query 'Snapshots[].{Id:SnapshotId,Vol:VolumeSize}'
aws elbv2 describe-load-balancers --region us-east-1 --query 'LoadBalancers[].LoadBalancerName'
aws nat ... || aws ec2 describe-nat-gateways --region us-east-1 --filter Name=state,Values=available --query 'NatGateways[].NatGatewayId'
```

Any survivor → investigate + destroy (record in Appendix).

## Task 12 — AWS Budgets Guard ($0, free tier — design §B.4; Tom may strike)

```bash
aws budgets create-budget --account-id 000000000000 --region us-east-1 --budget '{
  "BudgetName": "pilot-hibernation-floor", "BudgetType": "COST", "TimeUnit": "MONTHLY",
  "BudgetLimit": {"Amount": "10", "Unit": "USD"},
  "CostTypes": {"IncludeTax": true, "IncludeSubscription": true, "UseBlended": false}
}' --notifications-with-subscribers '[{
  "Notification": {"NotificationType": "ACTUAL", "ComparisonOperator": "GREATER_THAN", "Threshold": 100, "ThresholdType": "PERCENTAGE"},
  "Subscribers": [{"SubscriptionType": "EMAIL", "Address": "<Tom email — confirm in-session>"}]
}]'
```

## Task 13 — Verification Board (design §Verification — ALL 10 rows)

1–4: re-run the Task 2 curl board + Task 3 dig board (site 200 on apex/www/deep-link; NXDOMAIN ×3; zone diff = 3 deletions only).
5: `terraform state list` post-destroy = **scorched keep-list only** (S3 marketing + CloudFront + OAC + ACM certs + Cognito pool + 3 Lambdas + ECR repo shells + any TF-unmanaged backend); `aws secretsmanager list-secrets` → 0 `pilot/` entries; `aws kms describe-key` → `PendingDeletion`; `aws ecr list-images` ×4 → empty; `aws cloudwatch describe-alarms` → 0; log groups → 0.
6: orphan sweep outputs empty (Task 11).
7: Budgets budget active.
8: **Day-2 + day-7** Cost Explorer run-rate checks (console screenshot both) — EXPECT ≈ $1–3/mo AWS (+ $2 TFN). Day-7 result rides as the batch tail; record both in the Appendix.
9: runbook §21 Restart Runbook reviewed by Tom against design §F — every step reproducible from committed docs alone.
10: Task 14 docs all landed in the working tree.

## Task 14 — Documentation (same change — Rule 12.3; then Tom's checkpoint)

1. **[`aws-infrastructure-as-built.md`](../aws-infrastructure-as-built.md)**: hibernation banner at top (date, ADR-0020/0021 links) + §1 table annotated (destroyed vs keep-list) — do NOT rewrite history; annotate state-as-of 2026-09-07.
2. **[`aws-env-mgmt-ops-plan.md`](../aws-env-mgmt-ops-plan.md)**: new hibernation section per its §10 rules (env state = hibernated; secrets = deleted w/ external backup; vendors = test/idle postures; TFN kept; restart pointer).
3. **[`aws-ops-runbook.md`](../aws-ops-runbook.md)**: new **§17.2** (Cloudflare zone inventories from the committed exports + the 3 deletions + recreation steps) and new **§21 — Restart Runbook** operationalizing design §F steps 1–11 verbatim (incl. secrets re-entry, ECR rebuild+push with `cd`-anchored build paths, Cognito re-attach §14.5 full-carry, DNS recreation from the zone exports, marketing redeploy option, smoke + §19.6 canary).
4. **[`infrastructure/scripts/README.md`](../../../infrastructure/scripts/README.md)** + [`profile-off.sh`](../../../infrastructure/scripts/profile-off.sh): hibernation note (scripts dormant until restart; `.infra-state.env` stale; fix the line-19 Route 53 comment → Cloudflare).
5. **`aws-pilotfortrades-zone-export.json` _(private)_**: mark superseded (header comment) by the `godaddy-cloudflare-archive/` exports.
6. **Prompt appendix** (below): complete the Completion Summary.
7. **TOM GATE ⑤ — checkpoint**: hand Tom a green verification board; **he commits + merges to `dev`** (his directive — the freeze point for the hiatus). Record the commit hash in the Appendix.

**Explicitly out of scope** (design §C): any application code change; any edit under `frontend/apps/marketing/**`; Cognito/Lambda code changes; Stripe object changes; new AWS services; launch-plan re-sequencing.

---

## Definition of Done

- [ ] Pre-Work baseline captures recorded (account, artifacts, NS, pool config, state list, cost screenshot)
- [ ] Hold page live: apex/www/deep-link 200 with Tom-approved copy; zero forms/trackers in source
- [ ] DNS: `api`/`app`/`*` NXDOMAIN; zone diffs = 3 deletions only; ACM-validation + email records intact
- [ ] Third-party dispositions recorded (Telnyx, SendGrid, Stripe, GitHub workflows, TFN kept)
- [ ] AWS teardown complete: keep-list only in state; 0 secrets; KMS PendingDeletion; 0 ECR images; 0 alarms/log groups; RDS/Redis/NAT/ALB/VPC/GPU/bastion gone; orphan sweep clean
- [ ] Budgets `pilot-hibernation-floor` active (or Tom-struck, recorded)
- [ ] Verification board 1–10 green (day-7 cost row may close as the tail)
- [ ] All Task-14 docs landed; Tom's checkpoint commit + merge to `dev` recorded

---

## Appendix — Completion Summary

> Filled in by the executing engineer at close (ADR-0017/0018). Include: baseline vs final state table (services, DNS, cost), Tom gate outcomes ①–⑤ (copy approval, Telnyx dispositions, assets-bucket confirmation, RDS GO, destroy-plan GO, checkpoint commit hash), any deviations from design with resolution, curl/dig evidence, day-2 + day-7 Cost Explorer figures, files changed list, and the exact `terraform state list` post-destroy output.
