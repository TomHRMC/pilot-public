# Implementation Prompt: INT-BUG-1 — Prod Deploy-Sync + Migration Verify + §19.6 Runbook Hardening

**Mode**: Pilot DevOps Engineer
**Batch**: INT-BUG-1 (Phase 1 — Pre-Founder Core, ord 1)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §3.1
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-int-bug-1-design.md` (v1.0) — §B migration application plan, §F §19.6-hardening spec, §G resolved questions
**Estimated session**: 3–4 hours (includes image builds + the Tom walkthrough working session, Task 5)
**Platform**: AWS ECS/RDS prod (`pilot-production`) + runbook docs — **no new resources, $0 cost delta**
**Blocks**: launch-plan §3.2 (Tom's prod seed converge), §3.13 (MFA-WIRE-1 prod smokes), §2 row 2-8 (C-B14 rehearsal), and the entire Phase 2 prod pass

> **Sequencing gate**: Task 1 requires Tom's SSH tunnel to prod (runbook §9.2). Confirm the tunnel is up with Tom before Task 1. On any tunnel/connection failure → **STOP and ask Tom** (per `.roo/rules/02-database-mcp-access.md`); do not retry blindly.

> **Prod state update (Tom, 2026-08-25)**: prod `alembic_version` is **already at repo head `58c3ad26129f`** — migration application is **out of scope** (no snapshot, no `upgrade`). Scope per design v1.2: row-level verification (Task 1 — critical, see the stamp-vs-upgrade caveat), **full image build + push from `main`** (Task 2 — Tom decision 2026-08-25: `:latest` tagging means a revision sync alone cannot guarantee latest code), the service revision sync (Task 3), the first deploy canary (Task 4), and the §19.6 hardening (Task 5). If Task 1 finds prod *older* than head after all → **STOP**, return to the Architect (the design §B.2 chain review covers only the 4-migration delta).

---

## ⚠️ MANDATORY STOP: Read These First

Before touching prod, read:

- **`.roo/rules-pilot-devops-engineer/blue-green-constraints.md`** — one service at a time, steady-state gates, rollback posture (non-negotiable)
- **`.roo/rules-pilot-devops-engineer/secret-management-policy.md`** — DB password via Secrets Manager → tunnel `DATABASE_URL` only; never echoed, logged, or committed
- **`dev-docs/devops/aws-ops-runbook.md`** — §8.1 (backend image build/push), §8.3 (web image build/push — build context is `frontend/`, Cognito build-args required), §9.2 (prod Alembic procedure), §9.7 (migration-sync workflow — this batch's verification derives from it), §12 (health checks), §16 (rollback), §19.6 (revision sync — the section you will harden), §19.7 (image hygiene)
- **The design doc** — §B (chain risk review + stamp-vs-upgrade caveat), §C (execution order), §F (the §19.6 rewrite spec you must implement in Task 5), §G (resolved questions — do not re-litigate; Q9 is why Task 2 exists)

### Critical constraints for this batch

- **Row verify BEFORE service sync** (design §B.1 stamp-vs-upgrade caveat — mandatory). `alembic_version == head` proves the revision marker, not the data: if prod was stamped rather than upgraded, the PLATFORM-SMS-B1/B2 template rows never inserted, and the new image's fail-loud loader 806s on boot. Task 1's row-level verify is the gate; do not sync services on a revision number alone.
- **If prod is NOT at `58c3ad26129f` at execution time** (drift since the 2026-08-25 confirmation): **STOP — return to the Architect before applying anything.** The design's risk review covers only the 4-migration delta (`ba16d3b7fb6f` → `9b71cbd75c5f` → `c9043c486324` → `58c3ad26129f`).
- **Migrations-BEFORE-sync remains the standing rule** for every future deploy (design §B.3) — it is codified into the §19.6 rewrite in Task 4.
- **Prod carries the live 10DLC campaign** (plan §3 standing policy). You are not sending any SMS in this batch, but never run seed scripts, test endpoints, or smoke flows against prod beyond the exact verification steps below.
- **`postgres-prod` MCP is contingency-only** (design §G Q5) — used only if the Task 4 canary fails and partial-signup state inspection is needed. Tom's tunnel + his confirmation first; read-only; STOP on connection error.
- **One-at-a-time order for Task 3**: `pilot-celery-worker` → `pilot-celery-beat` → `pilot-api` → `pilot-web`, one at a time, steady state between each. API goes last among the backend services so background workers are stable first; web last.
- **`:latest` tagging means revision parity ≠ image parity** (design §G Q9). Every `update-service` in Task 3 uses `--force-new-deployment` (pulls the fresh `:latest` pushed in Task 2), and the Task 4 canary proves it via image-digest comparison — a revision-number match alone says nothing about the code actually running.

---

## Background / Context

On 2026-08-09/10, prod drifted twice: (1) a `terraform apply` registered new task-definition revisions but services kept running old ones (Telnyx env vars silently absent — platform SMS never sent, no error anywhere); (2) the prod image carried a baked `.env` (fixed by §19.7). Root causes are fixed in code (ALPHA-FIX-1 ✅ 2026-08-11), and migrations were confirmed applied by Tom on 2026-08-25 — leaving the **migration-embedded row verify** (stamp-vs-upgrade, Task 1) and **unverified task-def revision parity** across all four services (Task 2) as the open items. Until this batch lands, the prod signup/billing paths are unverified and every downstream prod activity (seed converge, MFA smokes, C-B14 rehearsal, Phase 2) is blocked.

This batch: ~~(1) apply the pending migration chain to prod~~ **confirmed applied 2026-08-25 (Tom)** — reduced to a row-level verify; (2) **build + push fresh images from `main`** (§8.1/§8.3 — v1.2, Tom decision: sync-only cannot guarantee latest code under `:latest` tagging); (3) sync all four services onto the fresh images per §19.6; (4) run the first full deploy canary; (5) harden §19.6 with Tom so the drift class cannot recur; (6) codify the founder-period deploy policy.

---

## Tasks

### Task 1 — Pre-flight confirm + migration-embedded row verify (CRITICAL — stamp-vs-upgrade gate)

With Tom's tunnel up (`127.0.0.1:5433` → prod RDS):

```bash
cd backend && source .venv/bin/activate
export DATABASE_URL="postgresql://pilot_user:${DB_PASS}@127.0.0.1:5433/pilot_prod"
alembic current            # expect 58c3ad26129f (head) — confirmed by Tom 2026-08-25
unset DATABASE_URL
```

- If `58c3ad26129f` → continue to the row verify below.
- If **anything older** → **STOP** — report the revision to the Architect (design §B.2 covers only the 4-migration delta; no `upgrade` without a chain review).

Then verify the migration-embedded rows actually exist — `alembic_version` proves the revision marker, **not the data**: if prod was stamped rather than upgraded, the seed INSERTs never ran (runbook §9.6 warning). Extract the authoritative code lists from the two migration files — `_NOTIFICATION_TYPES` + `_NOTIFICATION_TEMPLATES` in `2026_08_10_1646-ba16d3b7fb6f_platform_sms_b1_pathway_c_templates.py` and the equivalents in `2026_08_16_1537-58c3ad26129f_platform_sms_b2_security_maintenance_.py` — then, via the tunnel (psql or the VS Code PostgreSQL extension), **read-only**:

```sql
-- one row per expected type code (PLATFORM-SMS-B1 ships 5; B2 adds its own set)
SELECT code, audience, is_active FROM public.notification_type
WHERE code IN (<codes from the two migration files>) ORDER BY code;

