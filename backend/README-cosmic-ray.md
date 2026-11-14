# Mutation Testing with Cosmic Ray

**Tool**: [Cosmic Ray 8.4+](https://cosmic-ray.readthedocs.io/)
**Version**: 2.0
**Date**: May 30, 2026
**Python**: 3.14 compatible ✅

---

## Table of Contents

- [Mutation Testing with Cosmic Ray](#mutation-testing-with-cosmic-ray)
  - [Table of Contents](#table-of-contents)
  - [What Is Mutation Testing?](#what-is-mutation-testing)
  - [Tier \& Group Overview](#tier--group-overview)
    - [Tier 1 — Financial Correctness (~1 hr 45 min total)](#tier-1--financial-correctness-1-hr-45-min-total)
    - [Tier 2 — Security / IDOR / Tenant Isolation (~1 hr total)](#tier-2--security--idor--tenant-isolation-1-hr-total)
    - [Tier 3 — Core Workflow State Machines (~50 min total)](#tier-3--core-workflow-state-machines-50-min-total)
    - [Tier 4 — Voice AI + Integration Wiring (~3 hr 15 min total)](#tier-4--voice-ai--integration-wiring-3-hr-15-min-total)
  - [How to Run](#how-to-run)
    - [Step 1 — Activate the virtualenv](#step-1--activate-the-virtualenv)
    - [Step 2 — Run a tier script](#step-2--run-a-tier-script)
    - [Step 3 — Use the interactive menu](#step-3--use-the-interactive-menu)
  - [What You See During a Run](#what-you-see-during-a-run)
    - [Group selection (e.g. `[2]` — SMS \& Quota)](#group-selection-eg-2--sms--quota)
    - [File selection (e.g. `[11]` — billing\_rate\_service.py from G3)](#file-selection-eg-11--billing_rate_servicepy-from-g3)
  - [Session \& Report Files](#session--report-files)
  - [Reading the Report](#reading-the-report)
    - [The Key Insight: Occurrence Groups](#the-key-insight-occurrence-groups)
  - [Inspecting a Surviving Mutant](#inspecting-a-surviving-mutant)
  - [After a Run: QA Workflow](#after-a-run-qa-workflow)
    - [Step 1 — Open the report](#step-1--open-the-report)
    - [Step 2 — For each occurrence group in the report](#step-2--for-each-occurrence-group-in-the-report)
    - [Step 3 — Write the killing assertion](#step-3--write-the-killing-assertion)
    - [Step 4 — Verify the assertion kills the mutant](#step-4--verify-the-assertion-kills-the-mutant)
    - [Step 5 — Re-run to confirm score improved](#step-5--re-run-to-confirm-score-improved)
  - [QA Engineer Prompt](#qa-engineer-prompt)
  - [QA Workflow Log Files](#qa-workflow-log-files)
    - [Purpose](#purpose)
    - [Location](#location)
    - [Test File Naming Convention](#test-file-naming-convention)
    - [Naming Convention](#naming-convention)
    - [File Template](#file-template)
  - [How to Add / Remove Source Files and Tests](#how-to-add--remove-source-files-and-tests)
    - [Adding a new source file to a group](#adding-a-new-source-file-to-a-group)
    - [Adding a new group](#adding-a-new-group)
    - [Adding tests to a group](#adding-tests-to-a-group)
  - [File Layout](#file-layout)
  - [Excluded Files (Low ROI)](#excluded-files-low-roi)
  - [Understanding Result Outcomes](#understanding-result-outcomes)
  - [Priority Reference](#priority-reference)
  - [Cosmic Ray vs mutmut](#cosmic-ray-vs-mutmut)


---

## What Is Mutation Testing?

Mutation testing measures the **quality** of your test suite — not just coverage.

Traditional coverage tells you "this line was executed." It does **not** tell you whether your tests are strong enough to catch a real bug on that line.

Cosmic Ray answers the harder question: **"If I introduce a real bug into this production code, will my tests catch it?"**

Cosmic Ray works by:
1. Taking your production source code
2. Applying small targeted changes called **mutations** (flip `>` to `>=`, change `+` to `-`, invert an `if` condition, replace a constant)
3. Running your test suite against each mutated version in a **subprocess** — no in-process import issues
4. Recording which mutations your tests **killed** (caught) vs. which **survived** (slipped through)

A **survived** mutant means: "I changed the production logic, and your tests didn't notice." That is a test gap.

**We mutate production source files, not test files.** The scripts target `services/`, `api/routes/`, `tasks/`, and `core/`. This measures whether tests catch real bugs — the only measure that matters.

---

## Tier & Group Overview

Each tier is **standalone** — independent source files, independent test files. Within each tier, source files are organized into **groups** of logically related files that share the same test set.

> **Calibration**: `services/sms_quota.py` (225 lines) generated 219 mutations and completed in **11 min actual**. Rate: ~3 sec/mutation, ~20 mutations/min. Large files use ~0.5× density.

### Tier 1 — Financial Correctness (~1 hr 45 min total)

| Group | Files | Est. |
|---|---|---|
| G1 Stripe Billing | stripe_subscriptions (~11 min), stripe_payment_intents (~12 min), webhooks_stripe (~7 min) | ~30 min |
| G2 SMS & Quota | sms_quota (~11 min) | ~11 min |
| G3 Quote & Financial | quote_service (~8 min), etc_service (~7 min), billing_rate_service (~5 min) | ~20 min |
| G4 Invoices & Tax | invoices routes (~26 min), tax_calculation (~10 min), saas_billing_aggregator (~7 min) | ~45 min |

### Tier 2 — Security / IDOR / Tenant Isolation (~1 hr total)

| Group | Files | Est. |
|---|---|---|
| G1 Auth & RBAC | permissions (~14 min), db helpers (~3 min) | ~17 min |
| G2 Catalog & Models | catalog routes (~21 min), billing models (~22 min) | ~43 min |

### Tier 3 — Core Workflow State Machines (~50 min total)

| Group | Files | Est. |
|---|---|---|
| G1 Entitlement & Limits | entitlement_service (~13 min), tier_limit_enforcer (~6 min), trial_management (~9 min) | ~28 min |
| G2 Onboarding & Dispatch | tenant_signup (~10 min), notification_resolver (~9 min), quote_expiration_monitor (~4 min) | ~23 min |

### Tier 4 — Voice AI + Integration Wiring (~3 hr 15 min total)

| Group | Files | Est. |
|---|---|---|
| G1 ⚠️ Voice AI Router | voice_action_router (~75 min — ~5,200 lines!) | ~75 min |
| G2 Voice Sessions | voice_session_service (~10 min), voice routes (~14 min), voice_sessions routes (~10 min) | ~24 min |
| G3 QuickBooks | quickbooks_sync (~28 min), qb_conflict_diff (~8 min) | ~36 min |
| G4 SMS & Auth | sms_carrier (~7 min), telnyx_sms_carrier (~10 min), sms_service (~5 min), auth (~11 min) | ~33 min |
| G5 Public Links & Dunning | public_link_signer (~8 min), dunning (~7 min) | ~20 min |

> ⚠️ **Tier 4 / G1 warning**: `voice_action_router.py` at ~5,200 lines is the longest file in the codebase. Run it as a standalone file selection first to assess before running all of Group 1.

**Recommendation**: Run Tier 1 every sprint (start with individual files if ~1 hr 45 min is too long). Run Tiers 2–3 monthly. Run Tier 4 before a major release (plan for 3+ hours or run groups individually).

---

## How to Run

### Step 1 — Activate the virtualenv

```bash
cd backend
source .venv/bin/activate
```

### Step 2 — Run a tier script

```bash
bash admin_tools/cosmic-ray/run-tier-1.sh   # Financial
bash admin_tools/cosmic-ray/run-tier-2.sh   # Security / IDOR
bash admin_tools/cosmic-ray/run-tier-3.sh   # Core Workflow
bash admin_tools/cosmic-ray/run-tier-4.sh   # Voice AI + Integration
bash admin_tools/cosmic-ray/run-smoke-test.sh  # Quick verification (~3–11 min)
```

### Step 3 — Use the interactive menu

Every script shows a **3-section menu** after launch:

```
  ── GROUPS ──────────────────────────────────────────────────────
  [1] Stripe Billing           (~30 min)
  [2] SMS & Quota              (~11 min)
  [3] Quote & Financial        (~20 min)
  [4] Invoices & Tax           (~45 min)

  ── FILES ───────────────────────────────────────────────────────
  [5]  stripe_subscriptions.py    (~11 min)  (G1)
  [6]  stripe_payment_intents.py  (~12 min)  (G1)
  [7]  webhooks_stripe.py         (~7 min)   (G1)
  [8]  sms_quota.py               (~11 min)  (G2)
  [9]  quote_service.py           (~8 min)   (G3)
  [10] etc_service.py             (~7 min)   (G3)
  [11] billing_rate_service.py    (~5 min)   (G3)
  [12] invoices.py                (~26 min)  (G4)
  [13] tax_calculation.py         (~10 min)  (G4)
  [14] saas_billing_aggregator    (~7 min)   (G4)

  ── ADMIN ───────────────────────────────────────────────────────
  [A] Run All groups sequentially
  [E] Exit
```

**Groups section**: Enter a group number to run all files in that group with their shared test set.

**Files section**: Enter a file number to run just that single source file. The `(G#)` label tells you which group's test set will be used. This is the fastest way to iterate on a specific file.

**Admin section**: `[A]` runs all groups sequentially (full tier). `[E]` exits.

---

## What You See During a Run

### Group selection (e.g. `[2]` — SMS & Quota)

For a group with 1 file:
```
╔══════════════════════════════════════════════════════════════════╗
║  COSMIC RAY MUTATION TESTING                                     ║
║  Tier 1 › Group 2: SMS & Quota                                   ║
╚══════════════════════════════════════════════════════════════════╝
  Started:      2026-05-30 10:15:00
  Source files: 1
  Sessions:     admin_tools/cosmic-ray/sessions/tier-1/groups/g2-sms-quota
  Report:       .../reports/2026-05-30_10-15-00_...md

  [████████████████████████████████████████] 1/1
  File:    services/sms_quota.py
  Started: 10:15:01
  [1/3] Baseline: PASS
  [2/3] Mutants to test: 219
  [3/3] Running 219 mutations (~4 sec each) ...
  [3/3] Done — 11m 20s
  Result:  Score 59% | Killed 130 | Survived 89 | Incompetent 0 | 11m 20s

╔══════════════════════════════════════════════════════════════════╗
║  Tier 1 › Group 2: SMS & Quota COMPLETE                          ║
║  Killed: 130 | Survived: 89 | Score: 59%  | Elapsed: 11m 20s    ║
╚══════════════════════════════════════════════════════════════════╝
  Full report: .../g2-sms-quota/reports/...md
  ⚠  89 survived mutants — see report for details.
```

For a group with 3 files, the outer `[N/3]` bar advances per file, and each file gets its own 3-step block.

### File selection (e.g. `[11]` — billing_rate_service.py from G3)

Same format, header shows:
```
║  Tier 1 › File: billing_rate_service.py (G3)                    ║
```
Session saved to: `sessions/tier-1/files/f7-billing-rate-service/`

---

## Session & Report Files

Sessions are saved in `admin_tools/cosmic-ray/sessions/` with paths that reflect exactly what was run:

| Selection | Session path | Report name pattern |
|---|---|---|
| Group 2 | `sessions/tier-1/groups/g2-sms-quota/` | `YYYY-MM-DD_HH-MM-SS_tier1-group-sms-quota.md` |
| File 11 | `sessions/tier-1/files/f7-billing-rate-service/` | `YYYY-MM-DD_HH-MM-SS_tier1-file-billing-rate-service.md` |
| All groups | Each group gets its own subdirectory | One report per group |

The `sessions/` directory is **gitignored**. Session databases persist between runs so you can re-run `cr-report` any time without re-running mutations.

---

## Reading the Report

Each run generates a timestamped markdown report in the session's `reports/` subdirectory:

1. **Summary table** — Total elapsed, killed, survived, incompetent, mutation score
2. **Per-file results table** — One row per source file with individual scores
3. **Surviving Mutants section** — Grouped by occurrence number (unique source line)

### The Key Insight: Occurrence Groups

Multiple operators surviving at the **same occurrence number** all target the **same source line**. Adding one assertion that pins the correct value of that expression kills all of them simultaneously.

```
Occurrence 3 — apply to see the source line:
  .venv/bin/cosmic-ray apply services/sms_quota.py core/ReplaceBinaryOperator_Add_Sub 3

Operators that survived at this line:
- ReplaceBinaryOperator_Add_Sub
- ReplaceBinaryOperator_Add_Mul
- ReplaceBinaryOperator_Add_Div
- ReplaceBinaryOperator_Add_FloorDiv
- ReplaceBinaryOperator_Add_Mod
```

**5 surviving operators, 1 source line to fix, 1 new assertion kills all 5.**

---

## Inspecting a Surviving Mutant

```bash
cd backend

# Apply the mutation to see what code changed:
.venv/bin/cosmic-ray apply services/sms_quota.py core/ReplaceBinaryOperator_Add_Sub 3
git diff services/sms_quota.py

# Read the diff — understand what the line should produce correctly
# Write a test that asserts the EXACT correct value

# Restore the file (no unapply command — manually revert):
git restore services/sms_quota.py

# Or use the raw report to list surviving operators:
.venv/bin/cr-report admin_tools/cosmic-ray/sessions/tier-1/groups/g2-sms-quota/services_sms_quota.sqlite \
  | grep -B1 "TestOutcome.SURVIVED"
```

---

## After a Run: QA Workflow

### Step 1 — Open the report

Find the report at `admin_tools/cosmic-ray/sessions/<selection>/reports/`.

### Step 2 — For each occurrence group in the report

Apply the first operator listed, read the diff, understand what the line computes:

```bash
.venv/bin/cosmic-ray apply services/sms_quota.py core/ReplaceBinaryOperator_Add_Sub 3
git diff services/sms_quota.py
```

### Step 3 — Write the killing assertion

**Test file naming is mandatory** — use exactly one file per source file, named:
```
tests/domains/<domain>/test_<source_slug>_mutation_coverage.py
```
Examples:
- `services/sms_quota.py` → `tests/domains/subscriptions_usage/test_sms_quota_mutation_coverage.py`
- `services/stripe_subscriptions.py` → `tests/domains/invoicing_billing/test_stripe_subscriptions_mutation_coverage.py`
- `api/routes/invoices.py` → `tests/domains/invoicing_billing/test_invoices_mutation_coverage.py`
- `core/tax_calculation.py` → `tests/domains/tax_calculation/test_tax_calculation_mutation_coverage.py`

If the file already exists for this source, **add** the new test function to it. If it doesn't exist, **create** it. Never add mutation tests to any other file.

Add a test that asserts the **exact correct value** for that code path. The most common gap:

```python
# ❌ Weak — mutation survives (only checks status code):
def test_sms_quota(client, test_tenant):
    response = client.get("/api/v1/sms-quota")
    assert response.status_code == 200

# ✅ Strong — mutation killed (asserts actual values):
def test_sms_quota(client, test_tenant):
    response = client.get("/api/v1/sms-quota")
    assert response.status_code == 200
    data = response.json()
    assert data["monthly_limit"] == 100
    assert data["used"] == 0
    assert data["remaining"] == 100
```

**Arithmetic mutation example** (e.g. `year + 1` changed to `year - 1`):
```python
def test_create_initial_period_december_year_rollover(db_session):
    """December quota period end must roll over to January of NEXT year."""
    from unittest.mock import patch
    from datetime import datetime, UTC
    import services.sms_quota as quota_svc

    december_now = datetime(2026, 12, 15, tzinfo=UTC)
    with patch("services.sms_quota.datetime") as mock_dt:
        mock_dt.now.return_value = december_now
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        period = quota_svc.create_initial_period(db_session, tenant_id="test-id")

    assert period.period_end.year == 2027   # ← kills Add_Sub, Add_Mul, Add_Div, etc.
    assert period.period_end.month == 1
```

### Step 4 — Verify the assertion kills the mutant

```bash
# Restore first (if still mutated):
git restore services/sms_quota.py

# Test passes on original code:
.venv/bin/pytest tests/domains/subscriptions_usage/test_sms_quota_period.py -v

# Apply mutation and confirm test NOW fails:
.venv/bin/cosmic-ray apply services/sms_quota.py core/ReplaceBinaryOperator_Add_Sub 3
.venv/bin/pytest tests/domains/subscriptions_usage/test_sms_quota_period.py -v
# → Should FAIL ✅

# Restore:
git restore services/sms_quota.py
```

### Step 5 — Re-run to confirm score improved

**Only run this step after the user has reviewed and approved all code changes for this session.**

Do not re-run after each individual fix — wait until all occurrence groups have been addressed and all tests written. Then delete the session DB(s) for the selection and re-run the same menu choice to get an updated score:

```bash
# Example: after fixing all surviving mutants from the SMS & Quota group run
rm -f admin_tools/cosmic-ray/sessions/tier-1/groups/g2-sms-quota/services_sms_quota.sqlite
bash admin_tools/cosmic-ray/run-tier-1.sh  # select [2] SMS & Quota
```

The new score confirms how many mutants the new assertions killed.

---

## QA Engineer Prompt

Use this prompt in **Pilot QA Python Engineer** mode to automate test gap remediation from a report:

---

```
Mutation Testing — Test Gap Remediation
========================================
I have run Cosmic Ray mutation testing. The report is at:
backend/admin_tools/cosmic-ray/sessions/<selection>/reports/<report_file>.md

Reference files for this task (read before starting):
1. backend/README-cosmic-ray.md — sections: "Reading the Report", "Inspecting a
   Surviving Mutant", "After a Run: QA Workflow", "QA Workflow Log Files"
2. backend/tests/README-adding-tests.md — read the entire file

─────────────────────────────────────────────────────────────────────
STEP 0 — CREATE THE QA WORKFLOW LOG FILE (do this before any other work)
─────────────────────────────────────────────────────────────────────
a. Determine the session slug from the report path, if the report path is sessions/smoke/
    then determine the slug from the file name provided
   (e.g. sessions/tier-1/groups/g2-sms-quota → slug = tier1-group-sms-quota)
   (e.g. sessions/tier-1/files/f7-billing-rate-service → slug = tier1-files-f7-billing-rate-service)
   (e.g. sessions/smoke/reports/2026-05-29_18-51-10_Smoke Test — sms_quota.md → slug = smoke-sms-quota)

b. Create the workflow log file at:
   admin_tools/cosmic-ray/qa-workflows/YYYY-MM-DD_<slug>_qa-workflow.md

   Use today's date. The filename must match the session report slug exactly
   so the two files can always be cross-referenced.

c. Populate the INITIAL sections of the log:
   - Session Report: <path to report file>
   - Source File(s): <list from the report>
   - Mutation Score (before): <score from report>
   - Surviving Mutants: <count from report>
   - Baseline Test Count: run `.venv/bin/pytest -m unit --collect-only -q 2>/dev/null | tail -1`
     and record the number (e.g. "1,284 tests collected")
   - Baseline Pass Status: run `.venv/bin/pytest -m unit -q --tb=no 2>/dev/null | tail -1`
     and confirm all tests pass BEFORE making any changes. If any test fails,
     STOP and inform the user — do not proceed until the baseline is clean.

─────────────────────────────────────────────────────────────────────
STEP 1 — INVENTORY SURVIVING MUTANTS
─────────────────────────────────────────────────────────────────────
Read the report. Focus on "Surviving Mutants" → occurrence groups.
Each occurrence group = one source line = one fix kills all operators in the group.

For each occurrence group found, add a row to the log's "Occurrence Groups" table:
  | Occurrence | Operators (count) | Status |
  | 3          | Add_Sub, Add_Mul (6 total) | Pending |

─────────────────────────────────────────────────────────────────────
STEP 2 — PROCESS EACH OCCURRENCE GROUP (one at a time)
─────────────────────────────────────────────────────────────────────
For each unique occurrence group (working through them in order):

a. Apply the first operator to see the source line:
   .venv/bin/cosmic-ray apply <source_file> <first_operator> <occurrence>

b. Run git diff to see the exact code change.

c. Understand what the line computes correctly and what test scenario it requires.

d. Present the diff and proposed fix approach to the user for approval.

e. After user approval, restore the file:
   git restore <source_file>
   (This is the approved restore method — Cosmic Ray has no unapply command.)

f. Update the log file's "Occurrence Groups" table row to "In Progress".

g. Update the log file with the detailed analysis of this Occurrence Group.

─────────────────────────────────────────────────────────────────────
STEP 3 — WRITE THE KILLING TEST
─────────────────────────────────────────────────────────────────────
For each approved occurrence group:

a. Determine the target test file. Use EXACTLY ONE of the following rules — do not
   deviate or invent other naming:

   RULE A — If a mutation coverage file already exists for this source file:
     tests/domains/<domain>/test_<source_slug>_mutation_coverage.py
     Example: tests/domains/subscriptions_usage/test_sms_quota_mutation_coverage.py
     ADD the new test function to this existing file.

   RULE B — If no mutation coverage file exists yet for this source file:
     CREATE a new file at:
     tests/domains/<domain>/test_<source_slug>_mutation_coverage.py
     The <domain> folder is determined by the source file's PRD domain per
     tests/README-adding-tests.md. The <source_slug> is the source filename
     without the .py extension, with underscores preserved.
     Examples:
       services/sms_quota.py           → test_sms_quota_mutation_coverage.py
       services/stripe_subscriptions.py → test_stripe_subscriptions_mutation_coverage.py
       api/routes/invoices.py          → test_invoices_mutation_coverage.py
       core/tax_calculation.py         → test_tax_calculation_mutation_coverage.py

   DO NOT add mutation-coverage tests to any other existing test file.
   DO NOT create test files with any other naming pattern.
   Each source file gets exactly one mutation coverage test file — all mutation
   tests for that source file accumulate in that single file over time.

b. Write the new test function in the designated file:
   - The function name must be descriptive: test_<what_the_line_does>_<scenario>
     Example: test_create_initial_period_december_year_rollover
   - Exercises the specific code path the mutation targeted
   - Asserts the EXACT correct value — NOT just `status_code == 200`
   - The file must have pytestmark with the domain marker AND pytest.mark.unit
     (add this at the top of the file if it is a newly created file)

c. Confirm the test passes on unmodified code before continuing to the next group.

d. Update the log file row for this occurrence group:
   - Status: Complete
   - Test file: <path to test file>
   - Test function: <test function name>
   - Description: one sentence describing what the test asserts

e. Before moving to the next occurrence group, ask the user if they want you to continue.

─────────────────────────────────────────────────────────────────────
STEP 4 — FINAL VALIDATION (after ALL groups are addressed)
─────────────────────────────────────────────────────────────────────
After ALL occurrence groups are marked Complete in the log:

a. Run the FULL unit test suite and confirm everything passes:
   .venv/bin/pytest -m unit -q --tb=short 2>&1 | tail -10
   ALL tests must pass. If any fail, fix them before proceeding.
   Do NOT proceed to re-scoring if any test fails.

b. Record in the log:
   - Final Test Count: <number from pytest output>
   - Tests Added: <final count minus baseline count>
   - All Tests Pass: Yes / No (must be Yes before re-scoring)

c. Ask the user to confirm they want to re-run the mutation score.

d. On confirmation, provide the command to delete the session DB(s) and re-run:
   rm -f <session_path>/*.sqlite
   bash admin_tools/cosmic-ray/run-tier-X.sh   # user selects same option

e. After the user reports the new score, finalize the log:
   - Mutation Score (after): <new score>
   - Score Improvement: <before> → <after>  (+N percentage points)
   - Mutants Newly Killed: <count>
   - Status: COMPLETE
   - Completed: <date and time>

─────────────────────────────────────────────────────────────────────
Constraints:
─────────────────────────────────────────────────────────────────────
- Create the QA workflow log file FIRST, before any other work.
- Only fix surviving mutants from this specific report — no speculative tests.
- Do NOT modify source files except during apply/restore cycles in Step 2.
- Test file naming is MANDATORY: tests/domains/<domain>/test_<source_slug>_mutation_coverage.py
  Use RULE A (add to existing coverage file) or RULE B (create new) from Step 3.
  NEVER add mutation tests to any other file. NEVER use any other naming pattern.
- New tests go in tests/domains/ only — not legacy batch folders.
- Do NOT re-run the mutation score after each individual fix — Step 4 runs ONCE at the end.
- All tests MUST pass before re-scoring. A failing baseline or new test failure is a blocker.
- Keep the log file updated throughout the session — it is committed to git as the implementation record.
```

---

## QA Workflow Log Files

### Purpose

The `qa-workflows/` directory stores **implementation task logs** for each mutation testing remediation session. Unlike session databases (which are gitignored and ephemeral), workflow logs are **git-tracked** and serve as the permanent record of what was found, what was fixed, and what tests were added.

### Location

```
backend/
  admin_tools/cosmic-ray/
    sessions/        ← gitignored (SQLite DBs, local only)
    qa-workflows/    ← git-tracked (markdown logs, committed to repo)
      tier1-group-sms-quota/
        2026-05-30_tier1-group-sms-quota_qa-workflow.md
      tier1-file-billing-rate-service/
        2026-05-30_tier1-file-billing-rate-service_qa-workflow.md
```

> **Note**: `sessions/` is in `.gitignore`. `qa-workflows/` is NOT gitignored — these files must be committed.

### Test File Naming Convention

All mutation-coverage tests follow a strict naming convention so they can be discovered, audited, and accumulated consistently across all QA sessions:

```
tests/domains/<domain>/test_<source_slug>_mutation_coverage.py
```

| Source file | Domain | Test file |
|---|---|---|
| `services/sms_quota.py` | subscriptions_usage | `tests/domains/subscriptions_usage/test_sms_quota_mutation_coverage.py` |
| `services/stripe_subscriptions.py` | invoicing_billing | `tests/domains/invoicing_billing/test_stripe_subscriptions_mutation_coverage.py` |
| `services/billing_rate_service.py` | invoicing_billing | `tests/domains/invoicing_billing/test_billing_rate_service_mutation_coverage.py` |
| `api/routes/invoices.py` | invoicing_billing | `tests/domains/invoicing_billing/test_invoices_mutation_coverage.py` |
| `core/tax_calculation.py` | tax_calculation | `tests/domains/tax_calculation/test_tax_calculation_mutation_coverage.py` |
| `core/permissions.py` | identity_access | `tests/domains/identity_access/test_permissions_mutation_coverage.py` |
| `core/db.py` | platform_infrastructure | `tests/domains/platform_infrastructure/test_db_mutation_coverage.py` |
| `services/voice_action_router.py` | voice_ai | `tests/domains/voice_ai/test_voice_action_router_mutation_coverage.py` |

**Rules**:
- One file per source file — all mutation tests for a given source file accumulate here across multiple QA sessions
- If the file already exists, add new test functions to it; do not create a duplicate
- If the file does not exist, create it with the correct `pytestmark` header
- Never add mutation-coverage tests to any other test file
- Domain assignment follows the PRD §3 domain map in `tests/README-adding-tests.md`

### Naming Convention

```
YYYY-MM-DD_<tier>-<type>-<slug>_qa-workflow.md
```

The `<tier>-<type>-<slug>` portion must match the session directory slug exactly:
- `tier1-group-sms-quota` ← session at `sessions/tier-1/groups/g2-sms-quota/`
- `tier1-file-billing-rate-service` ← session at `sessions/tier-1/files/f7-billing-rate-service/`
- `smoke-group-billing-rate-service-t1` ← session at `sessions/smoke/groups/g1-billing-rate-service-t1/`

### File Template

```markdown
# QA Workflow Log — <Tier / Selection Label>

**Date**: YYYY-MM-DD
**Session Report**: admin_tools/cosmic-ray/sessions/<path>/reports/<report_file>.md
**Source File(s)**: services/<file>.py [, ...]
**AI Agent Mode**: Pilot QA Python Engineer

---

## Baseline (Before Changes)

| Metric | Value |
|---|---|
| Mutation Score | XX% |
| Surviving Mutants | N |
| Test Count (unit) | N,NNN collected |
| Baseline Pass Status | ✅ All passing |

---

## Occurrence Groups

| Occurrence | Operators | Count | Status | Test File | Test Function |
|---|---|---|---|---|---|
| 3 | Add_Sub, Add_Mul, Add_Div, Add_FloorDiv, Add_Mod | 5 | ✅ Complete | tests/domains/subscriptions_usage/test_sms_quota_period.py | test_create_initial_period_december_year_rollover |
| 7 | ReplaceComparisonOperator_Lt_Lte | 2 | ✅ Complete | tests/domains/subscriptions_usage/test_sms_quota_period.py | test_quota_period_boundary_exclusive |

---

## Tests Written

### Occurrence 3 — December year rollover
**Source line**: `period_end = period_start.replace(year=period_start.year + 1, month=1)`
**Mutation applied**: `year + 1` → `year - 1` (occurrence 3)
**What it means**: No test asserted that December quota periods roll over to January of the NEXT year.
**Test file**: `tests/domains/subscriptions_usage/test_sms_quota_period.py`
**Test function**: `test_create_initial_period_december_year_rollover`
**Kills operators**: Add_Sub, Add_Mul, Add_Div, Add_FloorDiv, Add_Mod (5 total)

### Occurrence 7 — Quota period boundary
...

---

## Final Validation

| Metric | Value |
|---|---|
| Test Count (unit) | N,NNN collected |
| Tests Added | +N |
| All Tests Pass | ✅ Yes |
| Mutation Score (after) | XX% |
| Score Improvement | XX% → XX% (+N points) |
| Mutants Newly Killed | N |

---

## Status: COMPLETE

**Completed**: YYYY-MM-DD HH:MM
```

---

## How to Add / Remove Source Files and Tests

Scripts are organized with **groups** and **individual files**. All definitions are at the top of each tier script — clearly separated sections.

### Adding a new source file to a group

1. Open the tier script (e.g. `run-tier-1.sh`)
2. Add the file path to the appropriate `GROUP_N_FILES=()` array
3. Add a new entry to `FILE_NAMES[]`, `FILE_TIMES[]`, `FILE_GROUP_REFS[]`
4. Add `FILE_N_SRC=` and `FILE_N_GROUP=` variables (incrementing N)
5. Update `GROUP_TIMES[]` for the affected group if the estimate changes

### Adding a new group

1. Append to `GROUP_NAMES[]` and `GROUP_TIMES[]`
2. Define `GROUP_N_FILES=()` and `GROUP_N_TESTS=()` for the new group N
3. Add individual file entries pointing `FILE_N_GROUP` to the new group number

### Adding tests to a group

Edit the `GROUP_N_TESTS=()` array for the relevant group. The test command is rebuilt automatically.

> **Note**: A source file and its tests don't have to be in the same group. Tests in a group should collectively exercise all source files in that group. A test file can appear in multiple groups if it covers files across groups.

---

## File Layout

```
backend/
  admin_tools/cosmic-ray/
    _lib.sh                       ← Shared menu, progress UI, reporting library
    run-smoke-test.sh             ← Quick verification (~3–11 min per option)
    run-tier-1.sh                 ← Tier 1: Financial Correctness
    run-tier-2.sh                 ← Tier 2: Security / IDOR
    run-tier-3.sh                 ← Tier 3: Core Workflow
    run-tier-4.sh                 ← Tier 4: Voice AI + Integration
    qa-workflows/                 ← Git-tracked; implementation logs for each QA run
      README.md                   ← Naming conventions and instructions
      2026-05-30_tier1-group-sms-quota_qa-workflow.md
      2026-05-30_tier1-file-billing-rate-service_qa-workflow.md
      ...
    sessions/                     ← Gitignored; created automatically on first run
      smoke/
        groups/
          g1-billing-rate-service-t1/
            services_billing_rate_service.sqlite
            reports/
              2026-05-30_10-00-00_smoke-group-billing-rate-service-t1.md
          g2-db-t2/
            core_db.sqlite
            reports/
              2026-05-30_10-00-00_smoke-group-db-t2.md
          g3-quote-expiry-task-t3/
            tasks_quote_expiration_monitor.sqlite
            reports/
              2026-05-30_10-00-00_smoke-group-quote-expiry-task-t3.md
          g4-dunning-task-t4/
            tasks_dunning.sqlite
            reports/
              2026-05-30_10-00-00_smoke-group-dunning-task-t4.md
        files/
          f1-billing-rate-service/
            services_billing_rate_service.sqlite
            reports/
              2026-05-30_10-00-00_smoke-file-billing-rate-service.md
          f2-db/
            core_db.sqlite
            reports/  ...
          f3-quote-expiration-monitor/
            ...
          f4-dunning/
            ...
      tier-1/
        groups/
          g1-stripe-billing/
            services_stripe_subscriptions.sqlite
            services_stripe_payment_intents.sqlite
            api_routes_webhooks_stripe.sqlite
            reports/
              2026-05-30_10-00-00_tier1-group-stripe-billing.md
          g2-sms-quota/
            services_sms_quota.sqlite
            reports/
              2026-05-30_10-00-00_tier1-group-sms-quota.md
          g3-quote-financial/
            services_quote_service.sqlite
            services_etc_service.sqlite
            services_billing_rate_service.sqlite
            reports/  ...
          g4-invoices-tax/
            api_routes_invoices.sqlite
            core_tax_calculation.sqlite
            tasks_saas_billing_aggregator.sqlite
            reports/  ...
        files/
          f1-stripe-subscriptions/     ← [5] in menu
            services_stripe_subscriptions.sqlite
            reports/  ...
          f4-sms-quota/                ← [8] in menu
            services_sms_quota.sqlite
            reports/
              2026-05-30_10-00-00_tier1-file-sms-quota.md
          f7-billing-rate-service/     ← [11] in menu
            services_billing_rate_service.sqlite
            reports/
              2026-05-30_10-00-00_tier1-file-billing-rate-service.md
          ...
      tier-2/
        groups/
          g1-auth-rbac/
            core_permissions.sqlite
            core_db.sqlite
            reports/  ...
          g2-catalog-models/
            ...
        files/
          f1-permissions/
          f2-db/
          f3-catalog/
          f4-billing/
      tier-3/
        groups/
          g1-entitlement-limits/
          g2-onboarding-dispatch/
        files/
          f1-entitlement-service/
          ...
      tier-4/
        groups/
          g1-voice-ai-router/          ← ⚠️ ~75 min, ~1,500 mutations
            services_voice_action_router.sqlite
            reports/  ...
          g2-voice-sessions/
          g3-quickbooks/
          g4-sms-auth/
          g5-public-links-dunning/
        files/
          f1-voice-action-router/      ← ⚠️ [5] in menu — run alone first
          f5-quickbooks-sync/
          f11-public-link-signer/
          f12-dunning/
          ...
```

**Session path rules**:
- Group run: `sessions/<tier>/groups/g<N>-<slug>/`
- File run: `sessions/<tier>/files/f<N>-<slug>/`
- Each selection gets its own subdirectory with SQLite DB(s) + `reports/` folder
- Report filenames: `YYYY-MM-DD_HH-MM-SS_<tier>-<type>-<slug>.md`
- The file index `f<N>` in file paths corresponds to the internal file index (not the menu number — menu numbers offset by the group count)

---

## Excluded Files (Low ROI)

Do **not** add these — mutations here have near-zero ROI:

```
migrations/versions/*          # Alembic migrations — not business logic
app/models/*.py                # SQLModel field declarations (not logic)
tests/conftest.py              # Test infrastructure
tests/phase_4/*, phase_5/*, phase_6/*  # Schema/column existence assertions
```

---

## Understanding Result Outcomes

| Outcome | Meaning | Action |
|---|---|---|
| **Killed** ✅ | Your test caught the mutation | Good — test is effective |
| **Survived** ⚠️ | Your test did NOT catch the mutation | Add an assertion that pins the correct value |
| **Incompetent** | Test subprocess errored before running | Run test command manually to diagnose |
| **Timeout** | Mutation caused infinite loop/hang | Check for missing loop guards |

---

## Priority Reference

For the full ranking of all 50 prioritized source files by business logic mutation ROI, and the domain cross-reference, see:
`dev-docs/analysis/pilot-app-be-tests-list.md` _(private)_ → Appendix A.

---

## Cosmic Ray vs mutmut

| Feature | Cosmic Ray 8.4 | mutmut v2/v3.5 |
|---|---|---|
| Python 3.14 compatible | ✅ Yes | ❌ No (pickle/numpy issues) |
| Subprocess-per-mutation | ✅ Yes | ✅ v2 / ❌ v3.5 |
| Interactive menu (Groups/Files/Admin) | ✅ Yes | ❌ No |
| Per-file / per-group selection | ✅ Yes | ❌ No |
| Grouped session paths | ✅ Yes | ❌ No |
| HTML report | ✅ Built-in | ❌ Needs plugin |
| Session persistence | ✅ SQLite | ✅ SQLite |
