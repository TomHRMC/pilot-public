# Implementation Prompt: DLC-B4 — "Pilot for Trades:" SMS Brand Prefix (10DLC Resubmission Unblocker)

**Mode**: Pilot Python Engineer
**Batch**: DLC-B4
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.0 #9 (DLC-B2 follow-on)
**Related record**: `dev-docs/integrations/telnyx/telnyx-10dlc-customer-comms-campaign.md` §16 (rejection & resubmission record)
**Estimated session**: 2–3 hours
**Platform**: Backend only (`backend/`)
**Frontend companion**: None

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; governs test structure, domain markers, fixtures
- **`backend/README-seed-data.md`** — the seed data model; `communication_template` rows are seeded here

Critical rules for this batch:

- **Rule 1**: Never guess column/table names. The Architect verified the schema via MCP (see Pre-Work) — but re-run the column query yourself before writing SQL. If MCP errors → STOP and ask Tom.
- **Rule 4**: Alembic migrations are **blank** (`alembic revision -m "..."`), never `--autogenerate`. Data changes use raw `op.execute()` with `SET LOCAL session_replication_role = 'replica';` at the top of `upgrade()`.
- **Rule 5**: Never module-level `TestClient` — use the `client` fixture.
- **Rule 11**: If ANY test fails during your work — even one that looks pre-existing — fix it before declaring done, or STOP and ask Tom.

---

## Background / Context — Why This Batch Exists (Do Not Re-Litigate)

The 10DLC customer-comms campaign (`CXXXXXX`) was rejected (`TELNYX_FAILED`, 2026-07-27). Per Telnyx compliance guidance, single-brand B2B2C is allowed, but **the platform brand must be the perceived sender**. The reviewer flagged that outbound messages identify only the contractor. The fix: **every customer-facing SMS must lead with the literal prefix `Pilot for Trades: `**.

Because the campaign's §8 rule requires submitted sample/auto-reply text to **exactly match what the code sends** (mismatch = MNO review failure, error 806), this is a backend change, not just a portal edit. **This batch is the prerequisite that unblocks campaign resubmission** — see `telnyx-10dlc-customer-comms-campaign.md §16`.

### Exact scope (verified via MCP by the Architect, 2026-07-27)

**A. 11 system SMS templates** in `communication_template` (`channel = 'sms'`, all `tenant_id IS NULL`, all `is_active = true`). Each `body_template` must be prefixed with `Pilot for Trades: `:

| `template_code` | Current `body_template` (start) |
|---|---|
| `appointment_reminder_1h` | `{{tenant_name}} is on the way — arriving around {{appointment_time}}...` |
| `appointment_reminder_24h` | `Reminder: {{tenant_name}} appointment tomorrow at {{appointment_time}}...` |
| `arrived` | `Hi {{ customer_first_name }}, {{ sender_name }} here — I've arrived...` |
| `confirm_appointment` | `Hi {{ customer_first_name }}, please confirm your appointment for {{ date_time }}...` |
| `invoice_sent` | `Your invoice is ready. View and pay at {{invoice_link}}...` |
| `job_complete` | `Hi {{ customer_first_name }}, {{ sender_name }} here — work is complete...` |
| `on_my_way` | `Hi {{ customer_first_name }}, this is {{ sender_name }} — I'm on my way, ETA {{ eta }}...` |
| `parts_delay` | `Hi {{ customer_first_name }}, {{ sender_name }} here — there's a parts delay...` |
| `payment_received` | `Payment received — thank you! {{tenant_name}} has processed...` |
| `recurring_job_scheduled` | `Hi {{customer_name}}, your scheduled {{service_description}} with {{company_name}}...` |
| `running_late` | `Hi {{ customer_first_name }}, {{ sender_name }} here — running about {{ minutes_late }} minutes behind...` |

**B. The double opt-in confirmation string** in code — `sms_compliance.py` — must also be prefixed. It is the FIRST message the consumer receives, so it's the most important sender-identification point.

