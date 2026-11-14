#!/usr/bin/env python3
"""
team_invite_1_close_update.py — one-off doc maintenance (2026-09-03, close pass).

TEAM-INVITE-1 (Ord 8) closed + deployed to prod 2026-09-03 (Part A 4786/0 +17;
Part B ui 685 / web 2236 / mobile 701). Applies the full ADR-0018 status-flip
close to pilot-launch-plan.md (v7.27) + the pilot-docs-list.md registry row for
the prod test plan. The apply_diff tool repeatedly fails substring edits on the
launch plan (emoji-adjacent lines), so all edits are count-asserted string
replacements / line inserts here. Idempotent — re-run is a no-op.

Edits:
 1. v7.26 line: designer-gate waiver phrase (same as team_invite_1_waiver_update.py — folded in so only one script run is needed)
 2. Version 7.26 → 7.27
 3. v7.27 changelog line inserted before "**Archives**:"
 4. §1 phase-table row 8 status 🔄 → ✅ 2026-09-03
 5. Card §3.8 heading gains "✅ Closed 2026-09-03" + a Closed line under it
 6. Appendix A-2 registry row after the PLP-FIX-5 row
 7. pilot-docs-list.md: prod-test-plan row after the TEAM-INVITE-1 design row

Run:
    cd <repo>
    python3 admin-tools/team_invite_1_close_update.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PLAN = REPO / "dev-docs/analysis/pilot-launch-plan.md"
REGISTRY = REPO / "pilot-docs-list.md"

failures: list[str] = []


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        print(f"  {label}: already applied — no-op")
        return text
    count = text.count(old)
    if count != 1:
        failures.append(f"{label}: expected 1 of {old[:60]!r}…, found {count}")
        return text
    print(f"  {label}: applied")
    return text.replace(old, new, 1)


def insert_after_line(
    path_text: str, anchor_prefix: str, new_line: str, label: str
) -> str:
    if new_line.strip() in path_text:
        print(f"  {label}: already present — no-op")
        return path_text
    lines = path_text.splitlines(keepends=True)
    for idx, line in enumerate(lines):
        if line.startswith(anchor_prefix):
            lines.insert(
                idx + 1, new_line if new_line.endswith("\n") else new_line + "\n"
            )
            print(f"  {label}: inserted after line {idx + 1}")
            return "".join(lines)
    failures.append(f"{label}: anchor {anchor_prefix[:50]!r}… not found")
    return path_text


# ── Launch plan ──────────────────────────────────────────────────────────────
plan = PLAN.read_text(encoding="utf-8")

# 1. v7.26 waiver phrase (idempotent; supersedes team_invite_1_waiver_update.py)
plan = replace_once(
    plan,
    "; designer spec commission is the Part B gate per Rule 1.5)",
    "; designer gate **waived by Tom** for Part B (design §G.12) — React prompt authored same day)",
    "1 v7.26 waiver phrase",
)

# 2. Version bump
plan = replace_once(plan, "**Version**: 7.26", "**Version**: 7.27", "2 version 7.27")

# 3. v7.27 changelog insert before **Archives**:
V727 = (
    "**v7.27 changes (2026-09-03)**: **TEAM-INVITE-1 ✅ closed (Ord 8) + deployed to prod** "
    "(designer gate waived by Tom — design §G.12) — **Part A (Python)**: 4769→4786 passed (+17: 14 invite + 3 Lambda) — "
    "migration `3da9abdfb2f2` (nullable `tenant_user_invite.role_code` + FK, DDL-only per ADR-0016); `team_invite` "
    "email template (Group A — email_template=17; **prod converge required for the send path**); 4 authed endpoints + "
    "4 `/test` twins + public `GET /invites/{token}` (uniform 404, 10/min limit); Idempotency-Key hard-required; Lambda "
    "Path 2 role-at-invite (NULL→technician fallback) + best-effort usage counter (never-raise preserved). "
    '**Part B (React)**: ui 660→685 (+25) / web 2224→2236 (+12) / mobile 701 — P0 "coming soon" dialog replaced by '
    "`InviteMemberDialog` (5 states incl. both 409 paths) + `PendingInvitesSection` (optimistic Resend/Revoke) + public "
    "`/invite/[token]` landing (bare-fetch precedent); **ADR-0010 invite-exposed subset EXECUTED — full rename** "
    "(37-literal census, within cap): `PilotRole` → BE vocabulary, accountant set REPLACED read-only, `users.manage` "
    "owner-only, AuthProvider identity mapping, ~30 call-site sweep. **§7 gate row stays ☐** — flips after Tom's "
    "end-to-end invite smoke: [`team-invite-1-prod-test-plan.md`](../testing-support/team-invite-1-prod-test-plan.md). "
    "Open tail: founder-invite journey folds into E2E-WEB-1."
)
plan = insert_after_line(
    plan, "**v7.26 changes (2026-09-03)**", "\n" + V727, "3 v7.27 changelog"
)

# 4. Phase-table row 8 status flip
plan = replace_once(
    plan,
    "| 8 | **TEAM-INVITE-1** | Invite-Employee UI + endpoint + invite-landing SignUp | Architect → Python + React | SIGNUP-GA-1 ✅ | 🔄 |",
    "| 8 | **TEAM-INVITE-1** | Invite-Employee UI + endpoint + invite-landing SignUp | Architect → Python + React | SIGNUP-GA-1 ✅ | ✅ 2026-09-03 |",
    "4 phase-table row 8 ✅",
)

# 5. Card heading + Closed line
plan = replace_once(
    plan,
    '### 3.8 — TEAM-INVITE-1: Tenant-Owner "Invite Employee" UI + Invite-Landing SignUp',
    '### 3.8 — TEAM-INVITE-1: Tenant-Owner "Invite Employee" UI + Invite-Landing SignUp ✅ Closed 2026-09-03',
    "5 card heading ✅",
)
plan = insert_after_line(
    plan,
    '### 3.8 — TEAM-INVITE-1: Tenant-Owner "Invite Employee" UI + Invite-Landing SignUp ✅ Closed 2026-09-03',
    "",
    "5b heading spacer",
)
plan = insert_after_line(
    plan,
    '### 3.8 — TEAM-INVITE-1: Tenant-Owner "Invite Employee" UI + Invite-Landing SignUp ✅ Closed 2026-09-03',
    "**Closed 2026-09-03** — Part A (4786/0, +17) + Part B (ui 685 / web 2236 / mobile 701) same-day; prod-deployed incl. migration `3da9abdfb2f2` (completion summaries in each prompt appendix). **Open tail**: ① Tom's end-to-end invite smoke ([`team-invite-1-prod-test-plan.md`](../testing-support/team-invite-1-prod-test-plan.md)) → flips the §7 gate row; ② founder-invite journey folds into E2E-WEB-1.",
    "5c card Closed line",
)

# 6. Appendix A-2 row after PLP-FIX-5
plan = insert_after_line(
    plan,
    "| PLP-FIX-5 | 2026-09-02 |",
    "| TEAM-INVITE-1 | 2026-09-03 | Tenant-owner invite-employee end-to-end — invite endpoints + email + Lambda role-at-invite + team UI + `/invite/[token]` landing + FE RBAC reconciliation (ADR-0010 subset) | [design](../architecture-design/batch-designs/batch-team-invite-1-design.md) · [BE](../implementation-prompts/fe-be-mob-batch-prompts/batch-team-invite-1-python-engr-prompt.md) · [FE](../implementation-prompts/fe-be-mob-batch-prompts/batch-team-invite-1-react-engr-prompt.md) |",
    "6 Appendix A-2 row",
)

# ── Registry ─────────────────────────────────────────────────────────────────
registry = REGISTRY.read_text(encoding="utf-8")
registry = insert_after_line(
    registry,
    "| [TEAM-INVITE-1 Design Doc]",
    "| [TEAM-INVITE-1 Prod Test Plan](dev-docs/testing-support/team-invite-1-prod-test-plan.md) | `dev-docs/testing-support/team-invite-1-prod-test-plan.md` | Tom's end-to-end invite smoke playbook (pre-flight gates: migration `3da9abdfb2f2` + `team_invite` template converge + Lambda redeploy; 11 test cases: happy path, role-at-invite, 409s, resend/revoke, RBAC as technician, cleanup) — §7 gate row flips on pass | 2026-09-03 |",
    "7 registry test-plan row",
)

# ── Write + report ───────────────────────────────────────────────────────────
if failures:
    print("\n❌ FAILURES — no files written:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)

PLAN.write_text(plan, encoding="utf-8")
REGISTRY.write_text(registry, encoding="utf-8")
print("\n✅ TEAM-INVITE-1 close applied — launch plan v7.27 + registry updated")
