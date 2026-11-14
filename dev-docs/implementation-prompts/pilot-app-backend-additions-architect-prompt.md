# Batch Design Session Prompt — Pilot Architect Mode

**Usage**: Open a new chat in `🏗️ Pilot Architect` mode. Replace `{N}` and `{Batch Name}` with the target batch. Paste this prompt verbatim.

**Prerequisite**: Confirm all prerequisite batches for B{N} are marked ✅ COMPLETE in §7 of the impl plan before starting.

---

```
Design session for Batch B{N} — {Batch Name}.

Before producing the design doc, complete all input reads below in full. Do not begin writing the design doc until all reads are done.

READ 1 — BATCH PLAN:
Read Section §6.B{N} of dev-docs/analysis/pilot-app-mvp-backend-impl-plan.md in full.

READ 2 — ADDITIONS LEDGER:
Read dev-docs/architecture-design/frontend-pass-1-4/frontend-backend-mvp-additions-latest.md.
Find and read every ANN entry that appears in this batch's item list. The batch section in the impl plan is a summary — the ledger has the authoritative detail.

READ 3 — ARCHITECTURE REFERENCE:
Read dev-docs/architecture-design/mvp-arch.md.
Identify which existing patterns (SSE, notification_outbox, voice_action_router, etc.) this batch extends or reuses.

READ 4 — PYTHON ENGINEER METHODS:
Read dev-docs/architecture-design/pilot-python-engineer-methods.md.
Identify which §16+ patterns apply to items in this batch (staleness check, confirm-as-turn, carrier-agnostic adapter, three-tier resolver, etc.). Note the exact section numbers for each.

READ 5 — LIVE DATABASE SCHEMA:
Use the postgres-local MCP to query the exact column shapes for every table this batch touches or extends. Do not guess column names or types. For each new column the design will add, verify it does not already exist before listing it in the migration plan. Example query pattern:
  SELECT column_name, data_type, is_nullable, column_default
  FROM information_schema.columns
  WHERE table_name = 'YOUR_TABLE'
  ORDER BY ordinal_position;

READ 6 — EXISTING BACKEND CODE:
Read the actual source files in backend/ that this batch will extend or consume. The design doc must reference real function signatures, real model field names, and real import paths — not invented examples. Required reads:
  - backend/db_models_map.md (model-to-file mapping)
  - backend/app_model_import.md (import paths)
  - Relevant route files in backend/api/routes/
  - Relevant service files in backend/services/
  - Relevant model files in backend/app/models/

After completing all six reads, produce the Batch B{N} Design Document at:
dev-docs/architecture-design/batch-designs/batch-b{N}-design.md

The design doc must contain all seven sections:

A. MIGRATION PLAN
   - Every new table: all column names, types, nullability, FK targets, and indexes
   - Every new table MUST include a mixin assignment: `StandardAuditMixin` (mutable records — adds created_at, updated_at, created_by, updated_by + 3-trigger set), `AppendOnlyMixin` (immutable/ledger records — adds created_at, created_by + 2-trigger set), or `MachineLogMixin` (automated system events — adds created_at only + audit trigger). State the mixin and one-line rationale for each new table. See backend/app/models/mixins.py.
   - Every column addition to an existing table (confirmed not pre-existing via MCP query before listing)
   - Migration naming convention: phase_fe_1_batch_b{N}_{short_description} (one migration per logical unit)

B. EXECUTION ORDER
   - Items in the order they will be implemented
   - One-line rationale for each item's position (intra-batch dependency or pattern-establishment reason)

C. NEW API ENDPOINTS
   - HTTP method + path + request body shape + response shape for every new endpoint
   - Auth requirement: JWT required / public / admin-only
   - RBAC permission required (referencing real permissions in backend/core/permissions.py)

D. PATTERN REUSE DECISIONS
   - For each §1.5 shared module this batch establishes or consumes: exact function call signature and which items use it
   - For each pattern from pilot-python-engineer-methods.md that applies: cite the section number and map it to specific batch items
   - All code examples must use real existing function signatures from the codebase, not invented ones

E. SHARED MODULE INTERFACES (for any new shared utility established in this batch)
   - Full Python interface: class name, method signatures, parameter types, return types, docstrings
   - File path where the module will live in backend/

F. OPEN QUESTIONS RESOLVED
   - Any schema ambiguity, FK target question, or design fork that could block implementation
   - Each question must have a recommended decision — do not leave questions open in the output
   - If a question genuinely cannot be resolved from available inputs, flag it explicitly and state what information is needed

G. EXTERNAL DEPENDENCY STATUS
   - Which items require Stripe / Telnyx / 10DLC / OpenAI / SendGrid / etc.
   - Mock strategy for each (per §1.5 Rule 2 of the impl plan)
   - What Tom must action before production delivery of that item (with known lead times if applicable)

Do not produce the design doc until all six reads are complete. Do not leave any section blank. Do not leave schema questions unresolved.
```