-- one row per expected template (system defaults are tenant_id IS NULL, channel 'sms')
SELECT notification_type_code, channel, is_active FROM public.notification_template
WHERE tenant_id IS NULL AND notification_type_code IN (<codes from the two migration files>)
ORDER BY notification_type_code;

-- the two new tables from the chain must exist
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name IN ('invoice_signoff', 'tenant_site');
```

**Gate**: every code from both migration files returns a row; both tables exist. **Any gap → STOP, escalate to the Architect with the diff** — do **not** hand-insert rows; the recovery path for a stamped DB is re-running the idempotent migration inserts / seed scripts per runbook §9.6, an Architect decision, not an ad-hoc fix. This gate is what makes the Task 3 service sync safe (the fail-loud loader reads these rows at boot).

### Task 2 — Build + push fresh images from `main` (§8.1 + §8.3) — **TOM LEADS, YOU SHADOW**

**Tom drives this task hands-on-keyboard** (his call, 2026-08-25): he runs the actual build/push commands so you see exactly what he runs when deploying to prod. This doubles as the **first half of the Task 5 §19.6 walkthrough** — what you record here becomes rewrite material. A revision sync alone cannot guarantee the latest code: ECR images are tagged `:latest`, so a task-def revision points at the tag, not a digest (design §G Q9) — this task puts the current code into ECR *before* the sync.

Your role:

1. **Prep the command sheet first** — from §8.1 (backend: one build → three repo tags `pilot/api`, `pilot/worker`, `pilot/beat`) + §8.3 (web: `frontend/` build context + Cognito build-args), adapted to current repo paths. Hand it to Tom before he starts; then **note where his actual commands diverge from it** — divergences are runbook drift you will fix in Task 5.
2. **Confirm the deploy commit** — clean working tree on `main`; `git log -1` is the intended deploy commit (COGNITO-EMAIL-1 is not yet merged and is intentionally **not** in this deploy). Record the SHA.
3. **Observe + record** every command Tom runs and its output (terminal log or notes — attach it to the Completion Summary).
4. **You own the verification gates** — Tom doesn't run these; you do, and you call pass/fail out loud:
   - **§19.7 hygiene check** on the fresh backend image **before any push**: `docker run --rm --entrypoint sh pilot-api:latest -c 'ls /app/.env 2>&1'` → must print *No such file or directory*. If it fails → **STOP — nothing pushes.**
   - **Digest capture** post-push for all four repos: `aws ecr describe-images --repository-name <repo> --image-ids imageTag=latest --query 'imageDetails[0].imageDigest'` — recorded for the Task 4 canary.
5. **Flag in real time** anything that surprises you (unexpected build-args, an unrecognized tag, a push to a repo outside the expected four) — pausing is cheap; a wrong push to prod is not.

**Gate**: all four repos have the fresh `:latest`; hygiene check passed (called by you); digests recorded (by you); Tom's command log captured.

### Task 3 — Service revision sync (§19.6, one-at-a-time order)

Run the §19.6 Step 1 compare loop for `pilot-api pilot-celery-worker pilot-celery-beat pilot-web`. **Every** service gets `--force-new-deployment` (pulls the fresh `:latest` from Task 2 — required even when the revision number already matches, design §G Q9), in this order — `pilot-celery-worker` → `pilot-celery-beat` → `pilot-api` → `pilot-web`:

```bash
aws ecs update-service --cluster pilot-production --service <svc> \
  --task-definition <family>:<latest> --force-new-deployment --region us-east-1
