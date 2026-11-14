# SD-9 — Voice AI Seed Data: `seed_scenario_voice_ai.py` + Second-Tenant Seed

**Batch code**: SD-9
**Owner**: Pilot Architect (design) → Python Engineer (implementation)
**Priority**: P1 — pre-Beta enabler (`pilot-launch-plan.md` Order 3, §2.0 item 14). Named (with HELP-B1) as the trigger to resume the deferred UI-INT-TEST full regression ("final seed-data density").
**Status**: v1.0 — AUTHORED 2026-08-18, awaiting Tom approval
**Estimate**: 4–5h Python (single batch; within Rule 9.6 scope limits)
**Cost impact**: $0 — no new AWS services, no infra change. Voice AI runs in Docker locally; prod GPU (`g4dn.xlarge`) already provisioned and is unaffected (Group C/D scripts are prod-refused per DB-MGMT-1 gating).

---

## 0. Context, Problem & Directive

**Launch-plan card (verbatim, §2.3 SD-9):** Seed `voice_command_log`, `voice_command_entity_link`, `conversation_session`, `conversation_message` for local dev (Voice AI runs in Docker locally). Enables Voice AI History, Command Detail, and Conversation Context surfaces to show real data. New `seed_scenario_voice_ai.py`. Not blocked by GPU (prod GPU already provisioned). Also: **multi-tenant seed** — ensure ≥2 tenants with distinct data exist in dev/QA to validate tenant isolation visually.

**Current state:**
- All five voice tables are **empty in every environment** (MCP-verified 0 rows, §A). They are listed in `README-seed-data.md §8.1` as "permanently excluded — requires live Voice AI session (Whisper + Ollama on GPU); blocked by GPU service dependency." That rationale is **stale**: the GPU instance is provisioned, Voice AI runs in Docker locally, and nothing about *seeding historical rows* requires the live pipeline — the same way `nec_calculation_log` is seeded without running the NEC service. This batch moves the five tables out of §8.1.
- The consuming surfaces exist and render empty states today:
  - **Voice AI History** — `VoiceSessionsPage.tsx` → `GET /api/v1/voice/sessions` (`voice_sessions.py`) listing sessions with derived per-day numbers (`get_sessions_with_numbers()`).
  - **Conversation Context / Session Detail** — `VoiceSessionDetailPage.tsx` + `VoiceMessageBubble.tsx` → `GET /api/v1/voice/sessions/{id}/messages`; renders `content_text` bubbles and a structured-data card for any `structured_content_json` payload.
  - **Command Detail / feedback review** — `GET /api/v1/voice/transcripts` + `GET/POST /api/v1/voice/feedback` (`voice_feedback.py`) reading `voice_command_log` + `voice_feedback`.
  - **Voice Analytics report** — `get_voice_analytics_report()` aggregating `voice_command_log` by intent/user/day with success-rate and p95 latency (null-latency rows excluded per F5).
- **Tenant isolation cannot be visually validated** — dev holds exactly **one** tenant (`00000000-…-0001`, MCP-verified). The card's multi-tenant requirement closes this.
- W-06 in `scenario-coverage-catalog.md` lists these four tables as ☐ unseeded (external-dep column: Whisper/Ollama — Phase 7 E2E; this batch is dev/QA seed only, no E2E critical path).

**Target state:** `seed_scenario_voice_ai.py` (Group D, scenario key `voice_ai`) seeds realistic, CHECK-constraint-valid, multi-user, multi-day voice history for the primary test tenant **and** a second tenant; `seed_second_tenant.py` (Group C) creates the second tenant (`…-0006`) with two users; `reset_dev_db.py` and `seed_qa_db.py` integrate both; README-seed-data is fully reconciled.

---

## A. Input Read Summary

