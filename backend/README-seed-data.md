# Seed Data — Status, Reference & Usage Guide

**Location**: `backend/` (covers `migrations/scripts/` seed system + `tests/e2e/` harness)
**Last updated**: 2026-08-18
**Status**: Phase 0.9 ✅ Complete — SD-01 through SD-10 + E2E-B1 + SD-4 + SD-5 + SD-6 + SD-7 Batches 1–3 + SD-8 delivered. Full field gap analysis completed 2026-07-23. SD-7 and SD-8 complete. **DB-MGMT-1** (env-aware seeds + schema-restore provisioning) delivered 2026-08-18 — ADR-0016.

---

## Table of Contents

- [Seed Data — Status, Reference \& Usage Guide](#seed-data--status-reference--usage-guide)
  - [Table of Contents](#table-of-contents)
  - [1. Overview — Two Directories, One Seed Layer](#1-overview--two-directories-one-seed-layer)
  - [2. Script Inventory](#2-script-inventory)
    - [migrations/scripts/ — Authoritative Seed Scripts](#migrationsscripts--authoritative-seed-scripts)
    - [tests/e2e/ — E2E Harness (SD-10 Tier 1)](#testse2e--e2e-harness-sd-10-tier-1)
  - [3. Data Group Model (A–D)](#3-data-group-model-ad)
  - [4. Current Seed State — What Is in the DB](#4-current-seed-state--what-is-in-the-db)
    - [Group A — Lookup tables (seed-script-owned; migrations are DDL-only — ADR-0016)](#group-a--lookup-tables-seed-script-owned-migrations-are-ddl-only--adr-0016)
    - [Group B — Platform config (`seed_platform.py`)](#group-b--platform-config-seed_platformpy)
    - [Group C — Test tenant (`seed_test_tenant.py`)](#group-c--test-tenant-seed_test_tenantpy)
    - [Group D — Scenario data (ephemeral)](#group-d--scenario-data-ephemeral)
  - [5. Deterministic UUIDs (Permanent — Never Reuse)](#5-deterministic-uuids-permanent--never-reuse)
  - [6. Run Order \& Quick Commands](#6-run-order--quick-commands)
    - [Target an environment (`--env` / `SEED_ENV`)](#target-an-environment---env--seed_env)
    - [Fresh dev environment setup](#fresh-dev-environment-setup)
    - [E2E database setup (isolated pilot\_e2e\_db)](#e2e-database-setup-isolated-pilot_e2e_db)
    - [QA database provisioning (`pilot_qa`)](#qa-database-provisioning-pilot_qa)
    - [Production converge (Tom only)](#production-converge-tom-only)
    - [Starter pricebook for a new tenant (concierge)](#starter-pricebook-for-a-new-tenant-concierge)
    - [Daily reset (wipe scenario data and reseed)](#daily-reset-wipe-scenario-data-and-reseed)
    - [Inspect current state](#inspect-current-state)
    - [Schema-only restore recovery](#schema-only-restore-recovery)
    - [Wipe Group C (full test tenant reset)](#wipe-group-c-full-test-tenant-reset)
  - [7. Known Constraints \& Gotchas](#7-known-constraints--gotchas)
    - [Seed scripts only manage their own inserted data](#seed-scripts-only-manage-their-own-inserted-data)
    - [pricebook\_item UUIDs are non-deterministic — never hardcode them](#pricebook_item-uuids-are-non-deterministic--never-hardcode-them)
    - [Customer phone numbers in the comms scenario share one test number](#customer-phone-numbers-in-the-comms-scenario-share-one-test-number)
    - [`reset_dev_db.py` and `seed_test_tenant.py --reset` use SAVEPOINT-per-table](#reset_dev_dbpy-and-seed_test_tenantpy---reset-use-savepoint-per-table)
    - [DELETE safety rule — `mode_seed` must never delete unrelated rows](#delete-safety-rule--mode_seed-must-never-delete-unrelated-rows)
    - [Run order is mandatory](#run-order-is-mandatory)
    - [Reserved UUIDs (`...0001` through `...0005`)](#reserved-uuids-0001-through-0005)
    - [GiST exclusion constraint (open-ended date ranges)](#gist-exclusion-constraint-open-ended-date-ranges)
    - [Shared DB with the test suite](#shared-db-with-the-test-suite)
    - [`subscription_status` fixture in `conftest.py`](#subscription_status-fixture-in-conftestpy)
    - [`user_endpoint` trigger guards](#user_endpoint-trigger-guards)
    - [`StandardAuditMixin` tables need explicit `created_at`/`updated_at`](#standardauditmixin-tables-need-explicit-created_atupdated_at)
    - ["Empty tenant" tests must use `second_tenant`](#empty-tenant-tests-must-use-second_tenant)
    - [`qco_line_type` and `jwk_status` UUIDs are non-deterministic — look up by code](#qco_line_type-and-jwk_status-uuids-are-non-deterministic--look-up-by-code)
  - [7.5 Environment-Value Matrix (DB-MGMT-1 / ADR-0016)](#75-environment-value-matrix-db-mgmt-1--adr-0016)
    - [Seeded values per environment](#seeded-values-per-environment)
    - [Vendor integration posture per environment](#vendor-integration-posture-per-environment)
    - [Seed-group × environment gating matrix](#seed-group--environment-gating-matrix)
  - [7.6 Per-Environment Provisioning Runbook (DB-MGMT-1 / ADR-0016)](#76-per-environment-provisioning-runbook-db-mgmt-1--adr-0016)
    - [QA scratch-DB proof (verified 2026-08-18)](#qa-scratch-db-proof-verified-2026-08-18)
  - [7.7 Migration-Sync Runbook (DB-MGMT-1 / ADR-0016)](#77-migration-sync-runbook-db-mgmt-1--adr-0016)
  - [8. What Is NOT Seeded by These Scripts](#8-what-is-not-seeded-by-these-scripts)
    - [8.1 — Permanently excluded (external API / pipeline dependency)](#81--permanently-excluded-external-api--pipeline-dependency)
    - [8.2 — On Hold (seed-ready but deferred by formal decision — 2026-07-23)](#82--on-hold-seed-ready-but-deferred-by-formal-decision--2026-07-23)
    - [8.3 — Short-Link Domain (not yet registered)](#83--short-link-domain-not-yet-registered)
  - [9. Scenario Status Registry](#9-scenario-status-registry)
  - [10. Roadmap — Data Tasks](#10-roadmap--data-tasks)
    - [SD-9 (Voice AI) — Voice AI seed data + second tenant ✅ Complete (2026-08-19)](#sd-9-voice-ai--voice-ai-seed-data--second-tenant--complete-2026-08-19)
    - [SD-7 — Full Field Completeness Sprint ✅ Complete (2026-07-23) — Batches 1–3](#sd-7--full-field-completeness-sprint--complete-2026-07-23--batches-13)
    - [SD-8 — Supplier Catalog Expansion + Template Test-Fire QA Tool ✅ Complete (2026-07-23)](#sd-8--supplier-catalog-expansion--template-test-fire-qa-tool--complete-2026-07-23)
    - [SD-6 — Deep Seed Data: Line Items, New Scenarios \& README Updates ✅ Complete (2026-07-15)](#sd-6--deep-seed-data-line-items-new-scenarios--readme-updates--complete-2026-07-15)
    - [SD-5 — Group D Scenario Data Expansion ✅ Complete (2026-07-15)](#sd-5--group-d-scenario-data-expansion--complete-2026-07-15)
    - [SD-4 — Group C Test Tenant Seed Audit \& Expansion ✅ Complete (2026-07-14)](#sd-4--group-c-test-tenant-seed-audit--expansion--complete-2026-07-14)
    - [Task SD-01 — Add All Missing Lookup Tables to `seed_core.py` ✅ Complete (2026-07-06)](#task-sd-01--add-all-missing-lookup-tables-to-seed_corepy--complete-2026-07-06)
    - [Task SD-02 — Write `seed_scenario_customer_comms.py` ✅ Complete (2026-07-06)](#task-sd-02--write-seed_scenario_customer_commspy--complete-2026-07-06)
    - [Task SD-03 — Write `seed_scenario_reporting.py` ✅ Complete (2026-07-06)](#task-sd-03--write-seed_scenario_reportingpy--complete-2026-07-06)
    - [Task SD-04 — Update Table of Contents in `README-seed-data.md` ✅ Complete (2026-07-06)](#task-sd-04--update-table-of-contents-in-readme-seed-datamd--complete-2026-07-06)
    - [Task SD-05 — Design: Payment Refund Status Support ✅ Complete (2026-07-06)](#task-sd-05--design-payment-refund-status-support--complete-2026-07-06)
    - [Task SD-06 — Design: Invoice Status Alignment + Automated Late Invoice Reminders ✅ Complete (2026-07-06)](#task-sd-06--design-invoice-status-alignment--automated-late-invoice-reminders--complete-2026-07-06)
    - [Task SD-07 — Design: Product Feature / Usage Billing Competitive Review ✅ Complete (2026-07-06)](#task-sd-07--design-product-feature--usage-billing-competitive-review--complete-2026-07-06)
    - [Task SD-08 — Design: Email Template + Notification Template Review \& Update ✅ Complete (2026-07-06)](#task-sd-08--design-email-template--notification-template-review--update--complete-2026-07-06)
    - [Task SD-09 — Design: Seed Data for Empty Functional Tables ✅ Complete (2026-07-06)](#task-sd-09--design-seed-data-for-empty-functional-tables--complete-2026-07-06)
    - [Task SD-10 — Design: Scenario Coverage Analysis + Automated E2E Test Harness ✅ Complete (2026-07-06, extended E2E-B1 2026-07-12)](#task-sd-10--design-scenario-coverage-analysis--automated-e2e-test-harness--complete-2026-07-06-extended-e2e-b1-2026-07-12)
  - [11. Reference Documents](#11-reference-documents)

---

## 1. Overview — Two Directories, One Seed Layer

The seed system spans two directories that work together — all seed **data** lives in `migrations/scripts/`; the E2E harness in `tests/e2e/` re-routes those same scripts to an isolated database.

```
backend/
├── migrations/scripts/     ← Authoritative seed data (Groups A–D), targets pilot_dev (port 5432)
│   ├── _env_profiles.py    ← Env registry (DB-MGMT-1): --env/SEED_ENV resolution, host guards, group gating, banner
│   ├── seed_core.py        ← Group A: 34+ lookup tables
│   ├── seed_platform.py    ← Group B: plans, features, statuses (env-aware Stripe price IDs)
│   ├── seed_test_tenant.py ← Group C: test tenant + users + pricing
│   ├── seed_scenario_*.py  ← Group D: 9 ephemeral scenario scripts (8 universal + notifications dev-only)
│   ├── reset_dev_db.py     ← Group D: wipe/reseed control panel
│   ├── provision_schema.py ← Schema-restore provisioning (DB-MGMT-1): pg_dump from dev → apply → UUID patch → alembic stamp
│   ├── seed_qa_db.py       ← QA orchestrator (DB-MGMT-1): Groups A→B→C→D, all 8 universal scenarios
│   ├── seed_prod_db.py     ← Prod converge orchestrator (DB-MGMT-1): Groups A+B only, typed confirmation, Stripe preflight
│   ├── seed_pricebook_starter.py ← Per-tenant starter pricebook (DB-MGMT-1, concierge, --tenant-id)
│   └── data/email_templates/*.json  ← email_template body files
└── tests/e2e/              ← SD-10 Tier 1 harness, targets pilot_e2e_db (port 5434)
    ├── init_e2e_schema.py  ← Step 1: thin back-compat wrapper over provision_schema.py --env e2e
    ├── seed_e2e_db.py      ← Step 2: calls migrations/scripts/* against port 5434
    ├── conftest_e2e.py     ← Session-scoped fixtures for E2E tests
    └── cp{1-9}_*/          ← 9 critical path test modules
```

These scripts populate the dev, e2e, and QA PostgreSQL databases with reference data, platform configuration, a test tenant, and scenario data for UI smoke testing — and they are also the **only** channel by which data reaches production. Per **ADR-0016 (DB-MGMT-1, 2026-08-18)**, Alembic migrations are **DDL-only**: all data (lookup rows, platform config, templates) is owned by seed scripts, and one-off deployment SQL is retired. Production is **converged in place — never wiped** — via `seed_prod_db.py` (Groups A+B, typed confirmation, Stripe key preflight), which Tom executes after any batch that changes Group A/B data. See §7.5–§7.7 for the environment-value matrix, per-env provisioning runbook, and migration-sync runbook.

The seed system was built in two phases and fully remediated:

| Phase | What happened | Status |
|:---|:---|:---|
| Phase 0.7.1 | 3 Alembic data migrations (21 lookup tables, system user, comm templates) | ✅ Complete |
| Phase 0.7.2 | 6 seed scripts written (Groups A–D) | ✅ Complete |
| Phase 0.8 | Post-delivery remediation: subscription_status, trial tier mapping, show/inspect gaps fixed | ✅ Complete (2026-06-15) |
| SD sprint | SD-01 through SD-10: 14 missing lookup tables, 5 new scenarios, E2E harness scaffold | ✅ Complete (2026-07-06) |
| E2E-B1 | NEC + mobile sync scenarios + cp6–cp9 critical path tests | ✅ Complete (2026-07-12) |

---

## 2. Script Inventory

### migrations/scripts/ — Authoritative Seed Scripts

| Script | Group | Purpose | Has `--reset`? |
|:---|:---:|:---|:---:|
| [`migrations/scripts/_env_profiles.py`](migrations/scripts/_env_profiles.py) | Shared | Env-awareness registry (DB-MGMT-1) — `SeedEnv`, `EnvProfile`, `resolve_seed_env()`, `assert_target_compatible()`, `print_seed_banner()` | — |
| [`migrations/scripts/_db_utils.py`](migrations/scripts/_db_utils.py) | Shared | SQLModel Session context manager — imported by all other scripts | — |
| [`migrations/scripts/seed_core.py`](migrations/scripts/seed_core.py) | A | Re-inserts 34+ Alembic-managed lookup tables (idempotent recovery after schema-only restore) | No |
| [`migrations/scripts/seed_platform.py`](migrations/scripts/seed_platform.py) | B | 3 product plans + feature limits + 6 subscription statuses + notification templates | No |
| [`migrations/scripts/seed_test_tenant.py`](migrations/scripts/seed_test_tenant.py) | C | Test tenant + **4 users** + pricing engine (labor rates + markup + burden_pct) + subscription + 2 discount versions + in_app/push endpoints | Yes (3-sec countdown) |
| [`migrations/scripts/seed_second_tenant.py`](migrations/scripts/seed_second_tenant.py) | C | Second tenant (`…-0006`) + 2 users (`…-0007`/`…-0008`) + tenant_user + email endpoints — **SD-9**: tenant isolation validation | Yes (FK-ordered tenant-B-only wipe) |
| [`migrations/scripts/seed_scenario_quote_to_cash.py`](migrations/scripts/seed_scenario_quote_to_cash.py) | D | 5 customers + 3 sites + 5 pricebook items + 1 draft quote | Yes |
| [`migrations/scripts/seed_scenario_dispatch.py`](migrations/scripts/seed_scenario_dispatch.py) | D | 5 jobs + 3 tech assignments + 1 PTO availability block | Yes |
| [`migrations/scripts/seed_scenario_customer_comms.py`](migrations/scripts/seed_scenario_customer_comms.py) | D | 3 customers with E.164 phone numbers + SMS threads + messages (2 unread) + entity_contact | Yes |
| [`migrations/scripts/seed_scenario_reporting.py`](migrations/scripts/seed_scenario_reporting.py) | D | 4 completed jobs (past dates) + time entries + expenses + tech assignments | Yes |
| [`migrations/scripts/seed_scenario_supplier_catalog.py`](migrations/scripts/seed_scenario_supplier_catalog.py) | D | 3 suppliers (Wesco 25 items, Graybar 21 items, Platt 21 items) + prices + pricing_cache (Wesco) — **SD-8**: JSON-driven loader | Yes |
| [`migrations/scripts/seed_scenario_nec.py`](migrations/scripts/seed_scenario_nec.py) | D | 2 nec_calculation_log rows (online + offline voltage_drop calcs) — E2E-B1 | Yes |
| [`migrations/scripts/seed_scenario_mobile_sync.py`](migrations/scripts/seed_scenario_mobile_sync.py) | D | mobile_sync_session + mobile_sync_event rows for test tech — E2E-B1 | Yes |
| [`migrations/scripts/seed_scenario_tenant_site.py`](migrations/scripts/seed_scenario_tenant_site.py) | D | Tenant site (hosted_compliance) — C-B16 | Yes |
| [`migrations/scripts/seed_scenario_notifications.py`](migrations/scripts/seed_scenario_notifications.py) | D | 5 `in_app_notification` rows for owner user (SD-6) — **dev-only** (not in QA/E2E orchestrators) | Yes |
| [`migrations/scripts/seed_scenario_voice_ai.py`](migrations/scripts/seed_scenario_voice_ai.py) | D | 8 conversation_session + ~34 conversation_message + 16 voice_command_log + 6 voice_command_entity_link + 2 voice_feedback rows for both tenants — **SD-9**: Voice AI history surfaces | Yes |
| [`migrations/scripts/reset_dev_db.py`](migrations/scripts/reset_dev_db.py) | D control | Interactive wipe/reseed panel — wipes Group D only | Yes (`--wipe-only`) |
| [`migrations/scripts/provision_schema.py`](migrations/scripts/provision_schema.py) | Provision | Schema-restore provisioning (DB-MGMT-1) — `pg_dump` from dev → apply to target → UUID patch → alembic stamp | No |
| [`migrations/scripts/seed_qa_db.py`](migrations/scripts/seed_qa_db.py) | Orchestrator | QA DB orchestrator (DB-MGMT-1) — runs Groups A→B→C→D with all 9 scenarios + second tenant (13 steps) | No |
| [`migrations/scripts/seed_prod_db.py`](migrations/scripts/seed_prod_db.py) | Orchestrator | Prod converge orchestrator (DB-MGMT-1) — typed confirmation + Stripe preflight + Groups A+B only | No |
| [`migrations/scripts/seed_pricebook_starter.py`](migrations/scripts/seed_pricebook_starter.py) | Per-tenant | Starter pricebook catalog (DB-MGMT-1) — 13-item electrical catalog, `--tenant-id` required | No |
| [`migrations/scripts/test_fire_templates.py`](migrations/scripts/test_fire_templates.py) | QA Tool | Manual template test-fire — email channel only; `--dry-run` supported; NOT part of seed system | No |
| [`migrations/scripts/data/supplier_catalog/*.json`](migrations/scripts/data/supplier_catalog/) | — | Supplier catalog data files: wesco.json (25 items), graybar.json (21 items), platt.json (21 items, 1 inactive) | — |

All seed scripts (except `reset_dev_db.py`) support three modes:

| Mode | Flag | What it does |
|:---|:---|:---|
| `seed` | `--mode seed` (default) | Runs INSERT logic against the DB |
| `inspect` | `--mode inspect` | Queries DB and prints current rows — no changes |
| `show` | `--mode show` | Prints what the script WOULD insert — no DB connection needed |

All seed scripts additionally accept `--env {dev,e2e,qa,prod}` (or the `SEED_ENV` env var) with a startup banner, host guards, and group gating — see [§6 Target an environment](#target-an-environment---env--seed_env) and the [§7.5 gating matrix](#seed-group--environment-gating-matrix). `seed_prod_db.py` and `seed_pricebook_starter.py` also accept `--stripe-mode {test|live}` (required for `--env prod` on scripts that touch env-specific values; fail-closed).

### tests/e2e/ — E2E Harness (SD-10 Tier 1)

The E2E folder owns no seed data — it re-routes `migrations/scripts/` against the isolated `pilot_e2e_db` (port 5434).

| Script / Module | Purpose |
|:---|:---|
| [`tests/e2e/init_e2e_schema.py`](tests/e2e/init_e2e_schema.py) | Step 1: applies `pg_dump --schema-only` from `pilot_dev`, patches UUID defaults on 24 lookup tables, stamps alembic at head |
| [`tests/e2e/seed_e2e_db.py`](tests/e2e/seed_e2e_db.py) | Step 2: calls Groups A→B→C→D seed scripts against `pilot_e2e_db` |
| [`tests/e2e/conftest_e2e.py`](tests/e2e/conftest_e2e.py) | Session-scoped `e2e_engine`, `e2e_client`, Cognito mock, entitlement bypass, AI service mock |
| [`tests/e2e/cp1_auth_tenant/`](tests/e2e/cp1_auth_tenant/) | Critical path 1: Auth + RBAC |
| [`tests/e2e/cp2_quote_to_cash/`](tests/e2e/cp2_quote_to_cash/) | Critical path 2: Quote → Invoice flow |
| [`tests/e2e/cp3_dispatch_field_sync/`](tests/e2e/cp3_dispatch_field_sync/) | Critical path 3: Dispatch board |
| [`tests/e2e/cp4_customer_sms/`](tests/e2e/cp4_customer_sms/) | Critical path 4: SMS threads |
| [`tests/e2e/cp5_dunning_cycle/`](tests/e2e/cp5_dunning_cycle/) | Critical path 5: Overdue invoice reminders |
| [`tests/e2e/cp6_invoice_stripe/`](tests/e2e/cp6_invoice_stripe/) | Critical path 6: Invoice + Stripe (E2E-B1) |
| [`tests/e2e/cp7_notifications/`](tests/e2e/cp7_notifications/) | Critical path 7: Notification delivery (E2E-B1) |
| [`tests/e2e/cp8_nec/`](tests/e2e/cp8_nec/) | Critical path 8: NEC calculations online + offline (E2E-B1) |
| [`tests/e2e/cp9_mobile_sync/`](tests/e2e/cp9_mobile_sync/) | Critical path 9: Mobile offline sync (E2E-B1) |

**E2E seed coverage**: `seed_e2e_db.py` calls 5 of 9 Group D scenarios. `seed_scenario_reporting.py` and `seed_scenario_supplier_catalog.py` are dev-only — no E2E critical path covers them.

---

## 3. Data Group Model (A–D)

Groups are organized by **when you need them and why** (not by FK dependency layer). Run order within each group respects FK dependencies.

| Group | Script(s) | What it owns | Wipes on `--reset`? | Never touches |
|:---|:---|:---|:---:|:---|
| **A** | `seed_core.py` | Platform-wide lookup tables (address_type, job_status, tax_rate_version, etc.) | No | Everything |
| **B** | `seed_platform.py` | Product plan hierarchy + subscription statuses + notification templates | No | Groups A, C, D |
| **C** | `seed_test_tenant.py`, `seed_second_tenant.py` | Test tenant + 4 users + subscription + pricing engine + 2 discount versions; second tenant (`…-0006`) + 2 users (**SD-9**) | Group C + D config | Groups A, B |
| **D** | `seed_scenario_*.py`, `reset_dev_db.py` | Ephemeral scenario data (customers, jobs, quotes, SMS threads, NEC logs, sync sessions, supplier catalog) | Group D only | Groups A, B, C |

---

## 4. Current Seed State — What Is in the DB

### Group A — Lookup tables (seed-script-owned; migrations are DDL-only — ADR-0016)

Historically these rows arrived via Alembic data migrations. From **DB-MGMT-1 / ADR-0016 (2026-08-18)** forward, migrations contain **DDL only** and [`seed_core.py`](migrations/scripts/seed_core.py) is the **sole owner of lookup/reference data in every environment** — dev/e2e/qa/prod alike. It is also the **recovery tool**: after any schema-only restore or wipe, all lookup and reference data can be restored without replaying Alembic migrations. All 34+ tables covered with `INSERT ... ON CONFLICT DO NOTHING`; prod application flows through the `seed_prod_db.py` converge path (§7.6).

| Table | Rows | Data | Notes |
|:---|:---:|:---|:---|
| `address_type` | 4 | billing, service_location (default), mailing, shipping | ⚠️ Live DB uses `service_location` and `shipping` — README previously said `service` and `other` |
| `contact_type` | 4 | primary (default), billing, decision_maker, technical | ⚠️ Live DB uses `decision_maker` and `technical` — README previously said `emergency` and `other` |
| `taxability_code` | 3 | taxable, exempt, zero_rated | ⚠️ Live DB uses `zero_rated` — README previously said `reduced` |
| `currency` | 4 | USD (active); GBP, EUR, CAD (is_active=False — US-only for launch) | SD-2: deactivated non-USD currencies |
| `job_status` | 5 | draft (default), scheduled, in_progress, completed, cancelled (terminal) | — |
| `job_expense_category` | 3 | materials, equipment, permits | ⚠️ Code is `materials` (plural), not `material` |
| `quote_status` | 10 | draft (default), pending_approval, approved, sent, pending, accepted (terminal), converted (terminal), rejected (terminal), expired (terminal), void (terminal) | `accepted` = customer accepted a sent quote; `converted` = became a job |
| `invoice_status` | 6 | draft (default), issued, partial (not terminal), paid (terminal), void (terminal), writeoff (terminal) | SD-2: added `partial`. "overdue" is a derived display state (`due_at < TODAY AND status NOT IN paid/void/writeoff`) |
| `payment_status` | 5 | pending (default), succeeded (terminal), failed (terminal), canceled (terminal), refunded (terminal) | SD-2: added `refunded`. Refunds create a new negative-amount payment row — original row unchanged |
| `payment_type` | 6 | card, ach, wallet, bank_debit, manual_check, venmo | — |
| `qco_line_type` | 5 | labor (default), material, misc, discount, note | SD-2: added `note` — display-only text block, no price, no QB mapping |
| `entity_type` | 7 | customer, site, job, quote, invoice, customer_communication, tenant | ⚠️ Live DB has `customer_communication` (not `user`). `user` entity type not present. **SEED-FIX-1**: count corrected 6→7 (verified 2026-08-09). |
| `customer_lifecycle_status` | 4 | prospect (default), active, dormant, churned | Lifecycle state for customer records |
| `site_lifecycle_status` | 3 | active (default), closed, construction | Lifecycle state for site records |
| `supplier_lifecycle_status` | 2 | active (default), deprecated | Lifecycle state for supplier records |
| `tenant_user_status` | 4 | active (default), invited, pending, suspended | Status for a user's membership in a tenant |
| `notification_category` | 8 | billing, customer_activity, field_issues, job_activity, quote_approvals, background_sync_alerts, sync_conflicts, system_announcements | — |
| `notification_default_policy` | 24 | 8 categories × 3 channels: email, in_app, push | SMS is opt-in only and intentionally absent from defaults |
| `notification_channel` | 4 | email, sms, push, in_app | `voice` channel is not yet implemented |
| `platform_role` | 3 | accountant, owner, support | Pilot internal staff roles — separate from tenant RBAC (`tenant_user_role`) |
| `tenant_user_role` | 4 | owner (default), technician, accountant, office_staff | Tenant-level RBAC roles — not the same as `platform_role`. **PLP-FIX-7**: office_staff gains `jobs.view` (Schedule board loads jobs — office staff schedule jobs). Seed block now applies a value-scoped converge UPDATE on existing rows (idempotent). **PLP-FIX-9 (2026-09-05)**: office_staff now 19 perms (added `communications.view`, `communications.send` + 4 self-service Security-page codes: `mfa.enroll_self`, `account.session.view_own`, `account.session.revoke_own`, `help_chat.delete_own_history`); technician now 21 perms (+4 self-service codes); accountant now 9 perms (+4 self-service codes). `communications.manage` deliberately excluded from all non-owner roles (design §G.1 — owner-only thread lifecycle admin). Owner unchanged (`*` wildcard). **PLP-FIX-11 (2026-09-06, INV-BUG-18)**: accountant now 10 perms (+`schedule.view_all` — read-only schedule view: jobs' technician assignments + read-only dispatch board; `schedule.manage`/`schedule.view_own` NOT granted). |
| `subscription_tier` | 4 | charter (is_trial=false, $49/mo, 90-day free, active), trial (is_trial=true, 14-day, $0, dormant), starter ($59/mo, dormant), teams ($179/mo, dormant) | enterprise removed; charter is the only active tier during Charter cohort launch period. **C-B2: Charter pricing updated to $49/mo ($588 annual); 4 new lifecycle cols added (free_period_days, requires_payment_method, signup_cap, price_locked).** |
| `platform_setting_catalog` | 48 | 48 catalog keys covering all configurable settings incl. `loto_confirmation_required`, `voice_persona_tone`, `background_sync_enabled`, `square_integration_enabled`, `default_payment_terms`, `default_billing_mode` | Defines key name, value_type, category, and tenant_editable flag. **SEED-FIX-1**: 3 B20 invoice-builder keys (`square_integration_enabled`, `default_payment_terms`, `default_billing_mode`) now seed_core-owned — closes migration-embedded seed gap found in 2026-08-09 prod sync. |
| `platform_setting` (defaults) | 48 | NULL-tenant default value row for each of the 48 catalog keys | System defaults; per-tenant overrides created when a tenant changes a setting |
| `tax_rate_version` | 3 | US-DEFAULT 6%, US-TX-HARRIS 8.25%, US-CA-LA 9.5% | Sample rates for local dev/QA — tenants add actual rates in production |
| `sync_conflict_classification_matrix` | 17 | Platform-default severity rules mapping `(entity_type, conflict_type)` → `(severity_class, auto_resolution_strategy)` | — |
| `email_template` | 17 | System transactional email templates (quote approval, invoice sent, payment received, team invite, etc.) | HTML/text body loaded from [`migrations/scripts/data/email_templates/*.json`](migrations/scripts/data/email_templates/) — TEAM-INVITE-1 added `team_invite` |
| `quote_link_status` | 4 | active (default), exhausted, expired, revoked | — |
| `qpl_contact_action_type` | 4 | view (active), approve, message, request_change | Used by quote public link contact actions |
| `webhook_event_type` | 3 | invoice.paid, job.updated, quote.accepted | — |
| `sso_provider` | 2 | google, microsoft | — |
| `jwk_status` | 3 | active (default, signable), retiring (signable=false), retired (signable=false) | — |
| `supplier_item_category` | 9 | conduit_raceway, dist_equip, enclosures, fasteners, fittings, lighting, tools_equip, wire_cable, wiring_devices | — |
| `supplier_item_uom` | 8 | bag, box, each (default), foot, linear_foot, package, roll, spool | — |
| `notification_category_sub_trigger` | 7 | Per-category push notification overrides (MFA reminders, field issues, job assignment) | — |
| `notification_type` | 20 | customer_communication_sent, dunning_reminder, quote_accepted; job_assigned, schedule_changed, qb_sync_conflict, qb_conflict_pre_warning, gps_variance_alert, system_template_updated, free_period_warning; platform_sms_double_optin, platform_sms_optin_reply, platform_sms_optout_reply, platform_sms_help_reply, platform_payment_failed, platform_security_new_device, platform_maintenance_broadcast; qb_connection_expired, stripe_connect_disconnected, stripe_dispute_opened | SD-2: 6 production service codes added. **SEED-FIX-1**: count corrected 9→10 (verified 2026-08-09). **PLATFORM-SMS-B1**: 5 Pathway C platform SMS type codes added (campaign CXXXXXX, 2026-08-10). **PLATFORM-SMS-B2**: 2 more Pathway C type codes added — `platform_security_new_device` (Sample 3, new-device sign-in alert) + `platform_maintenance_broadcast` (Sample 4, scheduled maintenance broadcast), 2026-08-16. **QB-H1** (2026-08-28): `qb_connection_expired` added. **STRIPE-CONNECT-1** (2026-08-28): `stripe_connect_disconnected` + `stripe_dispute_opened` added (owner notifications for Connect disconnect + dispute events). |
| `product_feature` | 3 | schedule_lanes, outbound_sms_segments, voice_ai_minutes | MKT-B11: `dispatch_slots` renamed → `schedule_lanes`. `seed_core.py` now DELETEs `dispatch_slots` (and any other orphaned codes) on each run |
| `communication_template` | 17 | SMS/email templates for customer-facing comms (on_my_way, arrived, invoice_sent, etc.) — 17 rows across 11 template types × 2 channels (email+sms) | **SEED-FIX-1**: Now fully owned by `seed_core.py` (sms + email variants, incl. `recurring_job_scheduled`/email from B21). Closes migration-embedded seed gap found in 2026-08-09 prod sync. |
| `quote_template` | 3 | 3 Alembic-owned system templates (confirmed via migration `29384efbde55`) | — |
| `quote_template_line` | **9** | 2–4 lines per system template: Service Call Basic (3), Installation Standard (4), Fixed Bid Simple (2). Post QT-FIX-1 (2026-07-30): lines are `tenant_id = NULL` (platform-level, matching parent `quote_template.tenant_id`); no test-tenant dependency. Migration `990231f963b0` dropped NOT NULL + converted the 9 existing rows. | **SD-7 Batch 1** + **QT-FIX-1** |
| `job_type` | **11** | Platform-default rows (tenant_id=NULL): service_call, troubleshoot, panel_upgrade, rewire, lighting, generator_install, ev_charger_install, new_construction, inspection, warranty, other. Sort orders 10–999. | **CLASS-B1** — identical rows seeded by migration `44fb6fed24c3`; `seed_core.py` is the schema-restore recovery path. |

### Group B — Platform config (`seed_platform.py`)

| Table | Rows | Data | Notes |
|:---|:---:|:---|:---|
| `product_plan` | 3 | charter_plan (active), starter_plan (dormant), **teams_plan** (dormant) | enterprise_plan removed. Only `charter_plan` is `is_active=true` during Charter cohort launch. **SD-3: `teams` renamed to `teams_plan`** to match `charter_plan`/`starter_plan` convention. |
| `product_plan_version` | 3 | One version per plan (AppendOnly — no `updated_at`) | **SD-3: `charter_plan` price_cents fixed from 4900 → 0** (free during cohort period; $49/mo billing activates at month 7 via Stripe Subscription Schedule — STRIPE-B1 scope). |
| `product_plan_product_feature_version` | 9 | All 3 plans × 3 features: schedule_lanes (5/5/20), voice_ai_minutes (90/90/300), outbound_sms_segments (100/100/500) | MKT-B11: `data_exports` removed from ppfv (unlimited, untracked). `dispatch_slots` → `schedule_lanes` rename. **SD-3: ppfv rows updated from `teams` → `teams_plan` code.** |
| `subscription_tier` | 4 | charter→charter_plan, trial→starter_plan, starter→starter_plan, teams→teams_plan | SD-3: `stripe_price_id_monthly` + `stripe_price_id_annual` columns. **C-B2: 4 new lifecycle cols** (`free_period_days`, `requires_payment_method`, `signup_cap`, `price_locked`). **charter**: annual=58800¢ ($588/yr), m2m=4900¢ ($49/mo flat), free_period_days=90, requires_payment_method=false, signup_cap=12, price_locked=true, stripe_monthly=`price_REDACTED15` (test), stripe_annual=NULL. **trial**: annual=0¢, m2m=0¢, free_period_days=14, requires_payment_method=false, stripe IDs=NULL. **starter**: annual=58800¢ ($588/yr), m2m=5900¢ ($59/mo), free_period_days=NULL, requires_payment_method=true, stripe_monthly=`price_REDACTED16` (test), stripe_annual=`price_REDACTED17` (test). **teams**: annual=178800¢ ($1788/yr), m2m=17900¢ ($179/mo), free_period_days=NULL, requires_payment_method=true, stripe_monthly=`price_REDACTED19` (test), stripe_annual=`price_REDACTED18` (test). charter is only `is_active=true` tier. **DB-MGMT-1 (2026-08-18)**: all test-mode price IDs realigned to the [`stripe_ids.test.json`](scripts/stripe_ids.test.json) mapping-file family (`price_REDACTED…`), superseding the 2026-07-14 manually-created family; live IDs unchanged (the live bootstrap adopted the 2026-07-14 live objects). |
| `subscription_status` | 6 | trialing, active, past_due (billing_active=true); unpaid, canceled, paused (billing_active=false) | Map 1:1 to Stripe's `subscription.status` enum |
| `notification_template` | **67** | Platform-default templates for all 20 notification_type codes × 3 channels (email, in_app, push) + 7 Pathway C sms-channel templates | **SD-3: Added 18 new rows for 6 SD-2 notification types** (job_assigned, schedule_changed, qb_sync_conflict, qb_conflict_pre_warning, gps_variance_alert, system_template_updated) × 3 channels = 18 rows. **SEED-FIX-1**: count corrected 27→30 (10 types × 3 channels, verified 2026-08-09). **PLATFORM-SMS-B1**: 5 sms-channel rows added for Pathway C platform SMS (campaign CXXXXXX, 2026-08-10) — platform_sms_double_optin, platform_sms_optin_reply, platform_sms_optout_reply, platform_sms_help_reply, platform_payment_failed. **PLATFORM-SMS-B2**: 2 more sms-channel rows added (2026-08-16) — platform_security_new_device (Sample 3, static), platform_maintenance_broadcast (Sample 4, `{{ maint_date }}`/`{{ maint_window }}` placeholders). The 2 new types also get email/in_app/push placeholder rows via the existing loop (6 rows). **DB-MGMT-1**: count corrected 41→58 (17 types × 3 channels = 51 platform-default rows + 7 sms-channel rows = 58, MCP-verified 2026-08-18). **QB-H1** (2026-08-28): +3 rows for `qb_connection_expired` (email/in_app/push) → 61. **STRIPE-CONNECT-1** (2026-08-28): +6 rows for `stripe_connect_disconnected` + `stripe_dispute_opened` (2 types × 3 channels) → 67 (20 types × 3 channels = 60 platform-default rows + 7 sms-channel rows = 67, MCP-verified 2026-08-28). Copy is byte-identical to migration `d038d647ec41`. |

### Group C — Test tenant (`seed_test_tenant.py`)

| Table | Before SD-4 | After SD-4 / SD-6 | Notes |
|:---|:---:|:---:|:---|
| `tenant` | 1 row | 1 row | **SD-4**: `stripe_customer_id = 'cus_REDACTEDX01'` (test-mode Stripe customer). **G3 (TEST-UPLIFT-1A, 2026-08-27)**: seed tenants intentionally carry NULL `stripe_customer_id` — they never traverse the signup wizard (the path that creates the Stripe customer via `create_stripe_customer`). The dev DB shows 2/2 NULL (MCP-verified). No backfill — creating real Stripe customers for fake tenants would pollute the Stripe account. **STRIPE-CONNECT-1-B2 (2026-08-29)**: `billing_contact_phone = '(804) 555-0142'`, `billing_contact_email = 'billing@pilotdevtenant.example.com'` — contractor-entered billing contact shown on the public invoice manual-payment panel. Idempotent upsert (set on both INSERT and ON CONFLICT DO UPDATE). |
| `user` | 3 rows | **4 rows** | **SD-4**: added `accountant@pilot.local` (UUID `...0005`). Colors: owner=#10B981, tech=#3B82F6, office=#F59E0B, accountant=#8B5CF6 |
| `user_endpoint` | 3 rows (email only) | **12 rows** | **SD-4**: added `in_app` + `push` for all 4 users (4 users × 3 channels). Email = primary (`is_primary=true`); in_app/push = secondary. Requires Alembic migration `aaaa1f8d5138` (extends `user_endpoint_channel_chk` to allow `in_app` + `push`). |
| `tenant_user` | 3 rows | **4 rows** | **SD-4**: added accountant user (role=accountant) |
| `password_policy` | 1 row (min_length=8) | 1 row | **SD-4**: lockout_threshold=5, lockout_window_minutes=15, lockout_duration_minutes=30, history_depth=5 |
| `tenant_email_branding` | 1 row (no footer) | 1 row | **SD-4**: `custom_footer` = "© 2026 Pilot Dev Tenant. All rights reserved." |
| `tenant_onboarding_checklist` | 1 row | 1 row | dismissed_permanently=True — suppresses FTU banners |
| `subscription` | 1 row (seats=1, billing_anchor=NULL) | 1 row | **SD-4**: `quantity_seats=4`, `billing_anchor='2026-07-01'`. Uses `charter_plan` explicitly. |
| `labor_rate_version` | 3 rows (burden_pct=0.0) | 3 rows | **SD-4**: burden_pct updated — master=0.25 ($150/hr), journeyman=0.20 ($102/hr), apprentice=0.15 ($63.25/hr). Open-ended range `[2026-06-01, NULL)` — future scenario scripts must use past closed ranges. |
| `tenant_markup_version` | 1 row | 1 row | 20%, category=materials. Open-ended range — same GiST constraint caveat. |
| `discount_version` | 0 rows | **2 rows** | SUMMER_PROMO (10% off, closed 2024-06→2024-08); NEW_CUSTOMER ($25 off, open-ended 2026-01-01). No GiST exclusion constraint on this table. |
| `user_preference` | 0 rows | **1 row** | **SD-6**: Owner user (`dev@pilot.local`) preference: `{"theme":"light","sidebar_collapsed":false,"notification_sounds":true,"default_invoice_terms":"net_30","dashboard_layout":"default"}` |
| `user_setting_override` | 0 rows | **2 rows** | **SD-6**: `background_sync_enabled=true`, `voice_persona_tone="professional"` for owner user. Only `allows_user_override=true` keys. |
| `user.email_verified_at` / `user.last_login_at` | NULL | **Set** | **SD-7 Batch 1**: `email_verified_at = created_at` (pre-verified) for all 4 users. `last_login_at`: owner=2h ago, tech=1d ago, office=3d ago, accountant=7d ago (rolling from `NOW()`). |
| `tenant_user.skill_level_code` / `tenant_user.employee_number` | NULL | **Set** | **SD-7 Batch 1**: owner=master/EMP-001, tech=journeyman/EMP-002, office=apprentice/EMP-003, accountant=NULL/NULL (admin role). |
| `auth_jwk` | 0 rows | **1 row** | **SD-7 Batch 1**: Active RS256 signing key `pilot-dev-signing-key-v1` (synthetic public JWK — no real private key, test-only placeholder). `jwk_status_id` = active. `tenant_id = NULL`. |

### Group D — Scenario data (ephemeral)

> **SD-5 Updated 2026-07-15**: All 7 scenario scripts expanded for full UI-testable data density.
> **SD-6 Updated 2026-07-15**: Invoice lines, change orders, loto confirmations, escalations, notifications seeded.

#### Quote-to-Cash scenario (`seed_scenario_quote_to_cash.py`) — E2E: cp2

| Table | Rows | Data | Notes |
|:---|:---:|:---|:---|
| `customer` | 8 | John Smith, Mary Johnson, Apex Commercial LLC, Bob Davis (prospect), Inactive Customer (dormant), + SD-5: Rachel Kim, Metro Properties LLC, James Torres | Non-deterministic UUIDs (`gen_random_uuid()`) |
| `site` | 7 | Smith Residence (NY), Johnson Home (TX), Apex HQ (IL), Davis Property (CO), Kim Residence (WA), Metro Office Park (TX), Torres Home (FL) | SD-5 added 4 sites |
| `entity_address` / `address` | 7 | Full US address objects linked to each site | — |
| `pricebook_item` | 6 | Standard Outlet Install $150 (labor), 200A Panel Upgrade $1,800 (labor), 15A Circuit Breaker $18 (material), EMT Conduit $3.50/ft (material), Residential Permit Fee $250 (misc, tax-exempt), Wire Nuts bag $5 (material) | SD-5 added Wire Nuts |
| `pricebook_item_version` | 6 | One active version per item | — |
| `quote` | 10 | QTC-001 (draft, 8 lines), QUO-900001 (pending_approval), QUO-900002 (pending), QUO-900003 (approved), QUO-900004 (sent), QUO-900005 (accepted), QUO-900006 (converted), QUO-900007 (rejected), QUO-900008 (expired), QUO-900009 (void) | All 10 quote_status codes represented |
| `quote_line` | 30+ | Draft quote has 8 lines (all qco_line_type codes: labor, material, misc, note, discount). Each non-draft quote has 2–3 lines | — |
| `quote_version` | 10 | One v1 snapshot per quote | — |
| `job` | 1 | JOB-900001 (completed) — linked to QUO-900006 | Part of Q-CONV-001 chain |
| `invoice` | 1 | INV-900001 (paid, billing_mode=line_item) — linked to JOB-900001 | Part of Q-CONV-001 chain |
| `invoice_line` | 3 | Line 1: Standard Outlet Install ×3 (labor, taxable, $450); Line 2: 15A Circuit Breaker ×12 (material, taxable, $216); Line 3: Permit Fee ×1 (misc, exempt, $250). Total: $916 + $39.96 tax = $955.96 | **SD-6**: source_type='ad_hoc'; pricebook FKs set |
| `invoice_line_tax_component` | 2 | US-DEFAULT 6% components for lines 1+2 | **SD-6** |
| `payment` | 1 | $955.96 payment for INV-900001 (status=succeeded, paid_via=check) | **SD-6: amount updated from $1,026 to $955.96 (matches line math)** |
| `change_order` | 2 | CO-001: "Additional 20A breakers — awaiting owner approval" ($314.64 total); CO-002: "EMT conduit extension — approved by owner 2026-07-10" ($466.40 total) | **SD-6**: both on JOB-900001 |
| `change_order_line` | 5 | CO-001: 2 lines (breaker ×8 + outlet ×1); CO-002: 3 lines (outlet ×2 + conduit 40ft + note) | **SD-6** |
| `quote_line.taxability_code` / `tax_rate_pct` / `tax_basis_cents` / `tax_amount_cents` / `tax_jurisdiction_code` | NULL | **Set** | **SD-7 Batch 1**: All 28+ quote lines: taxable lines → 6% (NY/default) or 8.25% (TX); exempt lines (Permit Fee, note) → exempt/0. |
| `quote_line_tax_component` | 0 rows | **Populated** | **SD-7 Batch 1**: 1 component row per taxable quote line. component_code = jurisdiction_code; rate_pct matches site state. |
| `change_order_line_tax_component` | 0 rows | **Populated** | **SD-7 Batch 1**: 1 component row per taxable CO line (4 taxable lines from SD-6: CO-001 lines 1+2, CO-002 lines 1+2). |
| `quote_acceptance` | 0 rows | **1 row** | **SD-7 Batch 1**: Internal owner-recorded acceptance for QUO-900005. `accepted_by_user_id=owner`, `contact_id=NULL`, `quote_public_link_id=NULL`. |
| `quote_approval_comment` | 0 rows | **1 row** | **SD-7 Batch 1**: `comment_type='kickback'` on QUO-900001 (pending_approval) — reviewer requesting permit fee clarification + AFCI breaker count. |
| `quote_message` | 0 rows | **1 row** | **SD-7 Batch 1**: `action_type='tenant_user'` follow-up message on QUO-900004 (sent). |
| `customer.dba_name` / `.notes` / `.taxability_code` / `.last_assigned_tech_id` / `.locale` / `.timezone` | NULL | **Set** | **SD-7 Batch 1**: Apex Commercial LLC → dba_name + notes + taxability_code=exempt; Metro Properties LLC → dba_name + notes; John Smith → notes + locale + timezone. |
| `site.notes` / `.hazard_notes` / `.jurisdiction_code` / `.gate_code` / `.access_instructions` | NULL | **Set** | **SD-7 Batch 1**: Smith Residence → notes+jurisdiction; Johnson Home → notes+jurisdiction(TX); Apex HQ → hazard_notes+jurisdiction; Metro Office Park → jurisdiction(TX)+gate_code+access_instructions. |
| `invoice.payment_terms` / `.customer_notes` | NULL | **Set** | **SD-7 Batch 1**: INV-900001 → payment_terms='net_30', customer_notes='Thank you for your business! Payment due within 30 days.' |
| `payment_schedule` | 1 | Active progress schedule on QUO-900002 (Apex Commercial LLC / Apex HQ). `contract_total_cents` = quote total; `status='active'`; `basis_default='percent'`. | **BILLING-B1**: Progress billing orchestration. |
| `payment_schedule_line` | 3 | Draw 1 "Deposit" (fixed_amount $500, invoiced → INV-900020); Draw 2 "Rough-in" (percent 50%, pending, milestone trigger); Draw 3 "Final" (percent 50%, pending, milestone trigger). Reconcile to contract total. | **BILLING-B1**: 3 draws; deposit pre-linked to a `progress` invoice for FE rendering. |
| `invoice` (progress) | 1 | INV-900020 (draft, billing_mode='progress', total=$500.00, progress_pct=19.77%) — linked to Draw 1 via `payment_schedule_line_id`. | **BILLING-B1**: Generated draw invoice; `payment_schedule_line_id` set. |

#### Dispatch scenario (`seed_scenario_dispatch.py`) — E2E: cp3

| Table | Rows | Data | Notes |
|:---|:---:|:---|:---|
| `job` | 6 | 1: scheduled tomorrow; 2: in_progress today; 3: completed yesterday; 4: completed 3d ago; 5: draft; 6: cancelled (DISP-006). **JOB-UI-B1**: each job has a descriptive `title` (e.g. "Scheduled - Outlet Installation", "In Progress - Panel Upgrade") | SD-5 added cancelled job. **CLASS-B1**: job 1=emergency/service_call, job 2=urgent/panel_upgrade, jobs 3-6=standard + varied types. **JOB-UI-B1**: `title` added to INSERT + idempotent UPDATE |
| `job_tech_assignment` | 5 | Jobs 1–3: primary tech (`...0003`); Jobs 1–2: owner (`...0002`) as helper role, ordinal=2 | SD-5 added owner as secondary on first 2 jobs |
| `tech_availability` | 2 | Tech PTO: next Friday 8am–5pm; Owner unavailable: 2 weeks after next Friday | SD-5 added owner unavailability block |

#### Customer Comms scenario (`seed_scenario_customer_comms.py`) — E2E: cp4

| Table | Rows | Data | Notes |
|:---|:---:|:---|:---|
| `tenant_phone_number` | 1 | +15125559001 (status=provisioning_failed to avoid unique constraint) | FK anchor for threads |
| `customer` | 3 | Carlos Rivera, Linda Park, Sunrise Electric LLC (all +1 410-555-0123) | E.164 US mobile numbers distinct from quote-to-cash scenario |
| `contact` | 3 | One contact per customer with mobile_phone | — |
| `entity_contact` | 3 | primary contact link per customer | — |
| `customer_communication_thread` | 3 | One SMS thread per customer, channel=sms; Sunrise thread = **archived** (SD-5) | SD-5: Sunrise thread status → archived |
| `customer_communication_message` | 9 | 4 (Carlos), 3 (Linda), 2 (Sunrise) — mix inbound/outbound; 2 unread (is_unread_inbound=True) | Unread messages have no `received_at` |

#### Reporting scenario (`seed_scenario_reporting.py`) — dev-only (no E2E cp)

| Table | Rows | Data | Notes |
|:---|:---:|:---|:---|
| `job` | 7 | Panel Upgrade (A, 30d ago), Service Call (B, 45d ago), Commercial Inspection (C, 60d ago), Outlet Install (D, 15d ago), HVAC Coord (E, 20d ago), Generator Hookup (F, 35d ago), Commercial Rewire (G, 75d ago) — all `status=completed`. **JOB-UI-B1**: each job has a descriptive `title` (e.g. "Panel Upgrade — Completed Job A") | Fixed past dates (anchored to 2026-07-01). **JOB-UI-B1**: `title` added to INSERT + idempotent UPDATE |
| `job_time_entry` | 11 | Mix of master + journeyman rates | Uses live labor_rate_version rates from seed_test_tenant.py |
| `job_expense` | 9 | Materials + permits; 20% markup on materials | Uses `materials` and `permits` category codes |
| `job_tech_assignment` | 7 | One per job, role=primary | Tech = UUID `...0003` (tech@pilot.local) |
| `invoice` | 7 | INV-SEED-A (paid), INV-SEED-B (paid), INV-SEED-C (issued), INV-SEED-D (draft), INV-SEED-E (partial), INV-SEED-F (void), INV-SEED-G (writeoff) | All 7 invoice_status codes represented; billing_mode=line_item |
| `invoice_line` | 21 | 3–4 lines per invoice; real pricebook FKs with 6% US-DEFAULT tax on taxable lines. Totals: A=$2,261.35, B=$437.78, C=$1,156.30, D=$169.60, E=$2,158.00, F=$2,343.50, G=$5,068.60 | **SD-6**: source_type='ad_hoc'; invoice totals updated to match line math |
| `invoice_line_tax_component` | 16 | US-DEFAULT 6% components for all taxable lines (Permit Fee lines are exempt) | **SD-6** |
| `payment` | 4 | A: $2,261.35 (succeeded), B: $437.78 (succeeded), E: $800.00 partial (succeeded), B refund: −$32.00 (refunded, SD-2 negative-amount model) | **SD-6: A+B+E amounts updated to match new line totals**. **CE-1**: A payment has `amount_variance_cents=1500`, `variance_resolution=NULL` (unresolved — populates web review banner) |
| `loto_confirmation` | 2 | Row 1: Panel Upgrade job (INV-SEED-A), confirmed 2026-06-01 09:15; Row 2: Commercial Rewire job (INV-SEED-G), confirmed 2026-04-17 08:00 | **SD-6**: job_id looked up via invoice number at seed time |
| `invoice_signoff` | 1 | INV-900002 (job A), signed_by='John Customer', terms_acknowledged=true, signed_at=2026-06-17 | **CE-1**: S3 object at `signatures/{tenant_id}/{invoice_id}/{signoff_id}.png`; minimal 1×1 PNG uploaded via `put_signature_object()`; FKs looked up by invoice_number at runtime |

#### Supplier Catalog scenario (`seed_scenario_supplier_catalog.py`) — dev-only (no E2E cp)

| Table | Rows | Data | Notes |
|:---|:---:|:---|:---|
| `supplier` | 3 | Wesco Distribution, Graybar Electric, Platt Electric Supply | **SD-8**: `website`, `api_auth_type`, `api_base_url` populated via JSON |
| `supplier_item` | **67** | Wesco: 25 items; Graybar: 21 items; Platt: 21 items (1 inactive — discontinued 60W bulb) | **SD-8**: Loaded from JSON files; `description` and `taxability_code` now populated |
| `supplier_item_price` | **67** | One current price row per item (open-ended valid_period) | **SD-8**: Prices match JSON `current_price_dollars` |
| `pricing_cache` | **~25** | Wesco items only — `price_cents` + 90-day `expires_at` | **SD-8**: New |

#### NEC Calculation scenario (`seed_scenario_nec.py`) — E2E: cp8

| Table | Rows | Data | Notes |
|:---|:---:|:---|:---|
| `nec_calculation_log` | 3 | voltage_drop (online, 20A/50ft), voltage_drop (offline, 15A/100ft, captured 3d before anchor), conduit_fill (online, 3/4" EMT, 6 conductors) | SD-5 added conduit_fill row; `--mode` arg added |

#### Mobile Sync scenario (`seed_scenario_mobile_sync.py`) — E2E: cp9

| Table | Rows | Data | Notes |
|:---|:---:|:---|:---|
| `mobile_sync_session` | 2 | Session 1: silent_push, outcome=success, device `...0001`; Session 2: foreground, outcome=partial, device `...0002` | SD-5 added partial-failure session |
| `mobile_sync_event` | 5 | Session 1: create_time_entry (succeeded), create_expense (succeeded); Session 2: update_job_status (conflict, severity=owner_escalation), upload_photo (failed); + **SD-6**: fabricated resolved-escalation event (idempotency_uuid=`...0099`) | SD-5 added conflict + failed events |
| `mobile_sync_owner_escalation` | 2 | Row 1: Open escalation linked to existing update_job_status conflict (status=pending, reason=tech_chose); Row 2: Resolved escalation on fabricated expense-conflict event (status=resolved, resolution_action=use_tech) | **SD-6** (W-12 coverage) |

#### Notifications scenario (`seed_scenario_notifications.py`) — dev-only

| Table | Rows | Data | Notes |
|:---|:---:|:---|:---|
| `in_app_notification` | 5 | For owner user (`dev@pilot.local`): job_activity (unread), sync_conflicts critical (unread), billing (read), customer_activity (read), field_issues (read). Anchored to 2026-07-01. | **SD-6**: New script. priority values: standard/critical only (check constraint) |

#### Tenant site scenario (`seed_scenario_tenant_site.py`) — dev-only

| Table | Rows | Data | Notes |
|:---|:---:|:---|:---|
| `tenant_site` | 1 | Published `hosted_compliance` row for the primary demo tenant (slug=`pilot-dev-tenant`). `published_snapshot` built via `build_snapshot()` from the service renderer. `website_auto_populated=TRUE`. | **C-B16**: New script. Idempotent via `ON CONFLICT (tenant_id) DO NOTHING`. Enables local smoke-testing of public pages at `{slug}.localhost:3000`. |

#### Voice AI scenario (`seed_scenario_voice_ai.py`) — dev/QA (SD-9)

Seeds realistic, CHECK-constraint-valid, multi-user, multi-day voice history for **both** the primary test tenant and tenant-B. Enables the web Voice AI History / Session Detail / Command Detail / feedback review / analytics surfaces to render real data. Rolling `NOW()` timestamps (not a fixed anchor) so sessions stay "today/yesterday" across re-seeds.

| Table | Rows (tenant-1) | Rows (tenant-B) | Data | Notes |
|:---|:---:|:---:|:---|:---|
| `conversation_session` | 6 | 2 | S1 owner active "Johnson panel quote"; S2 owner active "Davis 200A panel" (user-renamed); S3 tech ended "Field ops — Smith residence"; S4 tech ended "Time + expense logging"; S5 owner archived "Metro office rough-in"; S6 tech abandoned NULL title (fallback exercise); SB1/SB2 tenant-B | Deterministic UUIDs (`0010` family). `context_window_json` populated with runtime-resolved quote/job/customer IDs. `context_embedding`=NULL. |
| `conversation_message` | 28 | 6 | Alternating user/assistant turns + 1 `system` role (S1 session-init). 2 rows carry `structured_content_json`: S1 snapshot `quote_draft`, S3 live `job_etc_status`. | Deterministic UUIDs (`0011` family). `embedding`=NULL, `audio_object_key`=NULL. Append-only (`created_at`+`created_by` only). |
| `voice_command_log` | 13 | 3 | V1–V13 (tenant-1): create_quote, add_quote_line, query_job_profit, clock_in, log_time_entry, add_expense, update_job_status, navigate, schedule_job, check_next_job, parse-fail, deferred-completed, deferred-failed. VB1–VB3 (tenant-B): create_customer, tell_customer_arrived, calculate_voltage_drop. | `idempotency_uuid` on every row (`0013`/`0014` families). 2 rows with NULL latencies (report null-exclusion path). 2 deferred rows (processing_status=completed/failed). `voice_command_log` has **no** `created_by` column. |
| `voice_command_entity_link` | 5–6 | 0 | Links V4→job (clock_in), V5→job_time_entry (logged), V6→job_expense (created), V7→job (status_changed), V9→job (rescheduled, if Metro job exists), V1→quote (created). | Tenant-B gets **no** entity links (no tenant-B entities exist; `entity_id` is a bare UUID — cross-tenant linking would fabricate an audit lie). Entity IDs resolved by runtime business-key lookup. |
| `voice_feedback` | 2 | 0 | F1: transcription normalization (V2); F2: intent misparsed retrain sample (V11). | `s3_export_key`=NULL, `exported_at`=NULL (unexported — surfaces in `exported=false` filter). Deterministic UUIDs (`0012` family). |

**Second tenant** (`seed_second_tenant.py`, Group C): tenant `…-0006` "Pilot Dev Tenant B" + 2 users (`devb@pilot.local` owner, `techb@pilot.local` technician) + `tenant_user` rows (master/EMP-B01, journeyman/EMP-B02) + email `user_endpoint` rows. Deliberately minimal — no subscription, labor rates, or Group D business entities. Cognito pool users are out of scope (DB rows only).

---

## 5. Deterministic UUIDs (Permanent — Never Reuse)

These UUIDs are hardcoded across all seed scripts, test fixtures, and API mocks. **Do not reuse `...0001` through `...0005` in any new script or test.**

| Entity | UUID | Email | Color |
|:---|:---|:---|:---|
| Test Tenant | `00000000-0000-0000-0000-000000000001` | — | — |
| Owner User | `00000000-0000-0000-0000-000000000002` | `dev@pilot.local` | `#10B981` (green) |
| Technician User | `00000000-0000-0000-0000-000000000003` | `tech@pilot.local` | `#3B82F6` (blue) |
| Office Staff User | `00000000-0000-0000-0000-000000000004` | `office@pilot.local` | `#F59E0B` (amber) |
| Accountant User | `00000000-0000-0000-0000-000000000005` | `accountant@pilot.local` | `#8B5CF6` (purple) — **SD-4** |
| Second Tenant | `00000000-0000-0000-0000-000000000006` | — | — | **SD-9** |
| Tenant-B Owner | `00000000-0000-0000-0000-000000000007` | `devb@pilot.local` | `#EF4444` (red) — **SD-9** |
| Tenant-B Technician | `00000000-0000-0000-0000-000000000008` | `techb@pilot.local` | `#06B6D4` (cyan) — **SD-9** |
| System Sentinel | `00000000-0000-0000-0000-000000000000` | `system@pilot.internal` | — |
| E2E Seed Device | `00000000-0000-0000-0001-000000000001` | — | — |

**SD-9 Voice AI deterministic UUID families** (registered 2026-08-19):

| Entity | UUID family | Notes |
|:---|:---|:---|
| Voice sessions | `00000000-0000-0000-0010-0000000000NN` (NN=01–08) | Deterministic — idempotent seed by PK existence |
| Voice messages | `00000000-0000-0000-0011-0000000000NN` (NN=01–34) | Deterministic |
| Voice feedback | `00000000-0000-0000-0012-0000000000NN` (NN=01–02) | Deterministic |
| Offline-log idempotency UUIDs | `00000000-0000-0000-0013-0000000000NN` (NN=01–02) | On the 2 deferred-pipeline rows |
| Sync-log idempotency UUIDs | `00000000-0000-0000-0014-0000000000NN` (NN=01–13) | On the 13 synchronous command logs |

All Group D scenario rows (customers, sites, jobs, quotes) use `gen_random_uuid()` — they are intentionally non-deterministic. **Exception**: SD-9 Voice AI session/message/feedback rows use deterministic UUID families (above) for PK-existence idempotency — these tables have no natural unique key.

---

## 6. Run Order & Quick Commands

### Target an environment (`--env` / `SEED_ENV`)

All seed scripts accept `--env {dev,e2e,qa,prod}` or the `SEED_ENV` env var. Precedence: **`--env` flag > `SEED_ENV` > default `dev`** — default behavior is unchanged from before DB-MGMT-1. Every run prints a banner with the resolved environment and vendor posture. Guards are fail-closed: Group C/D scripts refuse `--env prod`, `reset_dev_db.py` refuses `e2e`/`prod`, non-prod scripts refuse RDS hosts, and `--env prod` requires the tunnel/RDS host shape. Seed scripts never read the app's pydantic `ENVIRONMENT` (design §G-1) — `prod` (seed vocabulary) vs `production` (app vocabulary) is intentional.

```bash
python migrations/scripts/seed_core.py                                          # dev (default)
SEED_ENV=qa python migrations/scripts/seed_core.py                              # env var
python migrations/scripts/seed_core.py --env qa                                 # explicit flag
python migrations/scripts/seed_platform.py --env prod --stripe-mode test        # prod also requires --stripe-mode
```

What differs per environment lives in [§7.5](#75-environment-value-matrix-db-mgmt-1--adr-0016); the group × env gating matrix there is enforced in code by `_env_profiles.py`.

### Fresh dev environment setup

```bash
cd /path/to/pilot/backend
source .venv/bin/activate

# Step 0 — Ensure schema is at latest migration
alembic upgrade head

# Step 1 — Re-insert lookup data (no-op if already populated by migrations)
python migrations/scripts/seed_core.py

# Step 2 — Platform config (plans + subscription_status)
python migrations/scripts/seed_platform.py

# Step 3 — Test tenant + users + pricing engine + subscription
python migrations/scripts/seed_test_tenant.py

# Step 3b — Second tenant (SD-9: tenant isolation validation)
python migrations/scripts/seed_second_tenant.py

# Step 4 — All scenario data
python migrations/scripts/seed_scenario_quote_to_cash.py
python migrations/scripts/seed_scenario_dispatch.py
python migrations/scripts/seed_scenario_customer_comms.py
python migrations/scripts/seed_scenario_reporting.py
python migrations/scripts/seed_scenario_supplier_catalog.py
python migrations/scripts/seed_scenario_nec.py
python migrations/scripts/seed_scenario_mobile_sync.py
python migrations/scripts/seed_scenario_notifications.py
python migrations/scripts/seed_scenario_voice_ai.py

# Step 5 — Verify
python migrations/scripts/seed_test_tenant.py --mode inspect
python migrations/scripts/seed_second_tenant.py --mode inspect
python migrations/scripts/seed_scenario_voice_ai.py --mode inspect
python migrations/scripts/reset_dev_db.py --mode inspect
```

**Expected after Step 5**:
- `[subscription] 1 row(s)  plan=charter_plan  is_active=True`
- `[user_endpoint] 12 row(s)` (4 users × 3 channels: email, in_app, push)
- `[customer] 11+ row(s)` (8 QTC + 3 comms), `[job] 7+ row(s)`, `[quote] 10 row(s)`
- `[mobile_sync_session] 2 row(s)`, `[nec_calculation_log] 3 row(s)`, `[in_app_notification] 5 row(s)`
- `[conversation_session] 6 row(s)` (tenant-1) + `2 row(s)` (tenant-B) — **SD-9**
- `[voice_command_log] 13 row(s)` (tenant-1) + `3 row(s)` (tenant-B) — **SD-9**

### E2E database setup (isolated pilot_e2e_db)

Run once after the E2E Docker container is started (`docker-compose -f docker-compose.e2e.yml up -d`), and re-run Step 1 whenever schema migrations are applied to `pilot_dev`.

> **DB-MGMT-1**: Steps 1–2 are now generalized as [`migrations/scripts/provision_schema.py`](migrations/scripts/provision_schema.py) — `DATABASE_URL=postgresql://pilot:pilot_e2e_password@localhost:5434/pilot_e2e_db python migrations/scripts/provision_schema.py --env e2e` performs the same dump → apply → UUID-patch → stamp flow. `init_e2e_schema.py` remains as a thin back-compat wrapper, so the commands below still work unchanged.

```bash
cd /path/to/pilot/backend
source .venv/bin/activate

# Step 1 — Generate schema dump from dev DB
pg_dump -h localhost -p 5432 -U pilot -d pilot_dev --schema-only \
    -f /tmp/pilot_dev_schema.sql

# Step 2 — Apply schema + stamp alembic on E2E DB
# NOTE: E2E DB runs on port 5434 (docker-compose.e2e.yml). Port 5433 is the prod SSH tunnel.
DATABASE_URL=postgresql://pilot:pilot_e2e_password@localhost:5434/pilot_e2e_db \
python tests/e2e/init_e2e_schema.py /tmp/pilot_dev_schema.sql

# Step 3 — Seed all data into E2E DB
DATABASE_URL=postgresql://pilot:pilot_e2e_password@localhost:5434/pilot_e2e_db \
SMS_CARRIER=mock ENVIRONMENT=dev \
python tests/e2e/seed_e2e_db.py

# Step 4 — Run E2E tests
python -m pytest tests/e2e/ --e2e --tb=short -q
```

### QA database provisioning (`pilot_qa`)

Full A+B+C+D density with test-mode values — Tom's beta-testing profile. Targets a local `pilot_qa` DB today; the Phase 2 QA RDS is the same flow over the SSH tunnel (URL-only change). Verified end-to-end against a scratch DB 2026-08-18 (proof in §7.6).

```bash
# Step 1 — Schema-restore from dev (pg_dump → apply → UUID patch → alembic stamp)
DATABASE_URL=postgresql://pilot:pilot@localhost:5432/pilot_qa \
python migrations/scripts/provision_schema.py --env qa

# Step 2 — Seed Groups A→B→C→D (all 8 universal scenarios)
DATABASE_URL=postgresql://pilot:pilot@localhost:5432/pilot_qa \
python migrations/scripts/seed_qa_db.py

# Step 3 — Verify counts against the §4 manifest
DATABASE_URL=postgresql://pilot:pilot@localhost:5432/pilot_qa \
python migrations/scripts/seed_core.py --env qa --mode inspect
```

### Production converge (Tom only)

Prod is **converged in place — never wiped** (ADR-0016 §G-3). Groups A+B only; the registry refuses Group C/D against prod. Run after any batch that changes Group A/B data, and at the GA Stripe key flip.

```bash
# Dry-run first (no typed confirmation required)
DATABASE_URL=<prod tunnel URL> \
python migrations/scripts/seed_prod_db.py --stripe-mode test --mode show

# Converge for real (typed confirmation PILOT-PROD-SEED + Stripe key preflight)
DATABASE_URL=<prod tunnel URL> \
python migrations/scripts/seed_prod_db.py --stripe-mode test   # 'live' only after the GA key flip
```

### Starter pricebook for a new tenant (concierge)

Run once per new founder tenant so they have a real, editable catalog on first login (`pilot-founder-onboarding-process.md` _(private)_ Stage C). Idempotent via `ON CONFLICT (tenant_id, sku) DO NOTHING`.

```bash
DATABASE_URL=<prod tunnel URL> \
python migrations/scripts/seed_pricebook_starter.py --env prod --tenant-id <new tenant UUID>
```

### Daily reset (wipe scenario data and reseed)

```bash
# Option A — Interactive (recommended)
python migrations/scripts/reset_dev_db.py

# Option B — CLI (CI-friendly)
python migrations/scripts/reset_dev_db.py --wipe-only
python migrations/scripts/seed_scenario_quote_to_cash.py
python migrations/scripts/seed_scenario_dispatch.py

# Option C — Wipe + reseed specific scenarios
python migrations/scripts/reset_dev_db.py --scenarios quote_to_cash,dispatch
```

### Inspect current state

```bash
python migrations/scripts/seed_core.py --mode inspect        # Group A lookup tables
python migrations/scripts/seed_platform.py --mode inspect    # Group B platform config
python migrations/scripts/seed_test_tenant.py --mode inspect # Group C test tenant
python migrations/scripts/reset_dev_db.py --mode inspect     # Group D scenario data
```

### Schema-only restore recovery

> **DB-MGMT-1**: for a blank target DB, prefer the one-step generalized tool — `python migrations/scripts/provision_schema.py --env {dev,qa,e2e}` (pg_dump from dev → apply → UUID patch → `alembic stamp head`). The manual sequence below documents what it automates.

If the DB was restored from a pg_dump that only captured schema (no data):

```bash
alembic stamp head                                                    # register version without re-running migrations
python migrations/scripts/seed_core.py                               # re-insert Alembic-managed lookup data
python migrations/scripts/seed_platform.py
python migrations/scripts/seed_test_tenant.py
python migrations/scripts/seed_scenario_quote_to_cash.py
python migrations/scripts/seed_scenario_dispatch.py
```

### Wipe Group C (full test tenant reset)

```bash
python migrations/scripts/seed_test_tenant.py --reset   # ⚠️ 3-second countdown — wipes tenant config + all Group D
python migrations/scripts/seed_test_tenant.py           # re-seed tenant
python migrations/scripts/seed_platform.py             # re-seed platform config if needed
python migrations/scripts/seed_scenario_quote_to_cash.py
python migrations/scripts/seed_scenario_dispatch.py
```

---

## 7. Known Constraints & Gotchas

### Seed scripts only manage their own inserted data

Each seed script is responsible only for data it has inserted. Do NOT add cleanup logic to `reset_dev_db.py` for rows that originated from manual testing or prior debugging sessions. If the DB contains spurious rows from testing, clean them with a standalone SQL DELETE statement run manually. If a completely clean DB is needed, instantiate from the schema-only SQL file and run seed scripts in order (A → B → C → D).

### pricebook_item UUIDs are non-deterministic — never hardcode them

[`pricebook_item`](../backend/migrations/scripts/seed_scenario_quote_to_cash.py) rows use `gen_random_uuid()` — their IDs change on every reset+reseed. **Never hardcode a `pricebook_item_id` UUID in a seed script constant.** Always look up IDs at runtime by SKU:

```python
pricebook_item_ids = {
    row.sku: str(row.id)
    for row in db.execute(
        text("SELECT id, sku FROM public.pricebook_item WHERE tenant_id = :tid AND is_active = true"),
        {"tid": tid},
    ).fetchall()
}
# Then reference: pricebook_item_ids.get("OUTLET-STD-01")
```

The `QCO_*` line type constants are stable (Alembic-managed UUID PKs — same across reseeds) and may remain hardcoded.

### Customer phone numbers in the comms scenario share one test number

All 3 customers in [`seed_scenario_customer_comms.py`](../backend/migrations/scripts/seed_scenario_customer_comms.py) (Carlos Rivera, Linda Park, Sunrise Electric LLC) share one 555 test number (`+14105550123`). For end-to-end SMS and MFA testing on a real device, replace it locally with your own phone number; never commit a real number.

### `reset_dev_db.py` and `seed_test_tenant.py --reset` use SAVEPOINT-per-table

Both wipe scripts use `SAVEPOINT` + `ROLLBACK TO SAVEPOINT` per table rather than bare `try/except: pass`. This prevents a single FK violation from poisoning the entire transaction (which would cause `InFailedSqlTransaction` on all subsequent DELETEs). If a table is skipped with `⚠️ Skipped (IntegrityError)`, it means a child table has not been deleted yet — the FK order in `GROUP_D_TABLES` / `group_d_deletes` needs to be corrected.

### DELETE safety rule — `mode_seed` must never delete unrelated rows

**This rule is mandatory for any agent modifying seed scripts.**

There are two contexts where DELETEs appear in seed scripts:

| Context | Rule |
|:---|:---|
| **`mode_reset`** | May delete ALL rows for `tenant_id` in the script's owned tables — this is the explicit wipe path |
| **`mode_seed`** | May ONLY delete the exact row(s) it is about to re-insert — matched by the full business key `(user_id + channel + value)`, `(tenant_id + name)`, etc. |

**Never write a `mode_seed` DELETE scoped to `(user_id, channel)` alone** — that would delete ALL endpoints for that channel, including real device tokens added by the app. The DELETE must always include the `value` field (or equivalent unique attribute) so only the exact duplicate is removed before re-insertion.

**Correct pattern** (used in `seed_test_tenant.py` for `user_endpoint`):
```sql
-- ✅ Correct: value-scoped DELETE removes only the exact row we're about to insert
DELETE FROM public.user_endpoint
WHERE user_id = :uid AND channel = 'in_app' AND value = :value;
INSERT INTO public.user_endpoint (...) VALUES (...);
```

**Forbidden pattern**:
```sql
-- ❌ Wrong: channel-scoped DELETE removes ALL in_app endpoints for this user
DELETE FROM public.user_endpoint WHERE user_id = :uid AND channel IN ('in_app', 'push');
```

This applies to every table that lacks a unique constraint on the natural key — use `(user_id, channel, value)`, `(tenant_id, name)`, `(tenant_id, code)`, or equivalent fully-qualified match. Tables that have a proper unique constraint should use `INSERT ... ON CONFLICT DO NOTHING` instead of DELETE + INSERT.

### Run order is mandatory

```
seed_core.py  →  seed_platform.py  →  seed_test_tenant.py  →  seed_scenario_*.py
```

`seed_test_tenant.py` creates a `subscription` row that requires the `product_plan_code` FK to exist in `product_plan` (Group B). If `seed_platform.py` hasn't run, subscription creation is **silently skipped** — no error, just a warning message.

### Reserved UUIDs (`...0001` through `...0005`)

These are permanently occupied. All new scenario data must use `gen_random_uuid()` in SQL or `uuid.uuid4()` in Python.

### GiST exclusion constraint (open-ended date ranges)

`labor_rate_version` and `tenant_markup_version` use open-ended ranges `[2026-06-01, NULL)`. Any future scenario script that inserts additional rows for the same `(tenant_id, category)` combination **must** use past closed ranges (e.g., `[2019-01-01, 2019-12-31)`) to avoid ExclusionViolation errors.

### Shared DB with the test suite

The seed scripts and `pytest` share the same local PostgreSQL database (`pilot_dev`). Any seed data that a test doesn't expect will cause test failures. **The golden rule**:

> After running any seed script for the first time, run `pytest -q` and confirm zero new failures before declaring the seed run complete.

The E2E DB (`pilot_e2e_db`, port 5434) is fully isolated — E2E tests use persistent state (no rollback per-test) and assert by ID, not by count.

### `subscription_status` fixture in `conftest.py`

The `subscription_status_active` fixture in `tests/batch_b19/test_stripe_subscription_lifecycle.py` was updated in Phase 0.8 to **query** the seeded row instead of inserting its own. If you ever see duplicate `active` row errors in that test, it means a conftest fixture somewhere is inserting a new `subscription_status` row — not a seed script bug.

### `user_endpoint` trigger guards

Two DB triggers protect `user_endpoint` integrity:
- `trg_user_endpoint_guard_bd` — blocks deletion of the last primary email endpoint
- `trg_user_endpoint_guard_biu` — blocks demotion of the last primary email endpoint

To delete `user_endpoint` rows during cleanup, disable both triggers first (see full SQL in [`dev-docs/seed-data/seed-scripts-usage-reference-analysis.md`](../dev-docs/seed-data/archived/seed-scripts-usage-reference-analysis.md) §8).

### `StandardAuditMixin` tables need explicit `created_at`/`updated_at`

All tables with `StandardAuditMixin` have `created_at NOT NULL` and `updated_at NOT NULL` but **no server-side `DEFAULT NOW()`**. Any raw SQL INSERT must include `created_at, updated_at` explicitly with `NOW(), NOW()`.

### "Empty tenant" tests must use `second_tenant`

`test_tenant` (`...0001`) will always have labor rate, markup, discount, and checklist seed rows. Any test that expects an empty initial state must use the `second_tenant` fixture instead of `test_tenant`.

### `qco_line_type` and `jwk_status` UUIDs are non-deterministic — look up by code

`seed_core.py` uses `gen_random_uuid()` for `qco_line_type` and `jwk_status` rows. Their UUIDs differ on every freshly-provisioned DB (e.g. QA scratch, e2e). **Never hardcode these UUIDs** in scenario scripts or seed_test_tenant.py — always look them up by `code` at runtime:

```python
qco_line_type_ids = {
    row.code: str(row.id)
    for row in db.execute(
        text("SELECT id, code FROM public.qco_line_type WHERE tenant_id IS NULL")
    ).fetchall()
}
# Then: qco_line_type_ids.get("labor")
```

**DB-MGMT-1 Task 4 fix (2026-08-18):** `seed_test_tenant.py` (auth_jwk → jwk_status) and `seed_scenario_quote_to_cash.py` + `seed_scenario_reporting.py` (invoice_line, change_order_line → qco_line_type) were converted from hardcoded UUIDs to runtime code lookups. This was the root cause of the QA scratch-DB seed failure.

---

## 7.5 Environment-Value Matrix (DB-MGMT-1 / ADR-0016)

Values that differ by target environment. The `_env_profiles.py` registry is the machine-readable source of truth; the seed banner prints the resolved env + vendor posture on every run.

### Seeded values per environment

| Seeded value | dev | e2e | qa | prod Phase 1 (pre-release test env) | prod Phase 2 (GA cutover) |
|---|---|---|---|---|---|
| `subscription_tier.stripe_price_id_monthly` / `_annual` (starter, teams) | test IDs | test IDs | test IDs | **test IDs** (matches `sk_test_` keys in `pilot/prod/stripe`) | **live IDs** (after key flip) |
| `subscription_tier` charter price ID(s) | current value (UNCLASSIFIED — see §7.5 note) | same as dev | same as dev | per `--stripe-mode` | per `--stripe-mode` |
| Group C test tenant incl. `tenant.stripe_customer_id = 'cus_REDACTEDX01'` (test-mode) | ✅ | ✅ | ✅ | ❌ **never** (concierge tenants would come from real signups after launch) | ❌ |
| Group D scenarios (incl. `tenant_phone_number +15125559001` `provisioning_failed`) | ✅ all 9 (8 universal + notifications dev-only) | 5 of 9 (cp-covered, per `seed_e2e_db.py`) | 8 of 9 (`seed_qa_db.py` excludes dev-only notifications) | ❌ **never** | ❌ |
| `@pilot.local` users, reserved UUIDs `...0001`–`...0005` | ✅ | ✅ | ✅ | ❌ | ❌ |
| Pricebook starter catalog | optional per-tenant | — | optional per-tenant | per-tenant at concierge provisioning | per-tenant (GA: fold into signup flow — future batch) |

> **Charter price-ID — CLASSIFIED 2026-08-18 (follow-up closed):** `price_REDACTED09` = the **original test-mode** charter monthly price (first C-B3 test bootstrap; documented in [`batch-c-b4-design.md`](../dev-docs/architecture-design/batch-designs/batch-c-b4-design.md) §A). The test bootstrap re-ran 2026-08-08 and minted new IDs — current values per the emitted mapping files: **test** charter monthly `price_REDACTED15` ([`stripe_ids.test.json`](scripts/stripe_ids.test.json)), **live** charter monthly `price_REDACTED11` (`stripe_ids.live.json` (IDs redacted)); annual = NULL in both modes. Charter is a price on `prod_starter`, not a separate product. **Registry fixed 2026-08-18**: `_env_profiles.py` TEST/LIVE charter slots corrected to the mapping-file values (Tom); remaining step is a dev converge so the DB charter row catches up — after that, prod converge may include the charter row. Details in [`stripe-pricing-config.md`](../dev-docs/integrations/stripe/stripe-pricing-config.md) §4 note.

### Vendor integration posture per environment

| Vendor | dev | e2e | qa (Phase 2) | prod Phase 1 (pre-release test env) | prod Phase 2 (GA) |
|---|---|---|---|---|---|
| **QuickBooks** | sandbox company (multiple sandboxes supported) | none (mocked) | sandbox company — separate from dev's to avoid cross-talk | sandbox | production app |
| **Cognito** | dev pool (MFA Disabled) | mocked ([`conftest_e2e.py`](tests/e2e/conftest_e2e.py)) | QA pool (mirrors prod; added when needed) | prod pool | prod pool |
| **SendGrid** | shared account — real sends supported | mocked | shared account (sandbox mode or dedicated QA key optional) | shared account, low volume | shared account, live |
| **Telnyx** | mock carrier | mock carrier | real (own messaging profile + number, ~$1/mo — §G-11 Option A) | real (campaign `CXXXXXX`) | real |
| **Stripe** | test mode | test mode | test mode | **test mode** (`pilot/prod/stripe` holds `sk_test_` keys) | **live mode** |

### Seed-group × environment gating matrix

Enforced in code by `_env_profiles.py` — a script invoked with a disallowed group/env combination **exits non-zero with an explicit message** (fail-closed).

| Group / script | dev | e2e | qa | prod |
|---|:---:|:---:|:---:|:---:|
| A — `seed_core.py` | ✅ | ✅ | ✅ | ✅ |
| B — `seed_platform.py` | ✅ | ✅ | ✅ | ✅ (env-driven values + `--stripe-mode` + preflight) |
| C — `seed_test_tenant.py` + `seed_second_tenant.py` | ✅ | ✅ | ✅ | ❌ refused |
| D — 10× `seed_scenario_*.py` (notifications is dev-only; voice_ai is dev/QA) | ✅ | subset via orchestrator | ✅ 9 universal | ❌ refused |
| `seed_pricebook_starter.py` | ✅ | — | ✅ | ✅ (concierge, `--tenant-id`) |
| `reset_dev_db.py` (wipe tool) | ✅ | ❌ (docker volume wipe) | ✅ local-only | ❌ **refused — prod wipe is forbidden** |

---

## 7.6 Per-Environment Provisioning Runbook (DB-MGMT-1 / ADR-0016)

> **Cross-ref**: [`aws-ops-runbook.md`](../dev-docs/devops/aws-ops-runbook.md) §Database Operations links here.

| Env | Provision schema | Seed data | Re-run cadence |
|---|---|---|---|
| **dev** | `alembic upgrade head` (unchanged) | existing quick commands (§6) | daily reset as today |
| **e2e** | `provision_schema.py --env e2e` (schema-restore from dev dump) | `tests/e2e/seed_e2e_db.py` (unchanged entry point) | after schema change |
| **qa** (local `pilot_qa` now; RDS Phase 2) | `provision_schema.py --env qa` | `seed_qa_db.py` | on demand for Tom's beta passes |
| **prod** | **n/a — converge only** (never wipe; ADR-0016 §G-3) | `seed_prod_db.py --stripe-mode <mode>` (Tom executes) | after any batch touching Group A/B data; at GA key flip |

### QA scratch-DB proof (verified 2026-08-18)

```bash
# 1. Create scratch DB
createdb -h localhost -p 5432 -U pilot_user pilot_qa_scratch

# 2. Provision schema from dev dump
DATABASE_URL=postgresql://pilot:pilot@localhost:5432/pilot_qa_scratch \
python migrations/scripts/provision_schema.py --env qa

# 3. Seed all groups (A→B→C→D, 13 steps: A+B+C+second-tenant+9 scenarios+tenant_site)
DATABASE_URL=postgresql://pilot:pilot@localhost:5432/pilot_qa_scratch \
python migrations/scripts/seed_qa_db.py

# 4. Verify inspect counts match dev baseline
DATABASE_URL=postgresql://pilot:pilot@localhost:5432/pilot_qa_scratch \
python migrations/scripts/seed_core.py --env qa --mode inspect

# 5. Drop scratch DB
dropdb -h localhost -p 5432 -U pilot_user pilot_qa_scratch
```

**Result**: all 11 seed steps passed (pre-SD-9; now 13 steps with second-tenant + voice_ai); inspect counts match dev baseline exactly (platform_setting_catalog=48, communication_template=17, notification_type=17, job_type=11, email_template=16, jwk_status=3, quote_template_line=9). **SD-9 (2026-08-19)**: `seed_qa_db.py` now runs 13 steps (added `seed_second_tenant.py` after Group C + `seed_scenario_voice_ai.py` in the scenario list).

#### Per-tenant seed write-path proof (verified 2026-08-27 — TEST-UPLIFT-1A)

**Standing rule**: Every new or changed seed script must execute its `mode_seed` write path against a scratch DB as part of the §7.6 QA-proof before its batch closes — no seed script ships write-path-unexecuted.

The 2026-08-25 `NotNullViolation` on `pricebook_item_version.created_at` (NOT NULL, no server default), hit on first use on the pre-release AWS environment, was caused by `seed_pricebook_starter.py --mode seed` never having executed against a live DB. This step codifies the proof that would have caught it.

```bash
# After the 13-step group seed above, run the per-tenant seed write-path proof:
DATABASE_URL=postgresql://pilot:pilot@localhost:5432/pilot_qa_scratch \
python migrations/scripts/seed_pricebook_starter.py --env qa --mode seed --tenant-id 00000000-0000-0000-0000-000000000001
# Expected: 13 items inserted, 0 errors (no NotNullViolation)
```

**Result (2026-08-27)**: 13 items inserted, 0 already existed, 0 errors. The `pricebook_item_version.created_at` NOT NULL column (no server default — only `recorded_at` has `now()`) was correctly populated by the seed script's ORM insert path. Proof clean.

---

## 7.7 Migration-Sync Runbook (DB-MGMT-1 / ADR-0016)

> **ADR-0016 binding rule**: migrations are DDL-only. Migration-embedded INSERTs are a code-review reject. New reference data ships in `seed_core.py`/`seed_platform.py` in the same PR.

1. **Author (dev)**: migration is DDL-only (ADR-0016 E-4); new reference data goes to `seed_core.py`/`seed_platform.py` in the same PR. `alembic upgrade head` on dev; `pytest -m unit` green.
2. **e2e**: `alembic upgrade head` against `pilot_e2e_db` (stamped at head, so clean) → `seed_core.py --env e2e` + `seed_platform.py --env e2e` (converge new rows) → inspect.
3. **qa**: same as e2e against the qa target.
4. **prod** (deploy window per [`aws-ops-runbook.md`](../dev-docs/devops/aws-ops-runbook.md)): RDS snapshot → `alembic upgrade head` via tunnel → `seed_prod_db.py --stripe-mode <current-mode>` converge → inspect counts vs README §4 manifest.
5. **Manifest upkeep**: any PR changing seed rows updates README §4 expected counts — the inspect output is the verification contract.

---

## 8. What Is NOT Seeded by These Scripts

### 8.1 — Permanently excluded (external API / pipeline dependency)

| Table | Reason |
|:---|:---|
| ~~`app_service`, `app_service_provider`~~ | **QB-H1 (2026-08-28): Removed from exclusion** — now owned by `seed_core.py` Group A (category `accounting`, provider `quickbooks`, global `app_service` row at deterministic UUID `…000aa5`). Canonical `provider_code` is `quickbooks` (design §G Q1). See [§4 Group A](#4-current-seed-state--what-is-in-the-db). |
| `payment_method` | Schema requires real Stripe `psp_payment_method_id`; cannot be faked. Deferred per SD-09. |
| `psp_customer`, `psp_transaction_log` | Requires real Stripe transaction IDs from live webhook events; cannot be fabricated without risk of FK cascade issues. |
| `help_article`, `help_article_chunk`, `help_training_corpus` | Requires embedding pipeline or pre-computed vectors. Deferred per SD-09. |
| ~~`voice_command_log`, `voice_command_entity_link`, `voice_feedback`, `conversation_session`, `conversation_message`~~ | **SD-9 (2026-08-19): Removed from exclusion** — now seeded by `seed_scenario_voice_ai.py`. See [§4 Group D — Voice AI scenario](#voice-ai-scenario-seed_scenario_voice_aipy--devqa-sd-9). |
| `integration_credential`, `integration_sync_log`, `integration_sync_conflict`, `connector_run_log`, `connector_config` | Requires QuickBooks OAuth flow; blocked by external API dependency. |
| `auth_email_verification`, `auth_mfa_otp`, `auth_password_reset`, `auth_refresh_token`, `auth_password_history` | Runtime auth flow tables — ephemeral, no stable seed values. |
| `calendar_sync_conflict`, `calendar_sync_log`, `tenant_calendar_integration` | Requires live Google/Outlook OAuth token. |
| `idempotency_key` | Runtime dedup table — ephemeral by design. |
| `user_sso_identity` | Requires real OAuth provider login. |
| `stripe_webhook_event_processed` | Requires real Stripe webhook event IDs. |

All other lookup, platform config, and reference tables are covered by `seed_core.py` (Group A) or `seed_platform.py` (Group B).

---

### 8.2 — On Hold (seed-ready but deferred by formal decision — 2026-07-23)

These tables and fields **can** be seeded without external dependencies but are deliberately held back until the corresponding feature or infrastructure is operational. They are tracked in [`dev-docs/seed-data/seed-data-field-gap-analysis-v1.md`](../dev-docs/seed-data/seed-data-field-gap-analysis-v1.md).

#### HOLD: SMS-related fields and tables

**Trigger to un-hold**: Telnyx 10DLC campaign approved + `tenant_phone_number.status = 'active'`

Do NOT populate any of the following until SMS is live:

| Table / Field | What to add when un-held |
|:---|:---|
| `customer_sms_consent_audit` | Consent audit rows for all customers with `sms_opt_in_consent=true` |
| `customer.sms_opt_in_at` | Timestamp when customer consented |
| `customer.sms_opt_in_source` | `"owner_attested"` for manually recorded consents |
| `customer.sms_consent_attested_by` | Owner user UUID |
| `customer.sms_consent_ip_address` | IP address of attesting device |
| `customer.sms_opted_out`, `.sms_opt_out_at` | Opt-out audit fields |
| `user.phone_number` | Required for MFA SMS delivery |
| `sms_quota_period` | Current-period SMS usage meter |
| `contact_endpoint` rows with `channel='sms'` | SMS delivery endpoint for contacts |
| `notification_outbox` rows with `channel='sms'` | SMS notification delivery entries |
| `tenant_phone_number.status` | Do NOT change from `provisioning_failed` — intentional hold value |

#### HOLD: Quote/Invoice Public Links

**Trigger to un-hold**: PDF generation pipeline operational + S3 upload path confirmed + short-link domain registered

Do NOT populate any of the following until the public link pipeline is operational:

| Table | What to add when un-held |
|:---|:---|
| `quote_public_link` | Links for sent/accepted quotes (QUO-900004, QUO-900005) |
| `invoice_public_link` | Link for paid invoice INV-900001 |
| `public_link_short_code` | Short URL entries (requires `p4t-link.com` or similar domain — see §8.3) |
| `quote_public_link_contact_action` | Customer view/approve actions on quote links |
| `invoice.pdf_object_key` | S3 key for generated PDF (depends on PDF pipeline) |

**Note**: `quote_acceptance` CAN be seeded without a public link (the FK `quote_public_link_id` is nullable). It represents an internal owner-recorded acceptance. ✅ Seed this in SD-7.

#### HOLD: Photo Attachments

**Trigger to un-hold**: Tom uploads test photos to S3 dev bucket and provides keys

Do NOT insert fake S3 keys — they break signed URL generation:

| Table | What to add when un-held |
|:---|:---|
| `job_attachment` | Real S3 object keys from dev bucket (path: `job-attachments/test/photo_001.jpg`, etc.) |
| `job_expense.receipt_object_key` | Real S3 receipt photo keys |
| `job_expense.ocr_processed_at` | Set after receipt photo exists |
| `job_expense.ocr_source` | `"mobile_camera"` on OCR-processed expenses |

---

### 8.3 — Short-Link Domain (not yet registered)

The `public_link_short_code` table requires a registered redirect domain. Recommendation: register `p4t-link.com` (or similar). Architecture: Route 53 → CloudFront → Lambda@Edge. The Lambda reads `short_code` from the path, looks up `public_link_short_code`, and returns a `302` redirect to the quote/invoice page URL. Cost: ~$12/yr domain + ~$0 Lambda. Register before unsealing the public-link hold above.

---

## 9. Scenario Status Registry

| Scenario key | Script | E2E critical path | Status |
|:---|:---|:---|:---|
| `quote_to_cash` | [`seed_scenario_quote_to_cash.py`](migrations/scripts/seed_scenario_quote_to_cash.py) | cp2 | ✅ Complete |
| `dispatch` | [`seed_scenario_dispatch.py`](migrations/scripts/seed_scenario_dispatch.py) | cp3 | ✅ Complete |
| `customer_comms` | [`seed_scenario_customer_comms.py`](migrations/scripts/seed_scenario_customer_comms.py) | cp4 | ✅ Complete (SD-02) |
| `reporting` | [`seed_scenario_reporting.py`](migrations/scripts/seed_scenario_reporting.py) | dev-only | ✅ Complete (SD-03) |
| `supplier_catalog` | [`seed_scenario_supplier_catalog.py`](migrations/scripts/seed_scenario_supplier_catalog.py) | dev-only | ✅ Complete (SD-09) |
| `nec` | [`seed_scenario_nec.py`](migrations/scripts/seed_scenario_nec.py) | cp8 | ✅ Complete (E2E-B1) |
| `mobile_sync` | [`seed_scenario_mobile_sync.py`](migrations/scripts/seed_scenario_mobile_sync.py) | cp9 | ✅ Complete (E2E-B1) |
| `notifications` | [`seed_scenario_notifications.py`](migrations/scripts/seed_scenario_notifications.py) | dev-only | ✅ Complete (SD-6) |
| `voice_ai` | [`seed_scenario_voice_ai.py`](migrations/scripts/seed_scenario_voice_ai.py) | dev-only | ✅ Complete (SD-9) |

---

## 10. Roadmap — Data Tasks

All SD-01 through SD-10 tasks are complete as of 2026-07-06. E2E-B1 (cp6–cp9 + nec/mobile_sync scenarios) complete 2026-07-12. SD-4 (Group C expansion + stripe annual prices) complete 2026-07-14. SD-5 (all 7 Group D scenario scripts expanded) complete 2026-07-15. SD-6 (invoice lines, change orders, loto confirmations, escalations, notifications) complete 2026-07-15. ✅

### SD-9 (Voice AI) — Voice AI seed data + second tenant ✅ Complete (2026-08-19)

**Completed**: 2026-08-19
**Mode**: Pilot Python Engineer
**Baseline**: 4633 passed, 1 skipped, 0 failed
**Final**: 4645 passed, 1 skipped, 0 failed (+12 new tests)

Seeded all 5 voice tables (`conversation_session`, `conversation_message`, `voice_command_log`, `voice_command_entity_link`, `voice_feedback`) for both the primary test tenant and a new second tenant (`…-0006`). Created `seed_second_tenant.py` (Group C) and `seed_scenario_voice_ai.py` (Group D). Wired both into `reset_dev_db.py` and `seed_qa_db.py` (13 steps). Removed the stale §8.1 voice-table exclusion row. 12 tests in `test_seed_scenario_voice_ai.py` covering full manifest, idempotency, CHECK validity, referential integrity, reset, tenant-B shape, deferred rows, structured content, and UUID family purity.

### SD-7 — Full Field Completeness Sprint ✅ Complete (2026-07-23) — Batches 1–3

**Status**: ✅ All three batches complete 2026-07-23. All 20 target table counts confirmed via live DB query; full reset + reseed cycle idempotent with 0 skipped tables.
**Gap analysis**: [`dev-docs/seed-data/seed-data-field-gap-analysis-v1.md`](../dev-docs/seed-data/seed-data-field-gap-analysis-v1.md)
**Mode**: Pilot Python Engineer
**Scope decisions recorded**: 2026-07-23 (see §8.2 for hold decisions)

#### SD-7 Batch 1 ✅ Complete (2026-07-23)

**Baseline**: 3 pre-existing failures, 4084 passed, 1 skipped
**Final**: 3 pre-existing failures, 4084 passed, 1 skipped (0 net new failures)

**Files changed**:

| File | Change |
|---|---|
| `backend/migrations/scripts/seed_core.py` | **SD-7 Batch 1** + **QT-FIX-1**: `quote_template_line` — 9 lines across 3 system templates (Service Call Basic: 3, Installation Standard: 4, Fixed Bid Simple: 2). Post QT-FIX-1 (2026-07-30): lines seeded with `tenant_id = NULL` (platform-level); no test-tenant guard; idempotent existence check scoped to `tenant_id IS NULL`. |
| `backend/migrations/scripts/seed_test_tenant.py` | **SD-7 Batch 1**: `user.email_verified_at`+`last_login_at` for all 4 test users; `tenant_user.skill_level_code`+`employee_number`; `auth_jwk` active signing key (`pilot-dev-signing-key-v1`, RS256). |
| `backend/migrations/scripts/seed_scenario_quote_to_cash.py` | **SD-7 Batch 1**: `_seed_sd7_batch1_fields()` helper — `quote_line` tax fields (all 28+ lines); `quote_line_tax_component` rows; `change_order_line_tax_component` rows (4 taxable CO lines); `quote_acceptance` for QUO-900005; `quote_approval_comment` (kickback) for QUO-900001; `quote_message` for QUO-900004; customer fields (`dba_name`, `notes`, `taxability_code`, `last_assigned_tech_id`, `locale`, `timezone`) on 3 customers; site fields (`notes`, `hazard_notes`, `jurisdiction_code`, `gate_code`, `access_instructions`) on 4 sites; invoice `payment_terms`+`customer_notes` on INV-900001. |
| `backend/README-seed-data.md` | Updated §1, §4, §10. |

#### What SD-7 Accomplished

SD-7 filled the field-level and table-level gaps identified in the 2026-07-23 full DB audit. All three batches complete. Fixes applied during the sprint: `reset_dev_db.py` moved `quote_version` after `job` in `GROUP_D_TABLES` (FK ordering); `seed_scenario_dispatch.py` `customer_communication.status` `'delivered'`→`'sent'` (valid per check constraint); `seed_scenario_customer_comms.py` added `ON CONFLICT DO NOTHING` to `tenant_phone_number`; `seed_scenario_notifications.py` removed `to_address` from outbox rows that set `recipient_user_id` (exclusive-recipient constraint).

**Batch 1 — Core field completeness + tax chain ✅ Complete**
- `quote_template_line`: 9 lines across 3 system templates ✅
- `quote_line` + `quote_line_tax_component`: all tax fields populated ✅
- `change_order_line_tax_component` rows ✅
- `quote_acceptance` for QUO-900005 (internal owner-recorded, no public link) ✅
- `quote_approval_comment`, `quote_message` for pending/sent quotes ✅
- Customer fields: `dba_name`, `notes`, `taxability_code`, `last_assigned_tech_id`, `locale`, `timezone` ✅
- Site fields: `notes`, `hazard_notes`, `jurisdiction_code`, `gate_code`, `access_instructions` ✅
- Invoice fields: `payment_terms`, `customer_notes` on INV-900001 ✅
- `auth_jwk`: 1 active signing key ✅
- `tenant_user.skill_level_code`, `tenant_user.employee_number` ✅
- `user.email_verified_at`, `user.last_login_at` ✅

**Batch 2 — Notification pipeline + mobile + usage metering ✅ Complete**
- `notification_event` (3 events: quote_accepted, invoice_sent, dunning_reminder) ✅
- `notification_outbox` (email + in_app + push only — no SMS) ✅
- `notification_delivery_attempt` (1 per outbox row) ✅
- `notification_preference` (owner user channel overrides) ✅
- `mobile_device_push_token` (tech user device registration) ✅
- `mobile_sync_event_audit` (resolved escalation audit) ✅
- `mobile_sync_owner_escalation.resolution_payload` (fill resolved row) ✅
- `subscription_usage` (current-period rows for all 3 product features) ✅
- `tenant_subscription_usage` (current-period summary) ✅
- `usage_ledger` (current-period voice AI + outbound SMS entries) ✅
- `user_dashboard_widget` (3 widgets for owner user) ✅
- `tenant_10dlc_profile` ✅

**Batch 3 — Dispatch + reporting + supplier + optional fields ✅ Complete**
- Rolling dates for all dispatch scenario job timestamps (switch from fixed to `NOW() ± INTERVAL`) ✅
- `job.estimated_duration_minutes`, `job.quote_version_id` on converted job ✅
- `job_time_entry`: GPS coordinates, `gps_variance_meters`, ETC fields, mobile capture timestamps ✅
- `job_expense`: `vendor_name`, mobile capture timestamps ✅
- `job_recurrence_rule` (1 weekly recurring job rule) ✅
- `customer_communication` (1 on-my-way record for dispatch scenario) ✅
- `contact_endpoint` rows (phone channel, `consent_status='unknown'`) ✅
- `customer_communication_message_read_state` for already-read messages ✅
- `customer_communication_unrouted` (1 parked inbound SMS) ✅
- `nec_calculation_log.job_id`, `.client_capture_at` ✅
- Supplier fields: `website`, `api_auth_type`, `api_base_url` ✅
- `pricing_cache` for Wesco items ✅
- Remaining tenant config rows: `tenant_signup`, `tenant_legal_acceptance`, `tenant_tier_override`, `tenant_domain`, `tenant_product_feature_override`, `mfa_grace_period_tracking`, `user_mfa_method`, `user_session_history` ✅

#### What SD-7 Does NOT Include (held — see §8.2)
- Any SMS-related fields or tables (held until Telnyx 10DLC live)
- `quote_public_link`, `invoice_public_link`, `public_link_short_code` (held until PDF pipeline + short-link domain)
- `job_attachment` (held until Tom uploads test S3 photos)
- `job_expense.receipt_object_key` and OCR fields (same hold)

### SD-8 — Supplier Catalog Expansion + Template Test-Fire QA Tool ✅ Complete (2026-07-23)

**Completed**: 2026-07-23
**Mode**: Pilot Python Engineer
**Baseline**: 4086 passed, 1 known pre-existing failure (test_find073_invoice_hmac_tokens)
**Final**: 4086 passed, 1 known pre-existing failure (+0 new tests — seed/QA-tool-only batch)

#### What Was Accomplished

- Refactored `seed_scenario_supplier_catalog.py` to load from JSON data files (same pattern as `data/email_templates/`)
- Expanded catalog from 14 to 67 items: Wesco (25), Graybar (21), Platt (21 active + 1 inactive)
- `supplier_item.description` and `.taxability_code` now populated from JSON
- `pricing_cache` seeded for all 25 Wesco items with 90-day TTL (`expires_at = NOW() + INTERVAL '90 days'`)
- `--reset` correctly wipes `pricing_cache` before `supplier_item_price` (FK order: pricing_cache → supplier_item_price → supplier_item → supplier)
- `--mode inspect` shows pricing_cache row count alongside supplier/item/price counts
- `--mode show` prints item count per supplier from JSON (no DB connection)
- Created `test_fire_templates.py` standalone QA tool — email channel only; `--dry-run` supported; `--email-template` and `--template-type` modes; clear error + exit 1 for unknown templates and non-email channels
- Updated `README-seed-data.md` §2, §4, §10

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/migrations/scripts/seed_scenario_supplier_catalog.py` | Updated — JSON-driven loader, description/taxability_code fields, pricing_cache seeding, updated reset/inspect/show modes |
| `backend/migrations/scripts/test_fire_templates.py` | Created — QA tool for manual template test-fire (email channel only) |
| `backend/migrations/scripts/data/supplier_catalog/wesco.json` | Architect-provided — 25 items (not modified) |
| `backend/migrations/scripts/data/supplier_catalog/graybar.json` | Architect-provided — 21 items (not modified) |
| `backend/migrations/scripts/data/supplier_catalog/platt.json` | Architect-provided — 21 items, 1 inactive (not modified) |
| `backend/README-seed-data.md` | Updated — §2, §4, §10 |

### SD-6 — Deep Seed Data: Line Items, New Scenarios & README Updates ✅ Complete (2026-07-15)

**Completed**: 2026-07-15
**Mode**: Pilot Python Engineer
**Baseline**: 4045 passed, 1 skipped, 0 failed
**Final**: 4045 passed, 1 skipped, 0 failed (0 net new tests — seed-data-only batch)

#### What Was Accomplished

- Seeded `invoice_line` + `invoice_line_tax_component` for all 8 invoices (24 lines, 18 tax components); updated all invoice totals to match line math; updated payment amounts for paid invoices
- Added `mobile_sync_owner_escalation` (1 open + 1 resolved) — closes W-12 coverage gap
- Added `loto_confirmation` (2 confirmed rows) on Panel Upgrade + Commercial Rewire jobs
- Added `change_order` + `change_order_line` (2 COs, 5 lines) on JOB-900001
- Created new `seed_scenario_notifications.py` — 5 `in_app_notification` rows for owner user; registered in `reset_dev_db.py`
- Added `user_preference` + `user_setting_override` to `seed_test_tenant.py`
- Fixed 13 tests that became seed-data-resilience failures (user_preference/user_setting_override/in_app_notification uniqueness conflicts)
- Updated `README-seed-data.md` §4, §7, §8, §9, §10
- **Discovered + corrected 2 column name discrepancies** (vs. design doc): `invoice_line.source_type` check constraint allows `'ad_hoc'` (not `'manual'`); `in_app_notification.priority` allows `'critical'` (not `'urgent'`); `mobile_sync_owner_escalation.escalation_reason` allows `'tech_chose'` (not `'job_status_conflict'`/`'expense_amount_conflict'`); `resolution_action` allows `'use_tech'` (not `'owner_accepted_device_change'`)

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/migrations/scripts/seed_scenario_quote_to_cash.py` | Updated — invoice_line + invoice_line_tax_component for INV-900001 + change_order + change_order_line for JOB-900001 |
| `backend/migrations/scripts/seed_scenario_reporting.py` | Updated — invoice_line + invoice_line_tax_component for INV-SEED-A through G + loto_confirmation |
| `backend/migrations/scripts/seed_scenario_mobile_sync.py` | Updated — mobile_sync_owner_escalation (1 open + 1 resolved) |
| `backend/migrations/scripts/seed_scenario_notifications.py` | Created — new Group D script (5 in_app_notification rows) |
| `backend/migrations/scripts/seed_test_tenant.py` | Updated — user_preference + user_setting_override for owner user |
| `backend/migrations/scripts/reset_dev_db.py` | Updated — registered notifications scenario + added SD-6 tables to GROUP_D_TABLES |
| `backend/README-seed-data.md` | Updated — §4, §7, §8, §9, §10 |
| `backend/tests/batch_b2/test_a7_field_mode.py` | Fixed — seed-data-resilient user_preference INSERT |
| `backend/tests/batch_b9/test_b9_settings_infrastructure.py` | Fixed — seed-data-resilient user_setting_override INSERT + 404 test |
| `backend/tests/batch_b12/test_a67_setting_resolver.py` | Fixed — seed-data-resilient voice_persona_tone override tests |
| `backend/tests/batch_b19/test_find133_mobile_inbox_behavior.py` | Fixed — seed-data-resilient unread_count test |
| `backend/tests/phase_6/test_phase_6_0_1_task_6_audit_fk.py` | Fixed — seed-data-resilient user_preference FK tests (4 tests) |
| `backend/tests/phase_6/test_phase_6_0_task_1_constraints_audit.py` | Fixed — seed-data-resilient user_preference uniqueness test |

---

### SD-5 — Group D Scenario Data Expansion ✅ Complete (2026-07-15)

Delivered 2026-07-15. Expanded all 7 Group D scenario scripts for full UI-testable data density:
- Full quote status coverage (10 quotes, all statuses)
- Full invoice status coverage (7 invoices, all statuses) + 5 payments
- Quote → Job → Invoice relational chain
- 3 suppliers with 14 items (Wesco, Graybar, Platt)
- Multi-tech dispatch + cancelled job + 3 availability blocks
- NEC conduit_fill 3rd calculation type
- Mobile sync partial-failure session + conflict + failed events
- Customer comms archived thread

**Test gate**: `pytest` full suite — 4045 passed, 1 skipped, 0 failed.

---

### SD-4 — Group C Test Tenant Seed Audit & Expansion ✅ Complete (2026-07-14)

Delivered 2026-07-14. Expanded `seed_test_tenant.py` and `seed_platform.py` for comprehensive UI testing:

- Added 4th test user `accountant@pilot.local` (UUID `...0005`, role=accountant, color=#8B5CF6)
- Set display_color for owner (#10B981) and office_staff (#F59E0B)
- Set `tenant.stripe_customer_id = 'cus_REDACTEDX01'` (test-mode Stripe customer)
- Added in_app + push user_endpoint rows for all 4 users (12 total; required new Alembic migration `aaaa1f8d5138` to extend `user_endpoint_channel_chk`)
- Filled password_policy lockout/history fields (threshold=5, window=15m, duration=30m, history=5)
- Set tenant_email_branding.custom_footer
- Updated subscription quantity_seats=4, billing_anchor=2026-07-01
- Updated labor_rate_version burden_pct: master=0.25, journeyman=0.20, apprentice=0.15
- Seeded discount_version: SUMMER_PROMO (10%) + NEW_CUSTOMER ($25 off); added inspect coverage
- Populated subscription_tier.stripe_price_id_annual for starter + teams (test-mode IDs, already in SD-3 code — patch applied to live DB)

**Test gate:** `pytest` full suite — 4080 passed, 39 skipped, 0 failed (baseline: 4045 unit tests passing).

---

### Task SD-01 — Add All Missing Lookup Tables to `seed_core.py` ✅ Complete (2026-07-06)

**Delivered 2026-07-06.** All 14 previously missing tables added to [`migrations/scripts/seed_core.py`](migrations/scripts/seed_core.py) with verified live DB values and all 3 modes (seed / show / inspect) updated.

Tables added: `webhook_event_type`, `sso_provider`, `quote_link_status`, `supplier_item_category`, `supplier_item_uom`, `notification_category_sub_trigger`, `product_feature`, `jwk_status`, `tenant_user_role`, `sync_conflict_classification_matrix`, `communication_template`, `email_template` (16 rows from [`migrations/scripts/data/email_templates/*.json`](migrations/scripts/data/email_templates/)), `platform_setting_catalog` (42 rows), `platform_setting` null-tenant defaults (42 rows).

**Test gate:** `pytest -m unit` — 3859 passed, 0 new failures (vs. 4 pre-existing).

---

### Task SD-02 — Write `seed_scenario_customer_comms.py` ✅ Complete (2026-07-06)

**Delivered 2026-07-06.** New file [`migrations/scripts/seed_scenario_customer_comms.py`](migrations/scripts/seed_scenario_customer_comms.py) created and registered as `"customer_comms"` in [`migrations/scripts/reset_dev_db.py`](migrations/scripts/reset_dev_db.py).

Seeded: 1 `tenant_phone_number` (+15125559001, status=provisioning_failed), 3 customers with E.164 numbers (Carlos Rivera, Linda Park, Sunrise Electric LLC), 3 contacts + entity_contacts, 3 SMS threads, 9 messages (2 unread).

**Test gate:** `pytest -m unit` — 3863 passed, 0 failed.

---

### Task SD-03 — Write `seed_scenario_reporting.py` ✅ Complete (2026-07-06)

**Delivered 2026-07-06.** New file [`migrations/scripts/seed_scenario_reporting.py`](migrations/scripts/seed_scenario_reporting.py) created and registered as `"reporting"` in [`migrations/scripts/reset_dev_db.py`](migrations/scripts/reset_dev_db.py).

Seeded: 4 completed jobs (30/45/60/15 days ago, anchored to 2026-07-01), 7 time entries (master + journeyman rates), 5 expenses (materials + permits, 20% markup), 4 tech assignments.

**Test gate:** `pytest -m unit` — 3863 passed, 0 failed.

---

### Task SD-04 — Update Table of Contents in `README-seed-data.md` ✅ Complete (2026-07-06)

Completed 2026-07-06 — updated §2, §4 Group A, §4 Group D, §9. Re-updated 2026-07-13 when file moved from `migrations/scripts/` to `backend/` and all relative paths corrected.

---

### Task SD-05 — Design: Payment Refund Status Support ✅ Complete (2026-07-06)

> **Design decision**: Add `refunded_amount_cents INTEGER NOT NULL DEFAULT 0` and `refunded_at TIMESTAMPTZ` columns to the `payment` table (no new `payment_status` codes needed); update the Stripe `charge.refunded` / `refund.created` webhook handler to write these columns.

**Completed**: 2026-07-06 (Batch: SD-BE-1)

Delivered: Alembic migration adding `refunded_amount_cents` + `refunded_at` to `payment`; `_handle_refund_event()` webhook handler; `Payment` SQLModel updated. Tests: `tests/domains/invoicing_billing/test_sd05_payment_refund.py` (3 tests). Final: 3912 passed, 0 failed, 1 skipped.

---

### Task SD-06 — Design: Invoice Status Alignment + Automated Late Invoice Reminders ✅ Complete (2026-07-06)

> **Design decision**: (A) `InvoicesPage.tsx` filter bug fixed — `"sent"` → `"issued"`, `"overdue"` removed (derived display state). (B) `dunning.py` enhanced with 3-tier customer SMS reminders (1d/7d/14d), `last_reminder_sent_at` + `reminder_count` on `invoice`, 3 new `platform_setting_catalog` keys.

**Completed**: 2026-07-06 (Backend: SD-BE-1 · Frontend: SD-FE-1)

Delivered: `last_reminder_sent_at` + `reminder_count` on `invoice`; enhanced dunning Celery task; `GET /invoices?overdue=true`; `InvoicesPage.tsx` filter fix. Tests: `tests/domains/invoicing_billing/test_sd06_invoice_dunning.py` (2 pass / 1 skip).

---

### Task SD-07 — Design: Product Feature / Usage Billing Competitive Review ✅ Complete (2026-07-06)

> **Design decision (Tom approved 2026-07-06)**: Revised `product_feature` set: `voice_ai_minutes` (60/240/1000), `dispatch_slots` (5/25/75), `outbound_sms_segments` (100/500/2500), `data_exports` (Teams+ gate). Remove `qb_sync_operations`. Rename `professional_plan` → `teams`.

**Completed**: 2026-07-06 (Batch: SD-BE-2)

Delivered: Alembic migration `fb896203a21a`; `seed_platform.py` + `seed_core.py` updated; `quickbooks_sync.py` UsageLedger write blocks removed. Tests: `tests/domains/subscriptions_usage/test_sd07_feature_revision.py` (11 tests). Final: 3937 passed, 1 skipped.

---

### Task SD-08 — Design: Email Template + Notification Template Review & Update ✅ Complete (2026-07-06)

> **Design decision (Tom approved 2026-07-06)**: All 5 customer-facing `email_template` bodies confirmed as stubs. Architect drafted v1 copy for all 5 templates + 9 `notification_template` body replacements. Tom approved as v1.

**Completed**: 2026-07-06 (Batch: SD-BE-2)

Delivered: Alembic migration `4a2fbda323db` updating all 5 customer-facing email templates and 9 notification templates; 5 email JSON files in [`migrations/scripts/data/email_templates/`](migrations/scripts/data/email_templates/) updated with approved copy. Tests: `tests/domains/notifications_comms/test_sd08_template_copy.py` (8 tests).

---

### Task SD-09 — Design: Seed Data for Empty Functional Tables ✅ Complete (2026-07-06)

> **Design decision**: `discount_version` → 2 rows in `seed_test_tenant.py` (Group C); `supplier`+`supplier_item`+`supplier_item_price` → new `seed_scenario_supplier_catalog.py` (Group D); `quote_template` → 3 Alembic-owned rows confirmed → added to `seed_core.py`. **Deferred**: `payment_method` (real Stripe ID required); `help_article`/`help_article_chunk` (embedding pipeline required).

**Completed**: 2026-07-06 (Batch: SD-BE-1)

Delivered: `quote_template` added to `seed_core.py`; `discount_version` (SUMMER_PROMO + NEW_CUSTOMER) added to `seed_test_tenant.py`; new [`migrations/scripts/seed_scenario_supplier_catalog.py`](migrations/scripts/seed_scenario_supplier_catalog.py) (1 supplier, 5 items, 5 prices) registered as `"supplier_catalog"`.

---

### Task SD-10 — Design: Scenario Coverage Analysis + Automated E2E Test Harness ✅ Complete (2026-07-06, extended E2E-B1 2026-07-12)

> **Design decision**: 3-tier hybrid harness — Tier 1: `pytest`+`httpx` (every PR); Tier 2: Playwright E2E web (nightly); Tier 3: Maestro mobile (weekly). Seeding strategy: dedicated `pilot_e2e_db` reset nightly. First 5 scenarios: Auth+RBAC, Quote-to-Cash, Dispatch+Field Sync, Customer SMS, Dunning cycle.

**Tier 1 completed**: 2026-07-06

Delivered: [`docker-compose.e2e.yml`](../docker-compose.e2e.yml); `backend/.env.e2e`; [`tests/e2e/`](tests/e2e/) scaffold with `conftest_e2e.py` + `seed_e2e_db.py` + `init_e2e_schema.py`; cp1–cp5 test modules; `.github/workflows/e2e-nightly.yml` (02:00 UTC cron); `--e2e` pytest marker.

**E2E-B1 completed**: 2026-07-12

Delivered: [`migrations/scripts/seed_scenario_nec.py`](migrations/scripts/seed_scenario_nec.py) + [`migrations/scripts/seed_scenario_mobile_sync.py`](migrations/scripts/seed_scenario_mobile_sync.py); cp6 (invoice_stripe), cp7 (notifications), cp8 (nec), cp9 (mobile_sync) test modules; both new scenarios registered in `reset_dev_db.py` and wired into `seed_e2e_db.py`.

**Pending**:
- Tier 2: Playwright web browser E2E (React Engineer)
- Tier 3: Maestro mobile (future batch)

---

## 11. Reference Documents

| Document | What it covers |
|:---|:---|
| [`dev-docs/seed-data/seed-scripts-usage-reference-analysis.md`](../dev-docs/seed-data/archived/seed-scripts-usage-reference-analysis.md) | Full usage guide, all seeded data values (pricing constants, customer/job/quote details), 7-mistake post-mortem with agent recommendations |
| [`dev-docs/seed-data/seed-data-analysis-summary-v1.md`](../dev-docs/seed-data/archived/seed-data-analysis-summary-v1.md) | Current status, Phase 0.8 remediation summary, smoke test checklist, key decisions |
| [`dev-docs/seed-data/seed-data-analysis-fixes-v1.md`](../dev-docs/seed-data/archived/seed-data-analysis-fixes-v1.md) | Detailed root cause analysis for the 4 critical gaps + 5 show/inspect gaps found 2026-06-08 |
| `dev-docs/analysis/pilot-app-pre-wkstm-3-prep-plan.md` _(private)_ §0.1–0.8 | Full design history: audit of JSON vs. live DB vs. Alembic, Groups A–D model, implementation plan, Phase 0.8 completion summary |
| `dev-docs/traceability/18-seed-data-catalog.md` _(private)_ | Authoritative registry of every table requiring platform seed data for production — Alembic-level, not script-level |
| [`tests/README-adding-tests.md`](tests/README-adding-tests.md) | Test writing rules including the Seed Data Coexistence Rules section (v1.3) — mandatory reading before modifying any seed script |
| [`dev-docs/testing-support/scenario-coverage-catalog.md`](../dev-docs/testing-support/scenario-coverage-catalog.md) | SD-10 Part A deliverable — all 16 workflows, tables exercised, E2E coverage status |

---

*This README is the canonical entry point for the Pilot seed system. For design decisions and historical context, follow the reference document links above.*