**Target result for each:** `Pilot for Trades: ` + existing body. Example — `appointment_reminder_24h` becomes:
> `Pilot for Trades: Reminder: {{tenant_name}} appointment tomorrow at {{appointment_time}}. Reply STOP to opt out.`

### Out of scope (do NOT touch)

- **Auto-reply strings** (STOP/START/HELP) in `customer_communication_threading.py` — they **already** contain "Pilot for Trades" (DLC-B2). Leave them exactly as-is.
- **Email templates** — the rejection is SMS-only. Do NOT prefix any `channel = 'email'` template.
- **Tenant-authored templates** — all current SMS rows are system (`tenant_id IS NULL`). The migration must scope to `tenant_id IS NULL` so a future tenant override is never rewritten.

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record `X passed, Y failed`. Zero pre-existing failures, or confirm with Tom before starting.

## Pre-Work: Run MCP Verification Queries

> **MCP Usage Rule**: `postgres-local` is **read-only verification only**. Never INSERT/UPDATE/DELETE via MCP — all data changes go through the Alembic migration. If a query errors → STOP and ask Tom.

```sql
-- 1. Confirm columns (must show template_code, body_template, channel, is_active, tenant_id)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'communication_template'
ORDER BY ordinal_position;

-- 2. Enumerate the exact SMS rows this batch will modify (expect 11, all tenant_id IS NULL)
SELECT template_code, tenant_id, is_active, body_template
FROM public.communication_template
WHERE channel = 'sms'
ORDER BY template_code;

-- 3. Idempotency guard check — how many SMS rows are ALREADY prefixed (expect 0 before this batch)
SELECT count(*) AS already_prefixed
FROM public.communication_template
WHERE channel = 'sms' AND body_template LIKE 'Pilot for Trades:%';

-- 4. Safety — confirm NO tenant-authored SMS templates exist that we'd accidentally hit
SELECT count(*) AS tenant_authored_sms
FROM public.communication_template
WHERE channel = 'sms' AND tenant_id IS NOT NULL;
```

> If query #2 returns a different set than the 11 codes in the table above (new templates added since 2026-07-27), **prefix those too** — the rule is "every active `channel='sms'` system template." Note any additions in your Completion Summary. If query #4 returns > 0 → STOP and ask Tom before scoping the migration (a tenant override changes the WHERE clause).

## Pre-Work: Read These Source Files

```
backend/migrations/scripts/seed_core.py                  ← the SMS template seed block (~line 1081); source of truth for fresh DBs — MUST be updated so re-seeds carry the prefix
backend/migrations/versions/2026_05_31_2216-5ec7fe1e46d8_seed_communication_template_gap_fill.py  ← pattern reference for a template-seed migration (idempotent INSERT/UPDATE style)
backend/tasks/sms_compliance.py                          ← line 26: the double opt-in confirmation string (Python literal, not DB)
backend/tests/README-adding-tests.md                     ← test structure + domain markers
```

Find every place a customer-facing SMS body is defined or asserted:

```bash
grep -rn "Reply STOP to opt out\|appointment tomorrow\|on my way\|invoice is ready" backend/ --include="*.py"
grep -rn "Pilot for Trades" backend/tasks/sms_compliance.py backend/migrations/scripts/seed_core.py
```

---

## Task 1 — Update the seed source of truth (`seed_core.py`)

In `seed_core.py` (SMS template block, ~line 1081), prepend `Pilot for Trades: ` to the `body_template` of **every** `channel='sms'` template in the seed definitions (all 11 codes above). This ensures any fresh DB re-seed produces prefixed templates.

> Read the block first. Match the exact quoting/escaping style already used (note `invoice_sent` uses `{{invoice_link}}` — keep the double-brace variables intact; only prepend the literal prefix before the first character).

Do NOT touch the `channel='email'` templates in the same block.