| Input | What it contributed | Read? |
|---|---|---|
| `pilot-launch-plan.md` §2.3 SD-9 card + §2.1 Order 3 + UI-INT-TEST deferral note | Batch scope (4 named tables + multi-tenant seed); SD-9 is a named resume-trigger for the deferred full UI regression | ✅ |
| `backend/README-seed-data.md` §2–§10 (full) | Group A–D model; script inventory; §8.1 stale exclusion row to remove; deterministic-UUID registry (§5); DELETE safety rule (§7); scenario status registry (§9); run-order docs (§6) | ✅ |
| `mvp-arch.md` §6.1–6.7 (Voice AI pipeline, intent registry, context, sessions, deferred processing) | Intent vocabulary for `intent_detected`; `context_window_json` shape; `structured_content_json` render modes; `processing_status` pipeline semantics | ✅ |
| `scenario-coverage-catalog.md` W-06 | Four tables confirmed unseeded; GPU dep is E2E-only (P3) — dev seed is unblocked | ✅ |
| `backend/app/models/ai.py` (full) | SQLModel definitions for all 5 tables; AppendOnly nature of `conversation_message`; `voice_command_log` has **no** `created_by`; Vector(1024) embedding columns | ✅ |
| `backend/services/voice_session_service.py` | Sessions are **user-scoped**, `is_active=true` filtered; per-day `session_number` is **derived** (no column — arch §6.4 is aspirational); title fallback `title or context_summary` | ✅ |
| `backend/api/routes/voice_sessions.py` + `voice_feedback.py` | Endpoint query shapes the seed must satisfy (tenant-scoped selects; transcripts ordered `created_at DESC`) | ✅ |
| `backend/services/report_service.py` `get_voice_analytics_report` (lines 609–726) | Aggregation contract: group by intent/user/day; null latencies excluded; success-rate math — drives latency/user/day spread in seed content | ✅ |
| `frontend/apps/web/src/features/voice/` (all 5 files) | UI renders `content_text` + raw `structured_content_json` card; empty states confirmed | ✅ |
| `backend/migrations/scripts/seed_scenario_mobile_sync.py` (full) | Canonical scenario-script pattern: raw SQL `text()`, `get_db_session()`, `--mode seed/inspect/show` + `--reset`, `_env_profiles` wiring, natural-key idempotency | ✅ |
| `backend/migrations/scripts/reset_dev_db.py` (SCENARIOS, GROUP_D_TABLES, wipe/scenario dispatch) | Registration points; `mode_seed(tenant_id)` / `mode_reset(tenant_id)` module contract; child-first FK ordering; wipe is single-tenant-scoped | ✅ |
| `backend/migrations/scripts/seed_test_tenant.py` (tenant/user upserts) | Template for second-tenant inserts (user upsert cols, tenant upsert cols, charter tier runtime lookup) | ✅ |
| `backend/migrations/scripts/seed_qa_db.py` (full) | 11-step QA orchestration — SD-9 adds 2 steps (second tenant + voice_ai scenario) | ✅ |
| `backend/migrations/scripts/_env_profiles.py` | Group gating: prod allows A+B only → Group C (`seed_second_tenant.py`) and Group D (`seed_scenario_voice_ai.py`) are automatically prod-refused; `add_env_args` / `assert_group_allowed` / `assert_target_compatible` / `print_seed_banner` | ✅ |
| `pilot-architect-methods.md` §3 + `python-engr-std-prompt-inclusions.md` | Design-doc section requirements; Rule 11.5 Seed Data Rollout; Rule 11.1 DELETE safety | ✅ |

**MCP live-DB verification (postgres-local, 2026-08-18):**

| Check | Result | Notes |
|---|---|---|
| 5 voice tables — columns/nullability/defaults | Full column dumps verified for `conversation_session`, `conversation_message`, `voice_command_log`, `voice_command_entity_link`, `voice_feedback` | All SQL in this design uses only MCP-verified column names |
| 5 voice tables — row counts | **0 rows each** | Clean slate; no preservation concerns |
| CHECK constraints | `conv_session_status_chk` (active/ended/abandoned/expired/archived) · `conv_msg_role_chk` (user/assistant/system) · `chk_voice_command_log_processing_status` (NULL or pending_upload/uploading/transcribing/parsing/completed/failed) | Seed content validated against these sets |
| FK constraints | session→(tenant,user) · message→(session,tenant,user) · log→(tenant,user,message NULL) · entity_link→(log **RESTRICT**) · feedback→(log **SET NULL**) | Insert order: session→message→log→link/feedback; wipe order: feedback, link→log→message→session |
| `tenant` rows | **1 tenant** (`00000000-0000-0000-0000-000000000001` "Pilot Dev Tenant", 4 users) | Second tenant required |
| `tenant` columns | NOT NULL w/o default: `id`, `name`, `current_subscription_tier_id` (+audit) | Second-tenant insert needs charter tier FK |
| `subscription_tier` | `tier_name` values: charter (active), trial/starter/teams (dormant) | Runtime lookup `WHERE tier_name='charter'` — never hardcode the tier UUID |
| Test users | `…-0002` Dev Owner (owner) · `…-0003` Dev Technician (technician) · `…-0004` Dev Office · `…-0005` Dev Accountant | Sessions seed for owner + technician |
| `tenant_user` columns | NOT NULL: `tenant_id`, `user_id`, `role_code`, `status_id` (+audit) | `status_id` = `tenant_user_status` lookup `code='active' AND tenant_id IS NULL` |
| `user` columns (first 12) | `id`, `email` (citext), `first_name`, `last_name`, `is_platform_user` NOT NULL, … | Insert mirrors `seed_test_tenant.py` exactly (omits `is_platform_user` → server default) |
| Linkable Group D entities (tenant …-0001) | job 14 · quote 10 · job_time_entry 15 · customer 11 · invoice 15 · job_expense 13 | Entity-link targets exist; runtime lookups only (non-deterministic UUIDs) |

