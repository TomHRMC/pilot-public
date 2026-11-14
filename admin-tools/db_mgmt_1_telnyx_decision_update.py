#!/usr/bin/env python3
"""One-off doc sync: record Telnyx Option A decision (Tom, 2026-08-18) across the
DB-MGMT-1 design v1.1 doc set.

Decision: mock SMS carrier in dev/e2e permanently; Phase 2 QA gets its own real
messaging profile + phone number (~$1/mo) per aws-env-mgmt-ops-plan §2.

Applies 7 exact-string replacements across 4 files. Self-verifying: each pattern
must occur exactly once; skips if the replacement is already present; exits
non-zero on any assertion failure. Safe to re-run (idempotent).

Run from the repo root:
    python admin-tools/db_mgmt_1_telnyx_decision_update.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # repository root

DESIGN = "dev-docs/architecture-design/batch-designs/batch-db-mgmt-1-design.md"
ENVPLAN = "dev-docs/devops/aws-env-mgmt-ops-plan.md"
DOCSLIST = "pilot-docs-list.md"
LAUNCH = "dev-docs/analysis/pilot-launch-plan.md"

EDITS = {
    DESIGN: [
        (
            "**Status**: v1.1 — AUTHORED 2026-08-17, amended 2026-08-18 (vendor-posture matrix §B.3 + Telnyx open question §G-11 per Tom), awaiting Tom approval",
            "**Status**: v1.1 — AUTHORED 2026-08-17, amended 2026-08-18 (vendor-posture matrix §B.3 + Telnyx Option A decision §G-11 per Tom), awaiting Tom approval",
        ),
        (
            "Telnyx non-prod support is an explicit open discussion item (§G-11).",
            "Telnyx non-prod **resolved 2026-08-18 (Tom): Option A** (§G-11) — mock carrier in dev/e2e permanently; Phase 2 QA gets its own real messaging profile + number (~$1/mo).",
        ),
        (
            "Telnyx beyond prod is an open decision (§G-11);",
            "Telnyx beyond prod is decided (§G-11 Option A — mock in dev/e2e permanently, real messaging profile + number for Phase 2 QA);",
        ),
        (
            "| **PENDING Tom decision — non-blocking.** Options: (A) keep dev/e2e on mock carrier + Phase 2 QA gets its own messaging profile + number per env-mgmt §2 (~$1/mo) — current plan; (B) real Telnyx from dev now (second profile + number, ~$1–2/mo, accelerates SMS-path debugging pre-beta); (C) mock everywhere except prod permanently (rely on prod smokes only). Seeds are Telnyx-independent (the Group D `tenant_phone_number` row is inert), so the batch proceeds under any outcome; the chosen posture lands in §B.3 and `_env_profiles.vendor_posture` at implementation time. |",
            '| **DECIDED 2026-08-18 — Option A (Tom):** mock carrier in dev/e2e permanently; Phase 2 QA gets its own real messaging profile + phone number (~$1/mo) per env-mgmt §2. Zero cost/change now; QA gains real SMS fidelity at beta. Lands in §B.3 and `_env_profiles.vendor_posture` (`telnyx: "mock"` for dev/e2e; `"real"` for qa/prod). |',
        ),
    ],
    ENVPLAN: [
        (
            "real Telnyx beyond prod is an open decision, see [`batch-db-mgmt-1-design.md`](../architecture-design/batch-designs/batch-db-mgmt-1-design.md) §G-11)",
            "real Telnyx beyond prod is limited to Phase 2 QA (own messaging profile + number; dev/e2e mock permanently — Tom 2026-08-18, [`batch-db-mgmt-1-design.md`](../architecture-design/batch-designs/batch-db-mgmt-1-design.md) §G-11 Option A)",
        ),
    ],
    DOCSLIST: [
        (
            "Telnyx non-prod = open Q §G-11; prod Stripe stays test-mode until GA):",
            "Telnyx non-prod = mock dev/e2e + QA real at Phase 2 (§G-11 Option A, Tom 2026-08-18); prod Stripe stays test-mode until GA):",
        ),
    ],
    LAUNCH: [
        (
            "Awaiting Tom approval (+ Telnyx open Q §G-11), then Python prompt.",
            "Awaiting Tom approval (Telnyx §G-11 decided Option A 2026-08-18), then Python prompt.",
        ),
        (
            "v1.1 2026-08-18 (vendor-posture matrix + Telnyx open Q) — **awaiting Tom approval**",
            "v1.1 2026-08-18 (vendor-posture matrix; Telnyx decided Option A) — **awaiting Tom approval**",
        ),
    ],
}

failures = 0
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

if failures:
    print(f"\n{failures} replacement(s) FAILED — review output above")
    sys.exit(1)
print(
    "\nAll replacements applied (or already present). Telnyx Option A is now consistent across all 4 docs."
)
