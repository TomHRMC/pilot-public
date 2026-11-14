# Batch Design: INT-BUG-1 — Prod Deploy-Sync + Migration Verify + §19.6 Runbook Hardening

**Version**: 1.3
**Date**: 2026-08-25
**Author**: Pilot Architect
**Changelog**: v1.1 (2026-08-25) — prod revision confirmed by Tom as `58c3ad26129f` (repo head) **before execution**: migration application removed from scope (§B.1/§C); template-row verify elevated to the critical gate (§B.1 stamp-vs-upgrade caveat). v1.2 (2026-08-25, Tom decision) — batch now includes the **full manual image deploy** (build + push from `main` per runbook §8.1/§8.3) before the revision sync: `:latest` tagging means revision parity ≠ image parity, so sync-only could never guarantee latest code (§G Q9). Canary check 1 gains image-digest parity (§F.1). v1.3 (2026-08-25, Tom decision) — **Tom leads the build/push step hands-on-keyboard** (§C row 2): the DevOps engineer shadows, records Tom's actual commands (walkthrough first half — input to the §19.6 rewrite), and owns the verification gates (§19.7 hygiene check, digest capture).
**Batch**: INT-BUG-1 (Phase 1, ord 1 — launch plan §1.1 / §3.1)
**Owner**: Pilot DevOps Engineer (executing); Tom (§19.6 walkthrough participant)
**Prompt**: `batch-int-bug-1-devops-prompt.md`
**Source plan**: `pilot-launch-plan.md` §3.1 (scope items 1–5 + exit criteria)
**Estimated session**: 3–4 hours (incl. the Tom walkthrough working session)
**Cost impact**: **$0** — no new AWS resources, no new third-party service (infrastructure-constraints §1: no founder cost review required)

---

## A. Input Read Summary

| Input | What was read / verified | Date |
|---|---|---|
| `pilot-launch-plan.md` | §1.1 row 1 (INT-BUG-1, depends on none); §3.1 full card (scope 1–5, exit); §7 gate row; §3.13 (MFA-WIRE-1 tail — blocked on this batch); §3.14 (Tom parallel track) | 2026-08-25 |
| `pilot-launch-plan-archive-2026.08.24.md` | INT-BUG-1 history row + E2E-REMAIN fold-in disposition | 2026-08-25 |
| `aws-ops-runbook.md` | §9.2 (prod Alembic procedure), §9.7 (full migration-sync workflow, 6 steps), §12 (health checks), §19.6 (current revision-sync procedure), §19.7 (image hygiene) | 2026-08-25 |
| `.roo/rules-pilot-devops-engineer/blue-green-constraints.md` + `secret-management-policy.md` | Both DevOps rule files | 2026-08-25 |
| `batch-signup-ga-1-devops-prompt.md` | DevOps prompt structure precedent (header block, MANDATORY STOP, tasks, rollback, DoD, completion appendix) | 2026-08-25 |
| `backend/migrations/versions/` (August chain) | Read `ba16d3b7fb6f`, `9b71cbd75c5f`, `c9043c486324` `upgrade()` bodies + `58c3ad26129f` identifiers — risk review in §B | 2026-08-25 |
| `postgres-local` MCP | `SELECT version_num FROM alembic_version` → `58c3ad26129f` — dev DB is at repo head | 2026-08-25 |
| `backend/openapi.json` | Canary sentinel paths verified present (tenant-site, signoff, mfa, phone/consent); `sms_consent_status` **absent** → §G Q3 | 2026-08-25 |

---

## B. Migration Plan — Migration *Application* Plan (no new migrations authored)

This batch authors **zero** new migrations. It applies the already-merged, already-dev-tested pending chain to prod, under the runbook §9.7 workflow.

### B.1 Pre-Migration Verification (state at design time)

| DB | Revision | Source |
|---|---|---|
| Dev (local Docker) | `58c3ad26129f` (head — `platform_sms_b2_security_maintenance_templates`) | `postgres-local` MCP, 2026-08-25 |
| Prod | **`58c3ad26129f` — at repo head** (confirmed by Tom 2026-08-25, pre-execution). Pending chain: **zero migrations — application removed from scope** | Tom, 2026-08-25 |