---

## B. Migration & Seed Rollout Plan

### B.1 Schema migrations

**None. Zero DDL in this batch.** All five tables exist with constraints in place. The audit-mixin DDL rule and 3-part NOT NULL pattern are not triggered.

### B.2 Seed Data Rollout (Rule 11.5 — mandatory)

| Layer | Change | Script(s) |
|---|---|---|
| **Layer 1 — Core/Platform** | None. No new lookup/reference rows. | — |
| **Layer 2 — Scenario (Group D)** | New `voice_ai` scenario: 8 `conversation_session` (6 tenant-1 + 2 tenant-B), ~24 `conversation_message`, ~16 `voice_command_log`, 6 `voice_command_entity_link` (tenant-1 only), 2 `voice_feedback` (tenant-1 only). Full content manifest in §F.2–F.5. | `seed_scenario_voice_ai.py` (new) |
| **Group C addition** | Second tenant `…-0006` "Pilot Dev Tenant B" + 2 users (`…-0007`, `…-0008`) + `tenant_user` rows + email `user_endpoint` rows. Minimal by design (§G-3). | `seed_second_tenant.py` (new) |
| **Wipe integration** | 5 tables appended to `GROUP_D_TABLES` (child-first, §B.5); `voice_ai` added to `SCENARIOS`. | `reset_dev_db.py` |
| **QA orchestration** | Second-tenant step inserted after Group C; `voice_ai` appended to the scenario list; step prints renumbered 11→13. | `seed_qa_db.py` |
| **Verification** | `seed_scenario_voice_ai.py --mode inspect` (both tenants' counts) + `seed_second_tenant.py --mode inspect` + `pytest -m unit` + full-suite Phase 2. | — |
| **README update** | §2 script inventory (+2), §3 Group C row, §4 Group C second-tenant block + new Group D "Voice AI scenario" subsection, §5 deterministic-UUID registry (+8 entries), §6 run order, §7.6 QA runbook (13 steps), **§8.1 voice-table exclusion row removed** (replaced with a pointer to §4), §9 scenario registry (+`voice_ai`), §10 new SD-9 (Voice AI) entry — named explicitly to avoid the SD-09 collision (§G-2). | `README-seed-data.md` |

### B.3 Deterministic UUID registry additions (README §5)

All new — none reuse the reserved `…-0001`–`…-0005` range. Registered in README §5 by this batch:

| Entity | UUID / family | Notes |
|---|---|---|
| Second tenant | `00000000-0000-0000-0000-000000000006` | "Pilot Dev Tenant B" |
| Tenant-B owner | `00000000-0000-0000-0000-000000000007` | `devb@pilot.local` |
| Tenant-B technician | `00000000-0000-0000-0000-000000000008` | `techb@pilot.local` |
| Voice sessions | `00000000-0000-0000-0010-0000000000NN` (NN=01–08) | Deterministic — idempotent seed by PK existence |
| Voice messages | `00000000-0000-0000-0011-0000000000NN` (NN=01–24) | Deterministic |
| Voice feedback | `00000000-0000-0000-0012-0000000000NN` (NN=01–02) | Deterministic |
| Offline-log idempotency UUIDs | `00000000-0000-0000-0013-0000000000NN` (NN=01–02) | On the 2 deferred-pipeline rows |

`voice_command_log.id` and `voice_command_entity_link.id` are **BIGINT identity** — never insert explicit ids; capture via `RETURNING id` for downstream FK references. Deterministic UUIDs for session/message/feedback rows are a deliberate exception to the "Group D rows use `gen_random_uuid()`" default: these tables have no natural unique key, and PK-existence idempotency is the cleanest rerun-safe pattern (§G-4).

### B.4 Idempotency strategy (per table)

| Table | Idempotency mechanism |
|---|---|
| `conversation_session` | Existence check by deterministic PK (`0010` family) |
| `conversation_message` | Existence check by deterministic PK (`0011` family) |
| `voice_command_log` | Every seeded row carries a deterministic `idempotency_uuid` (`0013` family for the 2 offline rows; `0014`-family-style deterministic UUIDs for sync rows — same pattern, registered with them); existence check `WHERE tenant_id=:tid AND idempotency_uuid=:u` before insert |
| `voice_command_entity_link` | Existence check on natural key `(voice_command_log_id, entity_type, entity_id)` — log id resolved at runtime from the `idempotency_uuid` |
| `voice_feedback` | Existence check by deterministic PK (`0012` family) |
| Second tenant / users / `tenant_user` / `user_endpoint` | `INSERT … ON CONFLICT (id) DO UPDATE` mirroring `seed_test_tenant.py` (created_by omitted from CONFLICT path — immutable-trigger caveat, per the established pattern) |

**Rule 11.1 compliance:** `mode_seed` performs **no DELETEs at all** (existence-check-then-insert only) — value-scoped by construction. `mode_reset(tenant_id)` performs full-tenant DELETEs on the five scenario-owned tables, which Rule 11.1 explicitly permits for reset paths. `seed_second_tenant.py --reset` deletes only `…-0006`-owned rows + the two `…-0007`/`…-0008` user rows (FK-ordered), never tenant-1 data.

### B.5 Wipe ordering (`GROUP_D_TABLES` append, child-first)

```python
# ── Voice AI (SD-9) ─────────────────────────────────────────────────────────
"voice_feedback",              # SD-9: FK → voice_command_log (SET NULL; deleted first for a clean wipe)
"voice_command_entity_link",   # SD-9: FK → voice_command_log (RESTRICT — must precede log)
"voice_command_log",           # SD-9: FK → conversation_message
"conversation_message",        # SD-9: FK → conversation_session
"conversation_session",        # SD-9
```

All five tables have `tenant_id` — the standard `DELETE … WHERE tenant_id = :tid` loop works unmodified. Placement: appended after `nec_calculation_log` (independent of the quote/job chain).

---

## C. Execution Order

Single batch, 7 tasks, strictly ordered.

| # | Task | Deliverable | ~Time |
|---|---|---|---|
| 1 | **Pre-work + MCP re-verification** — regression baseline; re-run §A MCP queries; confirm anchor entities for runtime lookups (JOB-900001, dispatch in-progress job, QUO-900006 chain, latest time entry/expense) | Baseline noted | 15m |
| 2 | **`seed_second_tenant.py`** — Group C script (§F.1): tenant `…-0006` + users `…-0007`/`…-0008` + `tenant_user` + email `user_endpoint`; `--mode seed/inspect/show`, `--reset`, `--env` (group "C" gating) | New script + inspect evidence | 1h |
| 3 | **`seed_scenario_voice_ai.py`** — Group D script (§F.2–F.6): sessions → messages → command logs → entity links → feedback, both tenants; `--mode seed/inspect/show`, `--reset`, `--env` (group "D" gating); `mode_seed(tenant_id)` / `mode_reset(tenant_id)` module contract | New script + inspect evidence | 1.75h |
| 4 | **`reset_dev_db.py` integration** — `SCENARIOS["voice_ai"]` + 5-table `GROUP_D_TABLES` append (§B.5); verify `--scenarios voice_ai` wipe+reseed cycle and full `--wipe-only` cycle | Patched script | 30m |
| 5 | **`seed_qa_db.py` integration** — second-tenant step after Group C; `voice_ai` appended to scenario list; step prints renumbered to 13 | Patched script | 15m |
| 6 | **Tests** — `tests/domains/platform_infrastructure/test_seed_scenario_voice_ai.py` (§F.7): ~12 tests (DB-touching seed/idempotency/reset + unit-level constant/contract guards) | Test file, green | 1h |
| 7 | **README-seed-data.md reconciliation** — all §B.2 README line items; live dev run: `seed_second_tenant.py` → `seed_scenario_voice_ai.py` → `--mode inspect` evidence for the completion summary | README + inspect output | 30m |

---

## D. New API Endpoints

**None.** This batch is seed tooling only — no endpoint, schema, or OpenAPI changes. `pnpm sync-api-types` is **not** required at close (no OpenAPI delta); state this explicitly in the completion summary.

---

## E. Pattern Reuse Decisions

| Pattern (source) | Application |
|---|---|
| **Idempotency (ADR-0006)** | Every insert is rerun-safe per §B.4; `idempotency_uuid` on every seeded `voice_command_log` row mirrors the runtime deferred-upload contract (arch §6.7) |
| **Env-profile gating (DB-MGMT-1 / `_env_profiles.py`)** | `seed_second_tenant.py` asserts group **"C"**; `seed_scenario_voice_ai.py` asserts group **"D"** — both prod-refused automatically; standard banner + target guards on every run |
| **Canonical scenario-script contract (`seed_scenario_mobile_sync.py` et al.)** | `mode_seed(tenant_id)` / `mode_reset(tenant_id)` module functions + CLI (`--mode`, `--reset`, `--env`) so `reset_dev_db.py` import-dispatch works |
| **DELETE safety rule (Rule 11.1 / README §7)** | `mode_seed` performs zero DELETEs; resets are full-tenant wipes of scenario-owned tables only (permitted); `seed_second_tenant.py --reset` is FK-ordered and `…-0006`-scoped |
| **Runtime lookup by business key (DB-MGMT-1 Task-4 fix precedent)** | Entity-link targets, charter tier, `tenant_user_status` are looked up by code/number at seed time — **no hardcoded row UUIDs** for runtime-created data |
| **Audit-mixin awareness (Rule §3)** | Raw-SQL inserts explicitly supply `created_at`/`updated_at` (+ `created_by`/`updated_by` where the column exists); note `voice_command_log` has **no** `created_by` and `conversation_message` is append-only (`created_at` + `created_by` only) |
| **§16 UX patterns** | Not applicable — no runtime/UI code in this batch |

---

## F. Shared Module Interfaces & Seed Content Manifest

### F.1 `seed_second_tenant.py` (new, Group C)

**Purpose**: create the second tenant with two users so tenant isolation is visually/verifiably testable (§G-3 for the deliberate minimal scope).

**Module contract:**

```python
SECOND_TENANT_ID  = UUID("00000000-0000-0000-0000-000000000006")
TENANT_B_OWNER_ID = UUID("00000000-0000-0000-0000-000000000007")
TENANT_B_TECH_ID  = UUID("00000000-0000-0000-0000-000000000008")

def mode_seed(tenant_id: UUID = SECOND_TENANT_ID) -> None   # default = second tenant
def mode_reset(tenant_id: UUID = SECOND_TENANT_ID) -> None  # FK-ordered wipe of tenant-B only
def mode_inspect() -> None
```

**Rows (tenant …-0006):**

| Table | Content |
|---|---|
| `tenant` | id=`…-0006`, name="Pilot Dev Tenant B", is_active=true, `current_subscription_tier_id` = runtime lookup `WHERE tier_name='charter'`, created_by=`…-0007`. Upsert mirrors `seed_test_tenant.py` (CONFLICT path omits created_by). No `stripe_customer_id` (NULL). |
| `user` ×2 | `…-0007` `devb@pilot.local` "Dev"/"Owner B", color `#EF4444`; `…-0008` `techb@pilot.local` "Dev"/"Technician B", color `#06B6D4`. `email_verified_at = created_at` (SD-7 B1 pre-verified precedent). Same INSERT column list as `seed_test_tenant.py` |
| `tenant_user` ×2 | owner: role_code='owner', skill='master', emp 'EMP-B01'; tech: role_code='technician', skill='journeyman', emp 'EMP-B02'. `status_id` = `tenant_user_status` lookup `code='active' AND tenant_id IS NULL`; `joined_at = created_at` |
| `user_endpoint` ×2 | email channel only per user (`is_primary=true`, `verification_status='verified'`, `consent_status='opted_in'`) — mirrors the tenant-1 email endpoint shape |

### F.2 `seed_scenario_voice_ai.py` (new, Group D) — session manifest

Rolling anchor: `NOW()` at run time with fixed negative offsets (§G-5). Sessions are **user-scoped** — owner and tech get independent histories; multiple same-day sessions exercise the derived per-day `session_number`.

| Key | User | created_at offset | status | title (auto?) | context_window_json |
|---|---|---|---|---|---|
| S1 | owner `…-0002` | today 09:14 | active | "Johnson panel quote" (true) | `active_quote_id`→quote QUO-900003 (runtime lookup), `active_customer_id`→Mary Johnson, `last_action`="add_quote_line", `pending_confirmation`=null, `safety_loto_verified`=false |
| S2 | owner | today 11:02 | active | "Davis 200A panel" (**false** — user-renamed) | `active_job_id`→dispatch job 2, `last_action`="query_job_profit" |
| S3 | tech `…-0003` | today 07:45 | ended | "Field ops — Smith residence" (true) | `active_job_id`→dispatch job 2, `safety_loto_verified`=true |
| S4 | tech | yesterday 15:20 | ended | "Time + expense logging" (true) | `active_job_id`→JOB-900001 |
| S5 | owner | −2 days | archived (`archived_at` set = updated_at) | "Metro office rough-in" (true) | `{}` |
| S6 | tech | −3 days | abandoned | **NULL** → `context_summary`="Service call scheduling" (exercises title fallback) | `{}` |
| SB1 | tenant-B owner `…-0007` | today 08:30 | active | "Apex storefront service call" (true) | `{}` |
| SB2 | tenant-B tech `…-0008` | yesterday 16:10 | ended | "Voltage drop questions" (true) | `{}` |

All sessions: `is_active=true`, `expires_at=NULL`, `created_by`/`updated_by` = owning user, `updated_at` ≈ last message time, `context_embedding` = NULL (§G-6).

### F.3 Message manifest (~24 rows)

Alternating `user`/`assistant` turns per session (4–6 for S1/S3; 2–4 others), chronological `created_at` within the session day, `created_by` = session user on user-turns and NULL on assistant/system turns, `embedding`=NULL, `audio_object_key`=NULL (§G-7). Utterances drawn from arch §6.2 example phrases; assistant replies mirror §6.1/§6.3 response shapes. Exactly **one** `role='system'` row (S1 session-init context note) to exercise the third CHECK value.

Two rows carry `structured_content_json` (rendered by `VoiceMessageBubble` as the structured-data card):

1. **S1 assistant (snapshot)** — `{"render_mode":"snapshot","content_type":"quote_draft","data":{"quote_number":"QUO-900003","customer_name":"Mary Johnson","total_cents":<runtime quote total>,"line_count":<runtime count>},"captured_at":<msg time>}`
2. **S3 assistant (live)** — `{"render_mode":"live","content_type":"job_etc_status","data":{"job_id":<dispatch job 2 id>},"captured_at":<msg time>}`

### F.4 `voice_command_log` manifest (~16 rows)

One log per voice-initiated user turn (not every message). Each row: `message_id` = its user-turn message; deterministic `idempotency_uuid`; `created_at` ≈ message time. Synchronous rows: `processing_status`=NULL, offline columns NULL. Latency triplets `(whisper, ollama, total)` within arch §6.1 ranges (300–800 / 150–400 ms), **two rows with all-NULL latencies** (report null-exclusion path). `is_successful` mix: 14 true / 2 false.

| Key | Session | intent_detected | entities_extracted | action_executed | Notes |
|---|---|---|---|---|---|
| V1 | S1 | create_quote | `{"customer_name":"Mary Johnson"}` | create_quote_via_voice | — |
| V2 | S1 | add_quote_line | `{"item_description":"200A service panel","qty":1}` | add_line_via_voice | feedback F1 links here |
| V3 | S2 | query_job_profit | `{"job_reference":"Davis"}` | get_job_profitability | — |
| V4 | S3 | clock_in | `{"job_reference":"Smith residence"}` | clock_in_via_voice | — |
| V5 | S3 | log_time_entry | `{"hours":3,"job_reference":"Smith residence"}` | log_time_entry_via_voice | — |
| V6 | S3 | add_expense | `{"amount":45.99,"vendor":"Home Depot","description":"breakers"}` | add_expense_via_voice | — |
| V7 | S4 | update_job_status | `{"job_reference":"Davis","status":"completed"}` | update_job_status_via_voice | **NULL latencies** |
| V8 | S4 | navigate | `{"target":"active jobs"}` | return_navigation_command | — |
| V9 | S5 | schedule_job | `{"job_reference":"Metro rough-in","when":"Thursday 10am"}` | schedule_job_via_voice | — |
| V10 | S6 | check_next_job | `{}` | check_next_job_via_voice | **NULL latencies** |
| V11 | S2 | NULL (parse failure) | NULL | NULL | is_successful=**false**; feedback F2 links here |
| V12 | S4 | log_time_entry | `{"hours":1.5,"job_reference":"Johnson panel"}` | log_time_entry_via_voice | **deferred**: processing_status='completed', captured→uploaded→transcribed→parsed chain (~3h gap), idempotency_uuid `…0013…01` |
| V13 | S6 | NULL | NULL | NULL | **deferred, failed**: processing_status='failed', is_successful=false, captured/uploaded set, transcribed/parsed NULL, idempotency_uuid `…0013…02` |
| VB1 | SB1 | create_customer | `{"customer_name":"Apex Storefront LLC"}` | create_customer_via_voice | tenant-B |
| VB2 | SB1 | tell_customer_arrived | `{"customer_reference":"Apex"}` | tell_customer_arrived_via_voice | tenant-B |
| VB3 | SB2 | calculate_voltage_drop | `{"length_ft":200,"awg":"10"}` | calculate_nec_voltage_drop | tenant-B, **NULL latencies** |

### F.5 `voice_command_entity_link` (6 rows, tenant-1 only) + `voice_feedback` (2 rows)

Entity links (runtime lookups by business key — job_number/title, quote_number; **same-tenant guard**, §G-8):

| Log | entity_type | entity target (runtime lookup) | action |
|---|---|---|---|
| V4 | job | dispatch in-progress job 2 | clock_in |
| V5 | job_time_entry | latest time entry on that job | logged |
| V6 | job_expense | latest expense on that job | created |
| V7 | job | JOB-900001 | status_changed |
| V9 | job | Metro Properties job (reporting/dispatch lookup) | rescheduled |
| V1 | quote | QUO-900003 | created |

Tenant-B gets **no** entity links (no tenant-B entities exist; `entity_id` is a bare UUID with no FK — linking cross-tenant would fabricate an audit lie).

Feedback (tenant-1, `created_by` = owner):

| Key | Links to | original_transcription | corrected_text | intent_misparsed | corrected_intent | feedback_notes |
|---|---|---|---|---|---|---|
| F1 | V2 | "Add ten feet of twelve gauge wire" | "Add 10 feet of 12-gauge wire" | false | NULL | "Transcription normalization only" |
| F2 | V11 | "Add the wire nuts to Tom's quote" | NULL | true | "add_quote_line" | "Llama returned no intent — capture as retrain sample" |

Both: `s3_export_key`=NULL, `exported_at`=NULL (unexported — surfaces in the `exported=false` filter).

### F.6 Script contract

**Injectable inner functions (mandatory — test-isolation seam, `test_seed_platform_env.py` precedent):** all DB work lives in inner functions that accept an open connection; the public modes are thin wrappers that open `get_db_session()`, call the inner function, and commit. Tests call the inner functions against the rollback-wrapped `db_session` fixture — the shared dev DB is never mutated by the suite (§F.7).

```python
def _seed_voice_ai(db, tenant_id: UUID) -> dict[str, int]:
    """All inserts for the passed tenant AND tenant-B (B-side skipped with a
    printed notice if seed_second_tenant has not run). Returns per-table counts."""

def _reset_voice_ai(db, tenant_id: UUID) -> dict[str, int]:
    """Wipe the 5 voice tables for the passed tenant AND tenant-B (§G-9)."""

def mode_seed(tenant_id: UUID) -> None    # opens get_db_session(), calls _seed_voice_ai, commits
def mode_reset(tenant_id: UUID) -> None   # opens get_db_session(), calls _reset_voice_ai, commits
```

`seed_second_tenant.py` follows the same shape (`_seed_tenant_b(db)` / `_reset_tenant_b(db)` inner functions).

CLI: `--mode seed|inspect|show`, `--reset`, standard `--env` wiring with `assert_group_allowed(profile, "D", "seed_scenario_voice_ai.py")`. Inspect prints per-tenant counts for all 5 tables.

### F.7 Test manifest (`tests/domains/platform_infrastructure/test_seed_scenario_voice_ai.py`)

**Isolation model (mandatory):** DB-touching tests call the injectable inner functions (`_seed_voice_ai(db_session, …)`, `_reset_voice_ai(db_session, …)`, `_seed_tenant_b(db_session)`) against the `db_session` fixture — the transaction **rolls back after every test**, so the shared dev DB (including Tom's manually seeded rows from the Task 7 live run) is never mutated. This is the `test_seed_platform_env.py` precedent and satisfies the Test Resilience Rule: within the transaction the test inserted (or found-and-skipped) only its own deterministic-ID rows; rollback reverts any in-transaction deletes. **Never** call `mode_seed`/`mode_reset` (which open their own engine and commit) from a test.

**Assertion scoping:** assertions target the deterministic `0010`–`0014` UUID families and business keys (`tier_name='charter'`, `devb@pilot.local`) — never unscoped table counts. Presence checks tolerate the real seed already existing (existence-check idempotency means the test's inner seed is a no-op over committed rows; assertions on the deterministic IDs still hold).

| # | Test | Type |
|---|---|---|
| 1 | `_seed_voice_ai` creates the full manifest — all 8 deterministic session ids present; message/log/link/feedback rows resolvable by their deterministic ids/UUIDs | DB (`db_session`) |
| 2 | Inner seed re-run is idempotent — second call inserts 0 new rows (returned counts all zero / per-id existence unchanged) | DB |
| 3 | All `role`/`status`/`processing_status` values within the MCP-verified CHECK sets | DB |
| 4 | Every `voice_command_log.message_id` resolves to a same-tenant seeded message | DB |
| 5 | Every entity link's `(entity_type, entity_id)` target exists in the same tenant (job/quote/time entry/expense runtime lookups) | DB |
| 6 | `_reset_voice_ai` removes the deterministic-id rows for **both** tenants (assert absent in-transaction; rollback restores) | DB |
| 7 | `_seed_tenant_b` creates tenant `…-0006` with charter tier FK + 2 `tenant_user` rows (`role_code` owner/technician) | DB |
| 8 | `_seed_tenant_b` re-run is idempotent (upsert — no dupes, no error) | DB |
| 9 | Deterministic UUID families are pairwise-distinct and outside the reserved `…-0001`–`…-0005` range | unit |
| 10 | Every seeded log row carries a non-NULL `idempotency_uuid`; the 2 deferred rows carry the full captured→uploaded→transcribed→parsed chain (failed row: transcribed/parsed NULL) | DB |
| 11 | Feedback rows reference existing log ids; `exported_at IS NULL` | DB |
| 12 | Structured-content messages' `structured_content_json` parses with `render_mode` in {live, snapshot} and non-empty `data` | DB |

---

## G. Open Questions Resolved

1. **Include `voice_feedback`?** The launch-plan card names 4 tables; README §8.1 lists 5. **Resolved: include it** (2 rows) — trivial cost, completes the feedback-review API surface (`GET /voice/feedback`), and removes the whole §8.1 exclusion row cleanly. Tom may veto at approval without affecting the rest.
2. **Naming collision — "SD-9".** README §10 already has a completed "Task SD-09 — Seed Data for Empty Functional Tables" (2026-07-06). **Resolved:** this batch is recorded as "**SD-9 (Voice AI)**" in README §10 and the launch plan to keep the two distinct.
3. **Second-tenant scope.** **Resolved: deliberately minimal** — tenant + 2 users + `tenant_user` + email endpoints only. No subscription row, labor rates, or Group D business entities: the goal is *isolation validation* (tenant-1 UI shows only tenant-1 voice data while the DB holds tenant-B rows; inspect mode proves both). **Cognito logins for tenant-B users are out of scope** — DB rows only; pool users would be a separate Tom/DevOps task if login-as-tenant-B testing is ever wanted (noted in handoff).
4. **Deterministic UUIDs for session/message/feedback rows vs the `gen_random_uuid()` Group D default.** **Resolved: deterministic families (`0010`–`0014` ranges).** These tables have no natural unique key; PK-existence idempotency is exact and rerun-safe. Registered in README §5 (§B.3). Entity-link/log ids stay identity-generated.
5. **Rolling timestamps vs fixed ANCHOR.** **Resolved: rolling `NOW()` offsets** (SD-7 B1 `last_login_at` precedent). Voice surfaces are recency-oriented ("today's sessions", report date filters); fixed 2026-07-01 anchors would age into invisibility. Reset+reseed refreshes.
6. **Embedding columns (`context_embedding`, `embedding`).** **Resolved: NULL everywhere.** Embeddings are runtime-pipeline output (Ollama 1024-dim); fabricating vectors would poison future similarity-search testing. HNSW indexes tolerate NULLs.
7. **`audio_object_key` on messages/logs.** **Resolved: NULL everywhere** — same rationale as the §8.2 photo hold: never fabricate S3 keys (breaks any future signed-URL path). Deferred rows are distinguishable via non-NULL `processing_status` + timestamp chain.
8. **`voice_command_entity_link.entity_id` is a bare UUID (no FK).** **Resolved: same-tenant guard** — links are resolved from tenant-1 business keys at seed time and asserted by test #5; tenant-B gets none.
9. **`mode_reset(tenant_id)` wipes both tenants.** **Resolved: documented deviation** — `reset_dev_db.py` only ever passes the primary tenant; without the tenant-B wipe, B-side rows would orphan across full resets. The function docstring + README §4 state this explicitly.
10. **E2E coverage.** **Resolved: none in this batch** — W-06 remains a Phase-7 GPU-dependent E2E item (P3). The scenario is dev/QA-only; `--env e2e` is permitted by gating but no cp spec is added.
11. **Prod safety.** **Resolved: structurally impossible to run in prod** — Group C/D gating refuses prod (DB-MGMT-1 §B.4); second tenant and scenario data can never reach prod by script.