```

- **One service at a time.** Wait for steady state (`aws ecs wait services-stable --cluster pilot-production --services <svc>`) before starting the next.
- After `pilot-api` stabilizes, spot-check `/ecs/pilot-api` startup logs for the expected config lines and **no** fail-loud template-loader error (the rows verified in Task 1 are what it loads).
- Re-run the Step 1 loop at the end — all four must show ✅ current.

### Task 4 — Deploy canary, first full run (design §F.1)

Run all five checks and record results — this exact set becomes the §19.6 canary block in Task 5:

| # | Check | Pass condition |
|---|---|---|
| 1 | Revision **+ image-digest** sync | Task 3 loop — all 4 services ✅ current; **and** each service's running task digest == the Task 2 ECR `:latest` digest (`aws ecs describe-tasks --cluster pilot-production --tasks <arn> --query 'tasks[0].containers[0].imageDigest'`) |
| 2 | API health | `curl -sf https://api.pilotfortrades.com/api/v1/health/celery` → HTTP 200 |
| 3 | OpenAPI shape | `curl -sf https://api.pilotfortrades.com/api/v1/openapi.json` contains every sentinel path in design §F.2 (platform-SMS phone endpoints, tenant-site, signoff, mfa) |
| 4 | Migration parity | prod `alembic current` (tunnel) == `58c3ad26129f` |
| 5 | Image hygiene | §19.7 check on the currently deployed image — `ls /app/.env` → *No such file or directory* |

For check 3, a compact assertion:

