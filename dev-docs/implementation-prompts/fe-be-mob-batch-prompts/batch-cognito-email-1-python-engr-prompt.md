# Implementation Prompt: COGNITO-EMAIL-1 (Part A) — Custom Email Sender Lambda + Branded Templates + Unit Tests

**Mode**: Pilot Python Engineer
**Batch**: COGNITO-EMAIL-1 (Part A of 2)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §1.1 Ord 15 + §3.15 card · §7 gate row
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-cognito-email-1-design.md` (§A–§G — read every section)
**Estimated session**: ~2 hours
**Platform**: Backend only (`backend/lambda/` + `backend/tests/`)
**DevOps companion**: Part B (`batch-cognito-email-1-devops-prompt.md`) — runs **after** this batch; needs your handler merged to build/deploy the package

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document (test structure, domain markers, fixtures)
- **`dev-docs/architecture-design/batch-designs/batch-cognito-email-1-design.md`** — §F (event contract + module interfaces) and §G (resolved decisions) are binding

Critical rules for this batch:

- **Rule 11**: If ANY test fails during your work — even a pre-existing one — fix it before declaring done. No "not my fault" exception.
- **Rule 14 (Ruff)**: changed files only (`git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||'`), fix ALL errors in those files, no unjustified `# noqa`.
- **Rule 5**: Never module-level `TestClient`. (This batch has no routes, but your tests live in the suite — follow `README-adding-tests.md`.)
- **Rule 1/16 (verify, don't assume)**: This batch writes **zero SQL** — the Lambda has no DB access by design (design §B). The one external contract you must verify instead: the **AWS Custom Email Sender doc page** (see Pre-Work reads) for exact `triggerSource` strings and the KMS decrypt `EncryptionContext` key casing (design §G.6).
- **Batch invariant (design §G.4) — RETHROW, never swallow**: this Lambda IS the email delivery path. Unlike our passive hooks (post-confirmation/post-authentication, which must never raise), a swallowed failure here = user never gets their code and Cognito thinks it sent. Structured log + **raise** on every failure path (KMS error, SendGrid non-202, unknown `triggerSource`).
- **Package discipline**: the Lambda package is **self-contained** — no `app.*` / `core.*` / `services.*` imports, no DB, no FastAPI. Only stdlib + `sendgrid` (packaged) + lazily-imported `boto3` (runtime-provided, never packaged). This keeps the auth path independent of RDS and the zip tiny.

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count (TEAM-INVITE-1 close: **4786 passed**). Must still pass at the end (plus your new tests). Any pre-existing failure → confirm with Tom before proceeding.

## Pre-Work: MCP Verification Queries

> **MCP Usage Rule**: `postgres-local` MCP is **read-only verification only** — never INSERT/UPDATE/DELETE. On any error → STOP and ask Tom. Two servers exist (`postgres-local` default; `postgres-prod` only via Tom's SSH tunnel — not used in this batch).

This batch touches **zero DB objects** (no migrations, no models, no SQL — design §B), so the standard 2–5 schema queries are deliberately reduced to one drift tripwire (architect-noted deviation: batch-specific, not filler):

```sql
-- 1. Alembic head drift tripwire — expect 3da9abdfb2f2 (TEAM-INVITE-1 head).
--    If it differs, record the current value and note it in your Completion Summary.
SELECT version_num FROM public.alembic_version;
```

## Pre-Work: Read These Source Files

Use `read_file` on each before writing any code:

```
backend/lambda/post_authentication/handler.py          ← resource-resolution pattern (env → Secrets Manager ARN, lazy boto3), never-raise passive-hook docstring (contrast: YOU raise — design §G.4)
backend/lambda/post_confirmation/handler.py            ← package layout convention (backend/lambda/<name>/handler.py + __init__.py)
backend/services/email_service.py                      ← house SendGrid pattern (Mail construction, FROM tuple, 202 = accepted)
backend/core/config.py (lines ~55–70)                  ← SENDGRID_FROM_EMAIL / SENDGRID_FROM_NAME values
backend/tests/domains/identity_access/test_post_authentication_handler.py  ← importlib Lambda-test pattern + module-level resource monkeypatching
backend/tests/domains/identity_access/test_post_confirmation_router.py     ← second reference for the importlib pattern
backend/migrations/scripts/data/email_templates/team_invite.json           ← brand tokens to mirror (Arial stack, #5B3FF0)
infrastructure/scripts/build-post-authentication-lambda.sh                 ← packaging awareness (Part B mirrors it; your handler must stay dependency-minimal)
dev-docs/architecture-design/batch-designs/batch-cognito-email-1-design.md ← §F event contract + §G decisions
```

**External contract read (mandatory)**: AWS doc — *Custom email sender Lambda trigger* (`https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-lambda-custom-email-sender.html`). Verify before implementing: (a) the six `triggerSource` strings, (b) the KMS decrypt `EncryptionContext` keys (design §G.6 expects `userpool-id` + `client-id` — confirm exact casing), (c) the response contract (return the event). If the doc disagrees with the design → follow the doc and note the divergence in your Completion Summary.

## Background / Context

The prod user pool sends auth emails via `COGNITO_DEFAULT`: 50 emails/day cap, no DKIM/SPF control, spam placement, unbranded — it failed one of the author's own test signups on 2026-08-25, and every TEAM-INVITE employee invite in testing arrives unbranded. This batch builds the Lambda that Cognito invokes instead (Custom Email Sender trigger, `V1_0`): KMS-decrypt the code → render a branded template → send via SendGrid. Part B (DevOps) packages, deploys, wires the trigger, and smokes. You build only the Python package + tests — no Terraform, no AWS calls.

## Task 1 — `backend/lambda/custom_email_sender/` package

Create `__init__.py` (empty, mirrors siblings) and `handler.py` implementing design §F exactly:

- **`handler(event, context) -> dict`**: route on `event["triggerSource"]`:
  - `CustomEmailSender_SignUp`, `CustomEmailSender_ResendCode`, `CustomEmailSender_VerifyUserAttribute`, `CustomEmailSender_UpdateUserAttribute` → flow `verification_code`
  - `CustomEmailSender_ForgotPassword` → flow `forgot_password`
  - `CustomEmailSender_AdminCreateUser` → flow `admin_invite`
  - anything else → structured log + `raise` (§G.4)
  - Extract email from `event["request"]["userAttributes"]["email"]`; missing/empty → log + raise. Decrypt → render → send → `return event`.
- **`_decrypt_code(event) -> str`**: base64-decode `event["request"]["code"]` → `kms.decrypt(CiphertextBlob=…, EncryptionContext={<verified per the AWS doc>})`. KMS client via a lazy `_get_kms_client()` (boto3 import **inside** the function — tests monkeypatch the factory).
- **`_resolve_sendgrid_key() -> str`**: `os.environ["SENDGRID_API_KEY"]` if set (local/tests) → else `SENDGRID_SECRET_ARN` → boto3 Secrets Manager (lazy import), JSON key `SENDGRID_API_KEY` (verified in env-mgmt line 79). Never log the key.
- **`_send(to_email, rendered) -> None`**: `SendGridAPIClient(key)`; `Mail(from_email=("noreply@pilotfortrades.com", "Pilot for Trades"), to_emails=to_email, subject=…, plain_text_content=…, html_content=…)`; **click + open tracking disabled** on the Mail object (§G.5 — auth links must not be wrapped); `response.status_code == 202` required — anything else → log body + raise.
- Docstring header: batch, design link, the §G.4 raise-vs-swallow rationale, and the packaging note (sendgrid packaged; boto3 runtime-provided, lazy).

## Task 2 — `templates.py` (same package)

Three flows × (HTML + plaintext), per design §F/§G.5:

- Inline styles only; Arial stack; brand `#5B3FF0`; the **code rendered large** (≥28 px, letter-spaced, monospace-friendly); expiry hint ("This code expires shortly."); no external images; only link is the `https://pilotfortrades.com` footer.
- `verification_code` — subject `Your Pilot for Trades verification code`.
- `forgot_password` — subject `Reset your Pilot for Trades password` (+ "If you didn't request this, ignore this email." line).
- `admin_invite` — subject `You've been invited to Pilot for Trades` (code = temporary password; "sign in and set a new password" guidance). Not exercised by current flows — future-proofing per design §G.5.
- `_render(flow, code, email) -> RenderedEmail` dataclass `(subject, html, text)`; plaintext twins carry the same code + one-line guidance.

## Task 3 — Tests

Create `backend/tests/domains/identity_access/test_custom_email_sender_handler.py`:

```python
pytestmark = [
    pytest.mark.domain_identity_access,
    pytest.mark.unit,
]
```

- Import via `importlib.import_module("lambda.custom_email_sender.handler")` (house Lambda pattern). `monkeypatch.setenv("SENDGRID_API_KEY", "SG.test-key")` so tests never touch Secrets Manager; monkeypatch the module's KMS client factory (decrypt → returns a known code, e.g. `"123456"`); mock `SendGridAPIClient` (capture the `Mail` argument; `.send()` returns an object with `status_code = 202`).
- **Per-flow coverage** (one parametrized set over the four verification trigger sources + one each for forgot-password + admin-invite): correct subject; the decrypted code appears in BOTH html and plaintext; FROM is `noreply@pilotfortrades.com`; click/open tracking disabled on the Mail object; sendgrid `.send()` called exactly once; handler returns the event.
- **Decrypt contract**: `kms.decrypt` called with the verified `EncryptionContext` (`userpool-id` = event's pool id, `client-id` = event's client id) and the base64-decoded blob.
- **Raise paths (§G.4)**: KMS `ClientError` → raises; SendGrid response `status_code = 400` → raises; unknown `triggerSource` → raises; missing email attribute → raises.
- Event fixtures via a small `_event(trigger_source, email=..., code_b64=...)` builder (base64 of any bytes — KMS is mocked). No DB fixtures needed — do not use `db_session` here.
- After adding the test file, regenerate the import map: `python generate_app_import_map.py tests > app_model_imports.md`.

## Verification Checkpoints

After Task 1+2: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5` (suite still green).
After Task 3: `python -m pytest tests/domains/identity_access/test_custom_email_sender_handler.py -v 2>&1 | tail -25`.

## Regeneration + Schema Steps

**None.** No endpoints (`export_openapi_json.py` N/A), no models (`generate_db_model_map.py` N/A), no schema (`schema_manager.py` N/A). Only `generate_app_import_map.py tests > app_model_imports.md` (new test file — Task 3).

## Final Verification

### Phase 1 — Unit Tests Only

```bash
cd <repo>/backend && source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

### Phase 2 — Lint (changed files only) + Full Suite, Vendor-Deselected

```bash
cd <repo>/backend && source .venv/bin/activate

CHANGED_PY=$(git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||')
if [ -n "$CHANGED_PY" ]; then
    ruff check --fix $CHANGED_PY && ruff format $CHANGED_PY && ruff check $CHANGED_PY
fi

python -m pytest -m "not integration and not requires_telnyx and not requires_stripe and not requires_sendgrid and not requires_redis and not e2e" --tb=short -q 2>&1 | tail -15

python -m pytest tests/domains/identity_access/ -v 2>&1 | tail -30
echo "=== COGNITO-EMAIL-1 PART A FINAL VERIFICATION COMPLETE ==="
```

> **Vendor-suite inclusion call (explicit)**: this batch is SendGrid-*adjacent* but the handler is fully unit-mocked — the `requires_sendgrid` vendor suite is **NOT** run (no changed code it covers; the live SendGrid proof is Part B's Gmail smoke, design §G.9).

## Definition of Done

- [ ] Pre-modification regression baseline captured (4786 passed — or confirmed with Tom)
- [ ] MCP tripwire query run — alembic head recorded (`3da9abdfb2f2` or drift noted)
- [ ] All mandatory source files + the AWS Custom Email Sender doc page read
- [ ] `backend/lambda/custom_email_sender/__init__.py` + `handler.py` created — trigger routing per design §F; **raise on every failure path (§G.4)**; lazy boto3; no `app.*`/`core.*`/`services.*` imports
- [ ] `templates.py` created — 3 flows × HTML+plaintext; brand tokens; code prominent; tracking-free; FROM constants match config
- [ ] KMS decrypt uses the doc-verified `EncryptionContext` keys
- [ ] `test_custom_email_sender_handler.py` created — per-flow, decrypt-context, and all four raise paths covered; `pytestmark` domain + unit; importlib pattern
- [ ] `python generate_app_import_map.py tests > app_model_imports.md` run
- [ ] No OpenAPI/model/schema regeneration needed (verified N/A)
- [ ] `ruff check --fix && ruff format` on changed files only — zero remaining issues
- [ ] **Phase 1**: unit suite green
- [ ] **Phase 2**: full vendor-deselected suite green; vendor-suite inclusion call recorded
- [ ] Final test count (before → after) documented
- [ ] Completion Summary filled in at this prompt doc's ending `## Appendix — Completion Summary` (ADR-0017)

## Handoff (Part B gate — do NOT start DevOps work)

When DoD is complete: commit, and notify that Part A is done. Part B (DevOps) builds the deployment package from `backend/lambda/custom_email_sender/`, so the handler must be merged first. In your handoff note, state: the exact `DEPS` your handler needs at runtime (`sendgrid==6.11.0` — boto3 is runtime-provided and must NOT be packaged), and the env var names (`SENDGRID_API_KEY` local-override, `SENDGRID_SECRET_ARN`).

## Completion Summary

After all Definition of Done items are complete, fill in the appendix below (ADR-0017). Format: Completed date / Mode / Baseline / Final counts · What Was Accomplished · Files Changed|Created table · Tests Added table.

---

## Appendix — Completion Summary

**Completed**: 2026-09-03
**Mode**: Pilot Python Engineer
**Batch**: COGNITO-EMAIL-1 (Part A of 2)
**ADR**: ADR-0017

### Baseline → Final Counts

| Phase | Passed | Skipped | Deselected |
|---|---|---|---|
| Pre-Work baseline (unit) | 4787 | 1 | 96 |
| Phase 1 (unit) | 4829 | 1 | 96 |
| Phase 2 (vendor-deselected full) | 4829 | 1 | 96 |
| identity_access domain (verbose) | 139 | 0 | — |

- **Delta**: +42 new tests (all in `test_custom_email_sender_handler.py`).
- **No pre-existing failures** encountered or introduced.
- **Alembic head**: `3da9abdfb2f2` (matches TEAM-INVITE-1 — no drift).
- **Vendor-suite inclusion call**: `requires_sendgrid` NOT run — the handler is fully unit-mocked; the live SendGrid proof is Part B's Gmail smoke (design §G.9).

### What Was Accomplished

Built the self-contained Cognito Custom Email Sender Lambda package (`backend/lambda/custom_email_sender/`) that Cognito invokes instead of `COGNITO_DEFAULT` for auth emails. The handler: routes on `triggerSource` → one of three template flows; KMS-decrypts the code; renders a branded template; sends via SendGrid with click/open tracking disabled; returns the event. Implements the §G.4 **rethrow-on-failure** invariant (opposite of the passive post-auth/post-confirmation hooks) — every failure path (KMS error, SendGrid non-202, unknown triggerSource, missing email) raises so Cognito surfaces a clean failure and the CloudWatch alarm fires.

**Package discipline**: no `app.*`/`core.*`/`services.*` imports, no DB, no FastAPI. Only stdlib + `sendgrid` (packaged by Part B) + lazily-imported `boto3` (runtime-provided, never packaged). Dual-mode import (`from .templates import render` / `from templates import render`) supports both the test package context and the flat Lambda zip layout.

**AWS doc verification**: confirmed the six `triggerSource` strings and the KMS decrypt `EncryptionContext` keys (`userpool-id`, `client-id` — lowercase hyphenated) against the AWS Custom Email Sender doc page. Design §G.6 is correct — no divergence.

### Files Changed | Created

| File | Action | Purpose |
|---|---|---|
| `backend/lambda/custom_email_sender/__init__.py` | Created | Empty package init (mirrors siblings) |
| `backend/lambda/custom_email_sender/handler.py` | Created | Lambda handler: trigger routing, KMS decrypt, SendGrid send, §G.4 raise invariant |
| `backend/lambda/custom_email_sender/templates.py` | Created | 3 flows × HTML+plaintext; brand tokens; code prominent ≥28px; tracking-free |
| `backend/tests/domains/identity_access/test_custom_email_sender_handler.py` | Created | 42 tests: per-flow, decrypt-contract, 4 raise paths |
| `backend/pyproject.toml` | Modified | Added N999 exemption for `lambda/custom_email_sender/__init__.py` |
| `backend/app_model_imports.md` | Regenerated | New test file import map |

### Tests Added

| Test Class | Count | Coverage |
|---|---|---|
| `TestPerFlow` (parametrized × 6 trigger sources) | 36 | subject, code-in-html+plaintext, FROM address, tracking disabled, send called once, returns event |
| `TestDecryptContract` | 1 | kms.decrypt called with verified EncryptionContext + base64-decoded blob |
| `TestRaisePaths` | 5 | KMS ClientError, SendGrid non-202, unknown triggerSource, missing email, empty email |
| **Total** | **42** | |

### Handoff to Part B (DevOps)

- **Runtime DEPS**: `sendgrid==6.11.0` (packaged). `boto3`/`botocore` are runtime-provided — must NOT be packaged.
- **Env vars**: `SENDGRID_API_KEY` (local/tests override), `SENDGRID_SECRET_ARN` (prod: ARN of `pilot/prod/sendgrid` secret, JSON key `SENDGRID_API_KEY`).
- **Handler entry point**: `handler.handler` (module=handler, func=handler).
- **Build script**: Part B mirrors `build-post-authentication-lambda.sh` — pip cross-install `sendgrid==6.11.0` manylinux cp312 wheels → `build/custom_email_sender/` → copy `handler.py` + `templates.py` to build root → TF `data.archive_file`.
- **No app/models tree needed** — this handler has no DB imports (unlike post-auth/post-confirmation).
