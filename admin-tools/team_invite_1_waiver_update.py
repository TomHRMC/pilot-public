#!/usr/bin/env python3
"""
team_invite_1_waiver_update.py — one-off doc maintenance (2026-09-03, second pass).

Tom waived the TEAM-INVITE-1 Part B designer-spec gate (design §G.12). The
v7.26 changelog line still says the designer spec is the gate — this script
updates that single phrase. Count-asserted (exactly 1 hit), idempotent.

Run:
    cd <repo>
    python3 admin-tools/team_invite_1_waiver_update.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PLAN = REPO / "dev-docs/analysis/pilot-launch-plan.md"

OLD = "; designer spec commission is the Part B gate per Rule 1.5)"
NEW = (
    "; designer gate **waived by Tom** for Part B (design §G.12) — "
    "React prompt authored same day)"
)


def main() -> int:
    text = PLAN.read_text(encoding="utf-8")
    if NEW in text:
        print("  plan: waiver phrase already present — no-op")
        return 0
    count = text.count(OLD)
    if count != 1:
        print(f"  plan: EXPECTED 1 occurrence of {OLD!r}, found {count} — aborting")
        return 1
    PLAN.write_text(text.replace(OLD, NEW), encoding="utf-8")
    print("  plan: v7.26 line updated — designer gate waived by Tom (design §G.12)")
    print("✅ done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