Intermediate check:
```bash
grep -n "Pilot for Trades: " backend/migrations/scripts/seed_core.py | wc -l   # expect ≥ 11 new SMS lines
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

---

## Task 2 — Write an idempotent Alembic migration to update EXISTING prod rows

`seed_core.py` only affects fresh seeds. Production already has the 11 unprefixed rows, so an Alembic data migration must update them in place.

Create a **blank** migration:
```bash
cd <repo>/backend && source .venv/bin/activate
alembic revision -m "dlc_b4_sms_brand_prefix"
```

`upgrade()` — idempotent, value-scoped, system-templates-only:
```python
def upgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.execute("""
        UPDATE public.communication_template
        SET body_template = 'Pilot for Trades: ' || body_template
        WHERE channel = 'sms'
          AND tenant_id IS NULL
          AND body_template NOT LIKE 'Pilot for Trades:%';
    """)
```

`downgrade()` — exact reverse (strip the prefix only where present):
```python
def downgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.execute("""
        UPDATE public.communication_template
        SET body_template = substring(body_template FROM length('Pilot for Trades: ') + 1)
        WHERE channel = 'sms'
          AND tenant_id IS NULL
          AND body_template LIKE 'Pilot for Trades:%';
    """)
```

> **Why `NOT LIKE 'Pilot for Trades:%'`**: idempotency — re-running upgrade must not double-prefix. **Why `tenant_id IS NULL`**: never rewrite a tenant-authored override (confirmed 0 today, but future-proof). This mirrors the seed-safety DELETE-scoping principle in `README-seed-data.md`.

Test the full cycle:
```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
alembic current
```

After `upgrade head`, re-run MCP query #2 (read-only) to eyeball that all 11 rows now start with `Pilot for Trades: ` and variables are intact.

Intermediate check:
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

---

## Task 3 — Prefix the double opt-in confirmation string

In `sms_compliance.py`, prepend `Pilot for Trades: ` to the confirmation message so it becomes:
> `Pilot for Trades: Hi {first_name}, {business_name} uses Pilot for Trades for service updates. Reply YES to confirm you want to receive texts. Msg freq varies. Msg & data rates may apply. Reply HELP for help, STOP to cancel.`

> Read the surrounding function first — match the exact f-string/format style. Only prepend the literal prefix; leave all `{first_name}` / `{business_name}` placeholders and existing disclosures unchanged. (Yes, "Pilot for Trades" now appears twice — that's intentional and correct: the leading prefix is the sender ID, the inline mention is the program description.)

Intermediate check:
```bash
grep -n "Pilot for Trades: Hi" backend/tasks/sms_compliance.py
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

---

## Task 4 — Tests

Per `README-adding-tests.md`, add tests under `tests/domains/notifications_comms/` (per the domain-folder mapping for notifications/comms/SMS). File header:

```python
pytestmark = [
    pytest.mark.domain_notifications_comms,
    pytest.mark.unit,
]
```

Required cases (scope by `template_code`, never by total row count):

1. **All 11 system SMS templates are prefixed** — query each of the 11 `template_code`s (channel='sms', tenant_id IS NULL) via the `db_session` fixture; assert each `body_template` starts with `"Pilot for Trades: "`. Assert the original variable(s) still present (e.g. `invoice_sent` still contains `{{invoice_link}}`).
2. **Migration idempotency** — running the upgrade UPDATE twice does not double-prefix (assert no row starts with `"Pilot for Trades: Pilot for Trades:"`). Test the SQL condition, not `.delay()`.
3. **Email templates untouched** — pick a known `channel='email'` template and assert it does NOT start with the prefix.
4. **Double opt-in string prefixed** — assert the string emitted by the `sms_compliance` confirmation builder starts with `"Pilot for Trades: "` and still contains the `{first_name}` / `{business_name}` placeholders (test the string/template, not a live send). Read `sms_compliance.py` for the correct function to import.

> Use `test_tenant` / `db_session` fixtures; no hardcoded UUIDs. These are system templates (`tenant_id IS NULL`) — query by `template_code`, and note seed data is always present so never assert on total counts.

Update any existing test that asserts an old (unprefixed) SMS body — search first:
```bash
grep -rn "appointment tomorrow\|on my way\|invoice is ready\|is on the way" backend/tests/ --include="*.py"
```
Fix each to expect the prefixed form (Rule 11 — no "pre-existing" pass-through).

