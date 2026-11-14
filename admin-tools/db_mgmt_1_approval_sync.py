#!/usr/bin/env python3
"""One-off doc sync: DB-MGMT-1 design APPROVED (2026-08-18) + Python prompt registered.

Applies the final stewardship edits after Tom's design approval + ADR-0016 recording:
  1. pilot-docs-list.md — flip design row to APPROVED; mark ADR-0016 as recorded
  2. pilot-launch-plan.md — Order-3 row + design-task row: approved + prompt link
  3. fe-be-mob-batch-prompts/README.md — add the new prompt to the folder listing

Self-verifying: each pattern must occur exactly once; skips if already applied;
exits non-zero on any failure. Safe to re-run (idempotent).

Run from the repo root:
    python admin-tools/db_mgmt_1_approval_sync.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # repository root

DOCSLIST = "pilot-docs-list.md"
LAUNCH = "dev-docs/analysis/pilot-launch-plan.md"
README = "dev-docs/implementation-prompts/fe-be-mob-batch-prompts/README.md"

README_LINE = (
    "  batch-db-mgmt-1-python-engr-prompt.md    ← DB-MGMT-1 (Python, backend tooling only, 5–6h): "
    "`_env_profiles.py` registry + `--env`/`SEED_ENV` on 12 seed scripts (fail-closed group gating, host guards, audit banner); "
    "`seed_platform.py` registry-driven Stripe price IDs + converge-UPDATE; `provision_schema.py` (generalized E2E schema-restore) "
    "+ `seed_qa_db.py`/`seed_prod_db.py` orchestrators (prod converge is Tom-run, Secrets preflight); "
    "`seed_pricebook_starter.py` (per-tenant, catalog Tom-gated); runbooks + drift fixes; ≥12 new platform_infrastructure tests. "
    "No endpoints/models/migrations. Design: batch-db-mgmt-1-design.md v1.1 ✅ APPROVED 2026-08-18 · ADR-0016. ☐ READY TO RUN"
)

EDITS = {
    DOCSLIST: [
        (
            "☐ AWAITING TOM APPROVAL 2026-08-18 | 2026-08-18 |",
            "✅ APPROVED 2026-08-18 | 2026-08-18 |",
        ),
        (
            "DDL-only-migrations rule → ADR-0016 candidate,",
            "DDL-only-migrations rule → ADR-0016 (recorded 2026-08-18),",
        ),
    ],
    LAUNCH: [
        (
            "v1.1 2026-08-18 (vendor-posture matrix; Telnyx decided Option A) — **awaiting Tom approval** | ☐ |",
            "v1.1 ✅ APPROVED 2026-08-18 · [Python prompt](../implementation-prompts/fe-be-mob-batch-prompts/batch-db-mgmt-1-python-engr-prompt.md) ☐ READY | 🔄 |",
        ),
        (
            "Awaiting Tom approval (Telnyx §G-11 decided Option A 2026-08-18), then Python prompt.",
            "✅ APPROVED 2026-08-18 (Telnyx §G-11 Option A); ADR-0016 recorded. Python prompt ☐ READY: [`batch-db-mgmt-1-python-engr-prompt.md`](../implementation-prompts/fe-be-mob-batch-prompts/batch-db-mgmt-1-python-engr-prompt.md).",
        ),
    ],
}

failures = 0

# ── Simple exact-string replacements ─────────────────────────────────────────
for rel, pairs in EDITS.items():
    path = ROOT / rel
    text = path.read_text(encoding="utf-8")
    changed = False
    for old, new in pairs:
        if new in text:
            print(f"SKIP (already applied): {rel} :: {old[:70]}")
            continue
        count = text.count(old)
        if count != 1:
            print(f"FAIL: {rel} :: pattern found {count}x (expected 1): {old[:90]}")
            failures += 1
            continue
        text = text.replace(old, new)
        changed = True
        print(f"OK: {rel} :: {old[:70]}")
    if changed:
        path.write_text(text, encoding="utf-8")

# ── README folder-listing insertion ──────────────────────────────────────────
readme_path = ROOT / README
rtext = readme_path.read_text(encoding="utf-8")
anchor = "  README.md                              ← this file\n"
if "batch-db-mgmt-1-python-engr-prompt.md" in rtext:
    print(f"SKIP (already applied): {README} :: folder-listing line")
elif rtext.count(anchor) != 1:
    print(f"FAIL: {README} :: anchor found {rtext.count(anchor)}x (expected 1)")
    failures += 1
else:
    rtext = rtext.replace(anchor, anchor + README_LINE + "\n")
    readme_path.write_text(rtext, encoding="utf-8")
    print(f"OK: {README} :: folder-listing line inserted")

if failures:
    print(f"\n{failures} replacement(s) FAILED — review output above")
    sys.exit(1)
print(
    "\nAll replacements applied (or already present). DB-MGMT-1 approval state is fully synced."
)
