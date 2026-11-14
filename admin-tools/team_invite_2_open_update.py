#!/usr/bin/env python3
"""
team_invite_2_open_update.py — Open TEAM-INVITE-2 in the launch plan (v7.27 → v7.28)
+ register the design doc in pilot-docs-list.md.

TEAM-INVITE-2 = invite-landing accept flow (password + Cognito verify on
/invite/[token]), fixing the CTA misroute to the owner /signup wizard found in
Tom's 2026-09-03 prod smoke. Pure-frontend batch; design + React prompt authored
same day. Per §6 protocol, prompt files are NOT added to pilot-docs-list.md
(prompts folders indexed at folder level) — only the design doc row is added.

House pattern (apply_diff repeatedly fails substring edits on the launch plan;
lines containing 🔄 carry a VS16 variation selector): assertion-guarded,
idempotent Python edits. Every mutation asserts an exact match count of 1.
Re-running after a successful run is a no-op.

Edits:
 1. Version 7.27 → 7.28
 2. v7.28 changelog line inserted before "**Archives**:"
 3. §1.1 phase-table: new Ord 27 row after the PLP-FIX-5 (Ord 26) row
 4. New card §3.27 inserted before "## Section 4 — Phase 2"
 5. pilot-docs-list.md: design-doc row after the TEAM-INVITE-1 Prod Test Plan row

Usage: python3 admin-tools/team_invite_2_open_update.py
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PLAN = REPO / "dev-docs/analysis/pilot-launch-plan.md"
REGISTRY = REPO / "pilot-docs-list.md"


def fail(msg: str) -> None:
    print(f"ERROR: {msg}")
    sys.exit(1)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"{label}: expected exactly 1 occurrence, found {count}")
    return text.replace(old, new, 1)


def insert_after_line_starting(
    text: str, prefix: str, new_line: str, label: str
) -> str:
    lines = text.split("\n")
    matches = [i for i, ln in enumerate(lines) if ln.startswith(prefix)]
    if len(matches) != 1:
        fail(
            f"{label}: expected exactly 1 line starting with {prefix!r}, found {len(matches)}"
        )
    lines.insert(matches[0] + 1, new_line)
    return "\n".join(lines)


def main() -> None:
    plan = PLAN.read_text(encoding="utf-8")
    registry = REGISTRY.read_text(encoding="utf-8")

    if "TEAM-INVITE-2" in plan:
        print("TEAM-INVITE-2 already present in launch plan — checking registry only.")
    else:
        # 1. Version bump
        plan = replace_once(
            plan,
            "**Version**: 7.27",
            "**Version**: 7.28",
            "version bump",
        )

        # 2. Changelog line before **Archives**:
        changelog = (
            "**v7.28 changes (2026-09-03)**: **TEAM-INVITE-2 opened** (new Ord 27 + card "
            "§3.27; design + React prompt authored, ready to execute — Tom green-light in "
            "session). Tom's TEAM-INVITE-1 prod smoke found the invite-landing **Create "
            "your account** CTA misroutes to the **owner** `/signup` wizard (business "
            "name/industry/plan, Path 3 provisioning) — root cause: Part B prompt STEP 6 "
            "prefill-fallback masked the missing invite-scoped step (architect spec miss, "
            "faithfully implemented). Pure-frontend fix: on-page password + Cognito verify "
            "accept flow at `/invite/[token]` (reuse `useCognitoSignUp` / `VerifyEmailStep` "
            "**minus** `POST /api/v1/signup`), role-branched completion (office → "
            "`/dashboard`; technician → mobile-app panel — web blocks techs post-login). "
            "Also same day: Tom hot-fixed prod `FRONTEND_URL` (invite-email footer URL) + "
            "revoked-email re-invite upsert with the Python Engineer.\n\n"
        )
        plan = replace_once(
            plan,
            "\n**Archives**:",
            "\n" + changelog + "**Archives**:",
            "v7.28 changelog",
        )

        # 3. Phase-table row (Ord 27) after the PLP-FIX-5 (Ord 26) row
        row27 = (
            "| 27 | **TEAM-INVITE-2** 🆕 | Invite-landing accept flow — on-page password + "
            "Cognito verify at `/invite/[token]` (fixes CTA misroute to owner `/signup` "
            "wizard found in Tom's prod smoke) — **design + prompt authored 2026-09-03 "
            "(ready to execute)** | React | 8 ✅ | 🔄 |"
        )
        plan = insert_after_line_starting(
            plan, "| 26 | **PLP-FIX-5**", row27, "Ord 27 row"
        )

        # 4. Card §3.27 before Section 4
        card = (
            "### 3.27 — TEAM-INVITE-2 🆕: Invite-Landing Accept Flow (Password + Verify + Land-in-Tenant)\n"
            "\n"
            "**Owner**: React · **Depends on**: TEAM-INVITE-1 ✅ · **Status**: 🔄 Design + prompt authored 2026-09-03 (Tom green-light in session)\n"
            "**Scope**: fix the invite-landing CTA misroute from Tom's prod smoke — the landing page's "
            '"Create your account" linked to the **owner** `/signup` wizard (business name, industry, '
            "plan → Path 3 `POST /api/v1/signup` provisioning). Replace with an on-page invite-scoped "
            "accept flow: password + confirm (Zod pool-policy, duplicated schema per §G.5) → Cognito "
            "`SignUp` (reuse `useCognitoSignUp`) → 6-digit verify (mirror `VerifyEmailStep` **minus** "
            "`POST /api/v1/signup` — Lambda Path 2 attaches at confirm) → role-branched completion: "
            'office roles auto-sign-in → `/dashboard`; technician → "open the mobile app" terminal '
            "panel (web blocks techs post-login per `usePostLoginRedirect`). Pure frontend — zero "
            "backend/DB/endpoint changes; Part B landing test asserting the old CTA updated in-batch.\n"
            "**Root cause**: architect prompt spec miss (Part B STEP 6 prefill-fallback masked the "
            "missing invite-scoped step); engineer executed as written. Designer gate **WAIVED by Tom "
            "2026-09-03** (design §G.7 — proven-primitive composition on an existing surface).\n"
            "**Design doc**: [`batch-team-invite-2-design.md`](../architecture-design/batch-designs/batch-team-invite-2-design.md) · "
            "**Prompt**: [`batch-team-invite-2-react-engr-prompt.md`](../implementation-prompts/fe-be-mob-batch-prompts/batch-team-invite-2-react-engr-prompt.md) · "
            "**Estimate**: ~2.5 h.\n"
            "\n"
            "---\n"
        )
        plan = replace_once(
            plan,
            "## Section 4 — Phase 2: Full UI Suite (batch detail)",
            card + "\n## Section 4 — Phase 2: Full UI Suite (batch detail)",
            "§3.27 card",
        )

        PLAN.write_text(plan, encoding="utf-8")
        print("launch plan: v7.28 + Ord 27 row + §3.27 card applied.")

    # 5. Registry row (design doc only — prompts indexed at folder level per §6)
    if "batch-team-invite-2-design.md" in registry:
        print("registry: TEAM-INVITE-2 design row already present — no-op.")
    else:
        reg_row = (
            "| [TEAM-INVITE-2 Design Doc](dev-docs/architecture-design/batch-designs/batch-team-invite-2-design.md) | "
            "`dev-docs/architecture-design/batch-designs/batch-team-invite-2-design.md` | "
            "TEAM-INVITE-2 design (v1.0, Tom green-light 2026-09-03): invite-landing accept flow — on-page "
            "password + Cognito verify at `/invite/[token]` (fixes CTA misroute to owner `/signup` wizard); "
            "reuse `useCognitoSignUp`/`VerifyEmailStep` minus `POST /api/v1/signup`; role-branched completion "
            "(office → `/dashboard`; technician → mobile-app panel); pure frontend | 2026-09-03 |"
        )
        registry = insert_after_line_starting(
            registry,
            "| [TEAM-INVITE-1 Prod Test Plan]",
            reg_row,
            "registry design row",
        )
        REGISTRY.write_text(registry, encoding="utf-8")
        print("registry: design-doc row added.")

    print(
        "DONE — TEAM-INVITE-2 open recorded (launch plan v7.28 + pilot-docs-list.md)."
    )


if __name__ == "__main__":
    main()