> **⚠️ Stamp-vs-upgrade caveat (v1.1)**: `alembic_version == head` proves the *revision marker*, not the *data*. If prod reached head via `alembic upgrade`, the migration-embedded rows exist; if via schema-restore + `alembic stamp` (§9.5/§9.6 warning), the seed INSERTs never ran. The prompt's row-level verify is therefore the **critical gate** before the service sync — the fail-loud loader reads those rows, not the revision marker.

### B.2 Chain Review — Historical Record (v1.1: all four confirmed applied on prod; review stands as the §9.7 Step 2 record)

| # | Revision | Batch | Content | Risk |
|---|---|---|---|---|
| 1 | `ba16d3b7fb6f` | PLATFORM-SMS-B1 | Data-only: 5 `notification_type` rows (`ON CONFLICT DO NOTHING`) + 5 `notification_template` rows (`WHERE NOT EXISTS` guard). **This is the fail-loud loader's dependency.** | **LOW** — idempotent seed inserts; value-scoped downgrade exists |
| 2 | `9b71cbd75c5f` | CE-1 | New table `invoice_signoff` (all four audit columns ✓, partial unique index, CHECK) + 4 **nullable** columns on `payment` | **LOW** — additive only |
| 3 | `c9043c486324` | C-B16 | DDL-only: new table `tenant_site` (25 cols, four audit columns ✓, 3 unique indexes, `updated_at` trigger) + nullable ALTER on `tenant_10dlc_profile` | **LOW** — additive only |
| 4 | `58c3ad26129f` | PLATFORM-SMS-B2 | Security-maintenance template seed rows (same guarded-insert pattern as #1) | **LOW** — idempotent seed inserts |

**Architect chain risk-review (§9.7 Step 2 — completed at design time)**: all four migrations are additive — new tables, nullable columns, guarded seed INSERTs. No data-affecting UPDATEs, no NOT NULL additions to populated tables, no drops, no PK renames. **Safe to run `alembic upgrade head` against prod.** If Task 1 shows prod is *further behind* than `7f57c3f5f15c` (chain longer than these 4), the engineer STOPs and returns to the Architect for an extended chain review before applying anything.

### B.3 Ordering Rule (mandatory)

**(v1.1: moot for this execution — zero pending; retained as the standing deploy rule.)** **Migrations run BEFORE the service revision sync** (runbook §9 principle, line 1118). Two reasons:
1. The new image's PLATFORM-SMS-B1 **fail-loud template loader** 806s on boot if the `ba16d3b7fb6f` rows are absent — syncing services first would take prod down.
2. The pending chain is purely additive, so the **old** image keeps working against the migrated schema (forward-compatible). No deploy-window breakage.

### B.4 Not applicable

3-part NOT NULL pattern, new-table trigger mandates, and DDL authoring rules are N/A — this batch creates no schema. Seed Data Rollout (Rule 11.5) is N/A — the migration-embedded seed rows were already rolled out by their owning batches (PLATFORM-SMS-B1/B2, C-B16, CE-1); this batch only executes them on prod.

---

## C. Execution Order

| # | Step | Runbook basis | Gate to proceed |
|---|---|---|---|
| 1 | **Pre-flight confirm + row verify (CRITICAL)** — via Tom's tunnel: `alembic current` == `58c3ad26129f` **and** the migration-embedded rows (PLATFORM-SMS-B1/B2 types + templates) + new tables (`invoice_signoff`, `tenant_site`) exist. Guards the §B.1 stamp-vs-upgrade caveat | §9.7 Step 1; §B.1 caveat | Revision == head AND all rows present; else STOP → Architect |
| 2 | **Build + push fresh images from `main`** (v1.2; v1.3 — **Tom leads hands-on-keyboard**, DevOps shadows + records: first half of the §19.6 walkthrough) — backend built once, tagged + pushed for api/worker/beat repos (§8.1); web built from `frontend/` with Cognito build-args (§8.3); §19.7 hygiene check on the backend image **before** push (engineer-run gate); deploy commit confirmed with Tom (clean tree); engineer captures Tom's command log + the pushed digests | §8.1, §8.3, §19.7 | Images pushed; hygiene check passes; digests recorded |
| 3 | **Service revision sync** — `--force-new-deployment` (pulls fresh `:latest`) + §19.6 Steps 1–3 across all four services (`pilot-api`, `pilot-celery-worker`, `pilot-celery-beat`, `pilot-web`), one service at a time, steady state between | §19.6; blue-green constraints | All ✅ current + digest parity |
| 4 | **Deploy canary — first full run** (new §F spec): revision + image-digest sync, health, openapi shape, migration parity, image hygiene | §F | All 5 checks pass |
| 5 | **§19.6 hardening working session with Tom** — walk the exact sections Tom uses to deploy; rewrite §19.6 to current reality (full build→push→sync→canary flow) + codify founder deploy policy | §F | Rewrite merged |
| 6 | **Full §12 health check** + close-out (completion summary, notifications) | §12 | All green |

(v1.1: the former snapshot + `alembic upgrade` steps were removed — prod confirmed at head 2026-08-25. No DB writes remain in this batch. v1.2: added the image build/push step — Tom decision 2026-08-25, §G Q9.)

Steps 1–4 are the **prod deploy + verify** (scope items 1–3). Steps 5–6 are the **runbook hardening** (scope items 4–5).

---

## D. New API Endpoints

**None.** Ops-only batch — no application code changes, no new endpoints, no OpenAPI regeneration.

---

## E. Pattern Reuse Decisions

| Pattern / rule | Application |
|---|---|
| **Blue-green constraints** (DevOps rule file) | One service at a time in Step 5; wait for steady state before the next; rollback = pin service to prior task-def revision (runbook §16/§19.2) |
| **Secret-management policy** | DB password via Secrets Manager → tunnel `DATABASE_URL` pattern only; never echoed, logged, or committed |
| **§16 platform UX patterns** | N/A — no user-facing surface |
| **Cost guardrail** | $0 delta — no new AWS service, no new vendor. Within the $888 baseline |
| **MCP access rule** (`.roo/rules/02-database-mcp-access.md`) | Partial-signup state inspection (plan scope item 3) is **contingency only** — `postgres-prod` requires Tom's SSH tunnel + explicit confirmation; STOP on any connection error |

---

## F. Shared Module Interfaces — §19.6 Hardening Spec (the batch's doc deliverable)

No code interfaces. The deliverable is the **`aws-ops-runbook.md` §19.6 rewrite**, which must add these blocks (content authored in the working session with Tom — this is the required shape). v1.2 scope note: the rewrite presents §19.6 as the **post-build half of one deploy flow** — build/push/hygiene (§8.1/§8.3/§19.7) → migrate-check (§9.2/§9.7) → sync (§19.6) → canary (F.1) — with cross-links, not duplicated procedures:

### F.1 Deploy Canary (new subsection, run as the last step of EVERY deploy)

| # | Check | Command / assertion |
|---|---|---|
| 1 | Revision **+ image-digest** sync | §19.6 Step 1 loop — all 4 services `✅ current`; **and** running tasks' image digest == ECR `:latest` digest (v1.2 — required because `:latest` tagging makes revision-number comparison blind to image staleness; §G Q9) |
| 2 | API health | `curl -sf https://api.pilotfortrades.com/api/v1/health/celery` → HTTP 200 |
| 3 | OpenAPI shape | `GET /api/v1/openapi.json` contains all sentinel paths (§F.2) |
| 4 | Migration parity | prod `alembic current` == repo `alembic heads` (via tunnel) |
| 5 | Image hygiene | §19.7 — `docker run --rm --entrypoint sh <image> -c 'ls /app/.env'` → *No such file or directory* (on any newly pushed image) |

Any check fails → **STOP**; rollback per runbook §16 before any second attempt; incident noted in the runbook log.

### F.2 OpenAPI Sentinel List (maintained in §19.6 — extends on each shipped batch)

| Sentinel path | Proves deployed batch |
|---|---|
| `/api/v1/signup/{tenant_id}/phone/consent` + `/api/v1/signup/{tenant_id}/phone/send-optin` | PLATFORM-SMS-B1 (double opt-in) |
| `/api/v1/tenant-site` + `/api/v1/public/tenant-sites/{slug}` | C-B16 (tenant sites) |
| `/api/v1/invoices/{invoice_id}/signoff` + `/api/v1/jobs/{job_id}/signoff-context` | CE-1 (sign-off) |
| `/api/v1/users/me/mfa-status` + `/api/v1/settings/tenant/mfa-required` | MFA-WIRE-1 |

### F.3 Migration-Verify Step (codified)

"After any `terraform apply` touching `module.compute` **or** any deploy carrying a new migration: tunnel → `alembic current` on prod must equal repo head **before** the §19.6 service sync." (This is the existing §9.2/§9.7 discipline, pulled into the §19.6 checklist so it cannot be skipped.)

### F.4 Founder-Period Deploy Policy (new block — plan §3 standing policy, codified)

- **Manual deploys retained through the founder beta** — no CI/CD auto-deploy work.
- **Off-hours only · one deploy at a time · announced** (Tom posts before start + after canary).
- Every deploy ends with the §19.6 sync + canary (F.1); no exceptions.

---

## G. Open Questions Resolved

- **Q1 — What revision is prod actually on?** **Resolved 2026-08-25 (v1.1): `58c3ad26129f` — repo head, confirmed by Tom.** Migration application is out of scope; the remaining verification is row-level (§B.1 stamp-vs-upgrade caveat). If execution finds prod *older* than head after all (drift since confirmation), the STOP gate still applies: no `upgrade` without an Architect chain review.
- **Q2 — Migrations before or after the service sync?** **Before** — the fail-loud loader 806s without the `ba16d3b7fb6f` rows, and the additive chain is forward-compatible with the old image (§B.3). This is the ordering that prevents repeating the 2026-08-09/10 incident class.
- **Q3 — The plan's `sms_consent_status` openapi sentinel does not exist.** Verified 2026-08-25: no `sms_consent_status` in `backend/openapi.json` or `backend/app`. The incident-era field name was superseded; the real consent surface is `user_endpoint.consent_status` + `user_sms_consent_audit`, exposed via the signup phone endpoints. **Corrected sentinels are the §F.2 path list** (the launch plan §3.1 wording is updated in this same change per stewardship §12.3). The DB-level guarantee comes from the Step 4 template-row verify, not an HTTP field.
- **Q4 — Is `pilot-web` in the sync scope?** Yes — it is the 4th ECS service and is already in the §19.6 Step 1 loop; its env vars (`NEXT_PUBLIC_API_URL` etc.) drift the same way. (The §3.14 DevOps env-var tail sets `NEXT_PUBLIC_API_URL` — separate item, not this batch.)
- **Q5 — When is partial-signup state inspection needed?** Only as a contingency if the canary fails after sync. `postgres-prod` via Tom's tunnel per `.roo/rules/02-database-mcp-access.md`; read-only; STOP on connection error.
- **Q6 — Any new AWS resources or cost?** None. $0 delta; no founder cost review required.
- **Q7 — What closes the E2E-REMAIN "staging environment smoke test" row?** This batch — replaced by prod verification + the F.1 deploy canary (Tom-approved 2026-08-24, plan §3.1 "Folds in").
- **Q8 — Does `aws-infrastructure-as-built.md` need an update?** No deployed-resource change (task-def revisions of existing services only). The runbook §19.6 rewrite is the only infra-doc update. (Stewardship §12.1 — Architect verifies on close.)
- **Q9 — Does a revision sync alone guarantee prod runs the latest code? (Tom, 2026-08-25)** **No.** ECR images are tagged `:latest`; a task-def revision points at the tag, not a digest. A `--force-new-deployment` pulls whatever `:latest` is *at that moment* — so if no fresh image was pushed, even a "successful" sync runs the old code, and the §19.6 revision-number loop cannot see it (revision parity ≠ image parity). Resolution (v1.2): the batch builds + pushes fresh images from `main` (runbook §8.1/§8.3) **before** the sync, and the canary's check 1 gains an **image-digest parity** assertion (running task digest == ECR `:latest` digest) as the durable proof. Rollback corollary: pinning a service to a *prior revision* does not roll back code under `:latest` — re-push the prior known-good digest as `:latest` first (digests are recorded at every deploy for exactly this). This also makes the §19.6 rewrite cover the true end-to-end deploy flow Tom runs.