```bash
curl -sf https://api.pilotfortrades.com/api/v1/openapi.json | python3 -c "
import json,sys
spec=json.load(sys.stdin)
need=['/api/v1/signup/{tenant_id}/phone/consent','/api/v1/signup/{tenant_id}/phone/send-optin','/api/v1/tenant-site','/api/v1/public/tenant-sites/{slug}','/api/v1/invoices/{invoice_id}/signoff','/api/v1/jobs/{job_id}/signoff-context','/api/v1/users/me/mfa-status','/api/v1/settings/tenant/mfa-required']
missing=[p for p in need if p not in spec['paths']]
print('MISSING:',missing) if missing else print('✅ all sentinels present')
"
```

Any check fails → **STOP**: rollback per runbook §16 (and note the `:latest` rollback corollary in the Rollback Plan below) before any second attempt; note the failure in the runbook incident log; escalate to the Architect. Only if signoff-path failures point at signup state does the `postgres-prod` partial-signup inspection apply (design §G Q5 — tunnel + Tom confirmation, read-only).

### Task 5 — §19.6 hardening working session with Tom (design §F)

The build/push portion of the walkthrough already happened live in Task 2 (Tom-led — use your command-log recording + divergence notes). In this session Tom walks you through the **remaining** sections he uses to deploy prod (migrate-check, sync, post-deploy verify). Then rewrite `aws-ops-runbook.md §19.6` to current reality — presented as the **post-build half of one deploy flow** (§8.1/§8.3 build+push → §9.2/§9.7 migrate-check → §19.6 sync → canary), with cross-links instead of duplicated procedures:

1. **Keep** the Steps 1–3 sync loop + the 2026-08-10 mode-toggle addendum (still correct).
2. **Add the Deploy Canary subsection** (design §F.1) — the five-check table + the openapi assertion one-liner from Task 4, marked "run as the last step of EVERY deploy."
3. **Add the sentinel list** (design §F.2) with a maintenance note: "extend this list on each shipped batch that adds API surface."
4. **Add the Migration-Verify step** (design §F.3) — prod `alembic current` == repo head **before** the service sync, non-skippable.
5. **Add the Founder-Period Deploy Policy block** (design §F.4) — manual deploys through the founder beta; off-hours; one at a time; announced; every deploy ends with sync + canary.
6. Cross-link §19.6 ↔ §9.7 so the migration workflow and the deploy checklist reference each other.

### Task 6 — Full health check + close-out

Run the §12 health-check block end to end (ECS services, API health, web, marketing, RDS, Redis, bastion, GPU). All green → batch complete. Then:

1. Append the Completion Summary (template below) to **this prompt's ending appendix** — per ADR-0017 nothing is pasted into the launch plan.
2. Notify Tom: §3.2 (prod seed converge, §2 row 2-1), §3.13 (MFA-WIRE-1 Step 7 + SMS smokes), and §2 row 2-8 (C-B14 rehearsal) are now unblocked.

---

## Rollback Plan

- **Migration branches are N/A** (prod confirmed at head 2026-08-25 — no `upgrade` runs in this batch). If the Task 1 row verify finds missing rows (stamped-DB case), that is a STOP-and-escalate, not a rollback.
- **Service regression after sync** (Tasks 3–4): pin the affected service to its prior task-def revision per runbook §16/§19.2. The old image is forward-compatible with the migrated schema (design §B.3), so rolling a service back does **not** require touching the DB. **`:latest` rollback corollary**: pinning a prior revision restores prior env config but still points at `:latest` — a force-new-deployment would re-pull the *new* (suspect) image. To roll back code, first re-tag/re-push the prior known-good digest as `:latest` (Task 2 records digests at every deploy for exactly this), then force-new-deployment.
- **Canary failure**: same as above — rollback first, diagnose second, incident-log always.

---

## Definition of Done

