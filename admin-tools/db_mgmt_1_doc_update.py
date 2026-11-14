#!/usr/bin/env python3
"""One-off status updater: DB-MGMT-1 design v1.1 (2026-08-18) doc sync.

Applies 4 exact-string replacements across the launch plan and docs registry.
Self-verifying: each pattern must occur exactly once; skips if already applied;
exits non-zero on any assertion failure. Safe to re-run.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # repository root

EDITS = {
    "dev-docs/analysis/pilot-launch-plan.md": [
        (
            "v1.0 authored 2026-08-17 — **awaiting Tom approval** | ☐ |",
            "v1.1 2026-08-18 (vendor-posture matrix + Telnyx open Q) — **awaiting Tom approval** | ☐ |",
        ),
        (
            "v1.0 authored 2026-08-17 — [`batch-db-mgmt-1-design.md`](../architecture-design/batch-designs/batch-db-mgmt-1-design.md); E2E DB restore was the working reference. Awaiting Tom approval, then Python prompt.",
            "v1.1 2026-08-18 — [`batch-db-mgmt-1-design.md`](../architecture-design/batch-designs/batch-db-mgmt-1-design.md); E2E DB restore was the working reference. Awaiting Tom approval (+ Telnyx open Q §G-11), then Python prompt.",
        ),
    ],
    "pilot-docs-list.md": [
        (
            "DB-MGMT-1 design (v1.0):",
            "DB-MGMT-1 design (v1.1 — adds §B.3 vendor-posture matrix: QBO sandbox / Cognito dev pool / SendGrid shared all real from dev; Telnyx non-prod = open Q §G-11; prod Stripe stays test-mode until GA):",
        ),
        (
            "AWAITING TOM APPROVAL 2026-08-17 | 2026-08-17 |",
            "AWAITING TOM APPROVAL 2026-08-18 | 2026-08-18 |",
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
    print(
        f"\n{failures} replacement(s) FAILED — file(s) NOT written for failed patterns"
    )
    sys.exit(1)
print("\nAll replacements applied (or already present).")