---

## Task 5 — Reconcile the campaign playbook samples (doc, not code)

The §6 samples in `telnyx-10dlc-customer-comms-campaign.md` must exactly match the rendered prefixed templates (§8 code↔portal match rule). Verify each §6 sample equals `Pilot for Trades: ` + the rendered template body. **If any mismatch exists** (e.g. a sample dropped a word like "Reminder:" that the real template contains), note it in your Completion Summary and flag it to Tom/Architect so the doc is corrected before resubmission — do not edit the sample to hide a real template difference; the portal sample must reflect what the code actually sends.

---

## Final Verification

### Phase 1 — Unit only (during development)
```bash
cd <repo>/backend && source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

### Phase 2 — Full suite (once, before sign-off)
```bash
cd <repo>/backend && source .venv/bin/activate
python -m pytest --tb=short -q 2>&1 | tail -10
python -m pytest tests/domains/notifications_comms/ -v 2>&1 | tail -25
echo "=== DLC-B4 FINAL VERIFICATION COMPLETE ==="
```

> Any failure in either phase must be fixed before done — no "pre-existing" exception without Tom's written confirmation.

---

## Definition of Done — DLC-B4

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`, `pytest -m unit`)
- [ ] MCP queries run — 11 SMS rows confirmed (or delta noted); query #4 tenant-authored SMS = 0 (or Tom sign-off)
- [ ] All mandatory source files read
- [ ] **Task 1**: `seed_core.py` SMS block — all 11 `body_template`s prefixed; email templates untouched
- [ ] **Task 2**: idempotent Alembic migration created; upgrade/downgrade/upgrade cycle verified; MCP re-check shows all 11 prefixed, variables intact
- [ ] **Task 3**: double opt-in string in `sms_compliance.py` prefixed; placeholders intact
- [ ] **Task 4**: tests added under `tests/domains/notifications_comms/` (prefix present ×11, idempotency, email untouched, double opt-in); existing SMS-body assertions updated
- [ ] **Task 5**: §6 playbook samples reconciled to rendered templates; any mismatch flagged to Tom
- [ ] All new tests use `pytestmark` domain marker + `pytest.mark.unit`; `client`/`db_session` fixtures; no hardcoded UUIDs
- [ ] **Phase 1**: all unit tests pass (zero failures)
- [ ] **Phase 2**: full suite passes (zero failures, incl. integration)
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to `pilot-launch-plan.md` Appendix B
- [ ] `telnyx-10dlc-customer-comms-campaign.md §16` rev-2 checklist item "DLC-B4 shipped" marked ✅
- [ ] Handoff note: campaign resubmission is now unblocked (Tom: resubmit rev 2 with §4 disclosure + §6/§8 prefixed samples)

---

## Completion Summary

Add a Completion Summary to `pilot-launch-plan.md` Appendix B:

```markdown
### DLC-B4 — "Pilot for Trades:" SMS Brand Prefix: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished
- Prefixed all 11 system SMS templates + the double opt-in confirmation with "Pilot for Trades: " so the platform is the perceived sender (10DLC campaign CXXXXXX rejection fix #2).
- Idempotent, tenant_id-IS-NULL-scoped Alembic migration updated existing prod rows; seed_core.py updated for fresh seeds.
- Unblocks 10DLC customer-comms campaign resubmission (rev 2).

#### Files Changed / Created
| File | Action |
|---|---|
| `backend/migrations/scripts/seed_core.py` | Updated — 11 SMS templates prefixed |
| `backend/migrations/versions/..._dlc_b4_sms_brand_prefix.py` | Created — idempotent prod data migration |
| `backend/tasks/sms_compliance.py` | Updated — double opt-in string prefixed |
| `backend/tests/domains/notifications_comms/test_dlc_b4_sms_prefix.py` | Created |

#### Tests Added
| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/notifications_comms/test_dlc_b4_sms_prefix.py` | `notifications_comms` | N | ✅ |
```