- [ ] Both DevOps rule files + runbook §9.2/§9.7/§12/§16/§19.6/§19.7 + design doc read before touching prod
- [ ] Task 1: prod revision re-confirmed == `58c3ad26129f`; all PLATFORM-SMS-B1 + B2 type/template rows verified present; `invoice_signoff` + `tenant_site` exist (stamp-vs-upgrade gate passed)
- [ ] Task 2 (Tom-led, you shadow): backend + web images built from the confirmed `main` commit; **you** ran the §19.7 hygiene check pre-push (passed) + captured all four digests; Tom's command log + divergence notes recorded
- [ ] Task 3: all 4 services force-new-deployed onto the fresh images, one-at-a-time order, steady-state between; no fail-loud loader error in `/ecs/pilot-api`
- [ ] Task 4: all 5 canary checks pass and recorded (incl. image-digest parity)
- [ ] Task 5: §19.6 rewritten — full deploy-flow framing + canary block + sentinel list + migration-verify step + founder deploy policy; §19.6 ↔ §8.1/§8.3/§9.7 cross-linked; Tom walked the sections he actually uses and signed off on the rewrite
- [ ] Task 6: §12 health check all green; Tom notified that §3.2 / §3.13 / §2 row 2-8 are unblocked
- [ ] No SMS, seed scripts, or test endpoints fired against prod beyond the steps above
- [ ] Completion Summary appended to this prompt's ending appendix (below)

---

## Appendix — Completion Summary

Fill in on completion (this is the only place the summary lives — ADR-0017):

```markdown
### INT-BUG-1 — Prod Deploy-Sync + Migration Verify + §19.6 Hardening: Completion Summary

**Completed**: 2026-08-25
**Mode**: Pilot DevOps Engineer

#### What Was Accomplished
- Prod revision re-confirmed at head `58c3ad26129f` (Tom, 2026-08-25) — no migrations applied; row verify passed (stamp-vs-upgrade gate)
- Template/table verify: 7 notification types (5 B1 + 2 B2) + 7 notification_template rows (system defaults, tenant_id NULL, channel sms) present; `invoice_signoff` + `tenant_site` exist — prod was upgraded, not stamped
- Images built from `feature/post-signup-lp-branch-work` @ `8a405e09` + pushed **Tom-led** (command log: Tom ran §8.1 backend build → 3 ECR tags + §8.3 web build with Cognito build-args); api/worker/beat digests `sha256:81380f42...3d526`, web digest `sha256:3221f18b...e630`; §19.7 hygiene check passed pre-push (both images: `/app/.env` → No such file or directory)
- Services force-new-deployed one at a time onto the fresh images (Tom ran update-service, DevOps shadowed + verified):
  - pilot-celery-worker: stable, digest parity ✅
  - pilot-celery-beat: stable, digest parity ✅
  - pilot-api: stable, digest parity ✅, clean startup logs (no ERROR, no fail-loud template-loader)
  - pilot-web: stable, digest parity ✅
- First full deploy canary: 5/5 pass (incl. image-digest parity); check 3 adapted to repo `backend/openapi.json` (live openapi.json intentionally disabled in prod — `openapi_url=None` in `backend/app/main.py`)
- §19.6 rewritten with Tom: full deploy-flow framing + copy-paste sync script (one at a time, automatic steady-state + digest + log verification) + canary block + sentinel list + migration-verify step + founder deploy policy + cross-links §19.6 ↔ §8.1/§8.3/§9.7/§16/§19.7; runbook version bumped 3.6 → 3.7

#### Prod State After
| Item | State |
|---|---|
| Prod alembic revision | `58c3ad26129f` |
| Services on latest task-def | pilot-api ✅ (rev 7) / worker ✅ (rev 4) / beat ✅ (rev 4) / web ✅ (rev 5) |
| Image-digest parity | all 4 running tasks == ECR `:latest` digests |
| Canary | 5/5 pass on 2026-08-25 |
| §12 health check | all green (GPU stopped — expected, not needed for this batch) |

#### Docs Updated
- `aws-ops-runbook.md` §19.6 (hardened — full rewrite) + §9.7 Step 6 cross-link to §19.6 + version 3.7

#### Runbook Drift Captured (for future fixes)
- §8.1/§8.3 say "from `main`" but repo has no `main` — builds come from latest dev/feature branch (documented in §19.6 branch-model note)
- §8.1 fires backend update-service calls back-to-back without explicit ordering — §19.6 now codifies one-at-a-time order (worker → beat → api → web)
- Canary check 3 originally specified curling live openapi.json — prod disables it; §19.6 documents repo-spec + digest-parity as the correct method

#### Unblocked
- §3.2 prod seed converge (Tom) · §3.13 MFA-WIRE-1 prod smokes (Tom) · §2 row 2-8 C-B14 rehearsal (Tom)
```
