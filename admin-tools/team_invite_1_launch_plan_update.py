#!/usr/bin/env python3
"""
team_invite_1_launch_plan_update.py — one-off doc maintenance (2026-09-03).

Two precise edits the apply_diff tool could not land (emoji-adjacent match
failures — the 🔄 on the v7.26 line likely carries a VS16 variation selector):

1. pilot-launch-plan.md — v7.26 changelog line: replace the stale
   "Architect design in progress)" tail with the current state
   (design + Part A prompt authored, designer spec = Part B gate).
2. pilot-docs-list.md — add the TEAM-INVITE-1 design doc registry row
   after the PLP-FIX-5 design row (design docs are individually indexed;
   prompt files stay folder-level per ADR-0017 / rules §6).

Both edits are count-asserted (exactly 1 hit) and idempotent (re-run is a
no-op with a clear message). Byte-preserving otherwise (UTF-8, no newline
normalization beyond the edited lines).

Run:
    cd <repo>
    python3 admin-tools/team_invite_1_launch_plan_update.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PLAN = REPO / "dev-docs/analysis/pilot-launch-plan.md"
REGISTRY = REPO / "pilot-docs-list.md"

# ── Edit 1: launch plan v7.26 line ───────────────────────────────────────────
OLD_PLAN = "Architect design in progress)"
NEW_PLAN = (
    "design + Part A Python prompt authored, ready to execute — "
    "**for Tom approval**; designer spec commission is the Part B gate per Rule 1.5)"
)

# ── Edit 2: docs-list registry row (insert after PLP-FIX-5 design row) ───────
REGISTRY_ANCHOR = "| [PLP-FIX-5 Design Doc]"
REGISTRY_ROW = (
    "| [TEAM-INVITE-1 Design Doc](dev-docs/architecture-design/batch-designs/batch-team-invite-1-design.md) "
    "| `dev-docs/architecture-design/batch-designs/batch-team-invite-1-design.md` "
    "| TEAM-INVITE-1 design (v1.0): tenant-owner invite-employee — invite endpoints + email "
    "(`team_invite` template, Group A seed) + `tenant_user_invite.role_code` (nullable FK; Lambda Path 2 "
    "role-at-invite + best-effort usage counter) + public `GET /invites/{token}` (uniform 404) + Part B (React): "
    'invite dialog replaces P0 "coming soon", `/invite/[token]` landing, ADR-0010 FE `operator`→`accountant` '
    "reconciliation; mixed batch, designer spec gates Part B | 2026-09-03 |"
)


def edit_plan() -> bool:
    text = PLAN.read_text(encoding="utf-8")
    if NEW_PLAN in text:
        print("  plan: already up to date — no-op")
        return True
    count = text.count(OLD_PLAN)
    if count != 1:
        print(
            f"  plan: EXPECTED 1 occurrence of {OLD_PLAN!r}, found {count} — aborting"
        )
        return False
    PLAN.write_text(text.replace(OLD_PLAN, NEW_PLAN), encoding="utf-8")
    print("  plan: v7.26 line updated (design + Part A prompt authored)")
    return True


def edit_registry() -> bool:
    lines = REGISTRY.read_text(encoding="utf-8").splitlines(keepends=True)
    if any("TEAM-INVITE-1 Design Doc" in line for line in lines):
        print("  registry: TEAM-INVITE-1 row already present — no-op")
        return True
    for idx, line in enumerate(lines):
        if line.startswith(REGISTRY_ANCHOR):
            lines.insert(idx + 1, REGISTRY_ROW + "\n")
            REGISTRY.write_text("".join(lines), encoding="utf-8")
            print(f"  registry: TEAM-INVITE-1 design row inserted after line {idx + 1}")
            return True
    print(f"  registry: anchor {REGISTRY_ANCHOR!r} not found — aborting")
    return False


def main() -> int:
    print("TEAM-INVITE-1 doc maintenance (2026-09-03)")
    ok = edit_plan() and edit_registry()
    print("✅ done" if ok else "❌ aborted — see messages above")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
