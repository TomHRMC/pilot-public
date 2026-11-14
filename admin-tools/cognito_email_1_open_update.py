#!/usr/bin/env python3
"""
cognito_email_1_open_update.py — Open COGNITO-EMAIL-1 in the launch plan
(v7.28 → v7.29) + register the design doc in pilot-docs-list.md.

COGNITO-EMAIL-1 = Cognito auth emails via SendGrid Custom Email Sender (Ord 15,
launch plan §3.15, §7 gate row). Design + both prompts authored 2026-09-03:
Part A Python (custom_email_sender Lambda + branded templates + unit tests) →
Part B DevOps (packaging + Terraform + one-call-all-triggers wiring + smokes).

Also records in the v7.29 changelog: TEAM-INVITE-2 executed same-day (web
2236→2256, +20 tests) with close HELD per Tom (smoke partial — Ord 27 stays 🔄,
§7 gate row ☐), and logs the new-device-SMS copy gap to PLAT-DEBT.

House pattern: assertion-guarded, idempotent Python edits (apply_diff fails
substring edits on the launch plan). Every mutation asserts exact match counts.
Re-running after a successful run is a no-op.

Edits:
 1. Version 7.28 → 7.29
 2. v7.29 changelog line before "**Archives**:"
 3. §1.1 phase-table Ord 15 row → 🔄 (rewritten, stale depends-note fixed)
 4. §3.15 card: Status line insert + stale schedule-note replacement +
    AdminCreateUser parenthetical correction
 5. PLAT-DEBT table: new-device SMS copy-gap row (after the RBAC row)
 6. pilot-docs-list.md: design-doc row after the TEAM-INVITE-2 design row

Usage: python3 admin-tools/cognito_email_1_open_update.py
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


def rewrite_line_starting(text: str, prefix: str, new_line: str, label: str) -> str:
    lines = text.split("\n")
    matches = [i for i, ln in enumerate(lines) if ln.startswith(prefix)]
    if len(matches) != 1:
        fail(
            f"{label}: expected exactly 1 line starting with {prefix!r}, found {len(matches)}"
        )
    lines[matches[0]] = new_line
    return "\n".join(lines)


def main() -> None:
    plan = PLAN.read_text(encoding="utf-8")
    registry = REGISTRY.read_text(encoding="utf-8")

    if "v7.29 changes" in plan:
        print(
            "v7.29 changelog already present — launch plan edits already applied; checking registry only."
        )
    else:
        # 1. Version bump
        plan = replace_once(
            plan, "**Version**: 7.28", "**Version**: 7.29", "version bump"
        )

        # 2. Changelog before **Archives**:
        changelog = (
            "**v7.29 changes (2026-09-03)**: **COGNITO-EMAIL-1 opened** (Ord 15 → 🔄; design + both "
            "prompts authored, **for Tom approval** — Part A Python: `custom_email_sender` Lambda + "
            "branded templates + unit tests (~2 h) → Part B DevOps: packaging + Terraform + "
            "one-call-all-triggers wiring + Gmail DKIM/SPF smokes (~3 h), sequential). Design "
            "corrections to the card: rollback = **detach trigger** (`email_sending_account` never "
            "leaves `COGNITO_DEFAULT`); wiring follows the ADR-0011 manual-CLI posture (one "
            "`update-user-pool` carrying PostConfirmation + PostAuthentication + CustomEmailSender + "
            "KMSKeyID — the API replaces the whole LambdaConfig map); **raise-on-failure** posture "
            "(the Lambda IS the delivery path — opposite invariant from the passive hooks). "
            "**TEAM-INVITE-2 executed same-day** (web 2236→2256, +20 tests — on-page invite accept "
            "flow: password + Cognito verify + role-branched completion; `/signup` CTA misroute fixed) "
            "— **close HELD per Tom: prod smoke partially passed, remainder pending; Ord 27 stays 🔄, "
            "§7 invite gate row stays ☐** (close script rides a later version). PLAT-DEBT: new-device "
            "SMS copy gap logged (owner fan-out is by design — PLATFORM-SMS-B2 §G-7; the static "
            "Sample 3 body doesn't name the sign-in email).\n\n"
        )
        plan = replace_once(
            plan,
            "\n**Archives**:",
            "\n" + changelog + "**Archives**:",
            "v7.29 changelog",
        )

        # 3. Ord 15 row rewrite
        row15 = (
            "| 15 | **COGNITO-EMAIL-1** 🆕 | Cognito auth emails via SendGrid custom sender "
            "(signup/forgot/invite, branded) — **design + both prompts authored 2026-09-03 "
            "(for Tom approval)** | Python → DevOps | none | 🔄 |"
        )
        plan = rewrite_line_starting(
            plan, "| 15 | **COGNITO-EMAIL-1**", row15, "Ord 15 row"
        )

        # 4a. Card: Status line after the Owner line
        status_line = (
            "**Status**: 🔄 Design + both prompts authored 2026-09-03 (for Tom approval) — "
            "Part A Python (Lambda + templates + tests) → Part B DevOps (packaging + Terraform + "
            "wiring + smokes), sequential. Design doc: "
            "[`batch-cognito-email-1-design.md`](../architecture-design/batch-designs/batch-cognito-email-1-design.md)."
        )
        plan = insert_after_line_starting(
            plan,
            "**Owner**: Python + DevOps · **Depends on**: nothing (SendGrid live",
            status_line,
            "§3.15 status line",
        )

        # 4b. Card: stale schedule-note replacement
        plan = rewrite_line_starting(
            plan,
            "**Schedule note**:",
            "**Schedule note**: TEAM-INVITE-1/2 closed 2026-09-03 without this (invite + verification "
            "emails currently ride `COGNITO_DEFAULT`, unbranded, 50/day cap); must close before "
            "founder #1 (§7 gate row) — branded auth emails are founder-facing from day one.",
            "§3.15 schedule note",
        )

        # 4c. Card: AdminCreateUser parenthetical correction
        plan = replace_once(
            plan,
            "and **AdminCreateUser invites** (TEAM-INVITE-1) —",
            "and **AdminCreateUser invites** (future-proofing; TEAM-INVITE-1 is self-`SignUp` per ADR-0011) —",
            "§3.15 AdminCreateUser note",
        )

        # 5. PLAT-DEBT row after the RBAC hardening row
        plat_row = (
            "| New-device SMS copy doesn't name the sign-in identity | Python | Owner fan-out is "
            '**by design** (PLATFORM-SMS-B2 §G-7); the static Sample 3 body says "your account" '
            "for employee sign-ins. Parameterize `platform_security_new_device` with the sign-in "
            "email — touches the Celery task + template + verbatim-guardrail test. From Tom's "
            "tracker 2026-09-03 (COGNITO-EMAIL-1 design §G.7). |"
        )
        plan = insert_after_line_starting(
            plan, "| RBAC hardening", plat_row, "PLAT-DEBT row"
        )

        PLAN.write_text(plan, encoding="utf-8")
        print(
            "launch plan: v7.29 + Ord 15 🔄 + §3.15 card annotations + PLAT-DEBT row applied."
        )

    # 6. Registry row (design doc only — prompts indexed at folder level per §6)
    if "batch-cognito-email-1-design.md" in registry:
        print("registry: COGNITO-EMAIL-1 design row already present — no-op.")
    else:
        reg_row = (
            "| [COGNITO-EMAIL-1 Design Doc](dev-docs/architecture-design/batch-designs/batch-cognito-email-1-design.md) | "
            "`dev-docs/architecture-design/batch-designs/batch-cognito-email-1-design.md` | "
            "COGNITO-EMAIL-1 design (v1.0): Cognito auth emails via SendGrid Custom Email Sender — "
            "Lambda (KMS-decrypt → branded templates → SendGrid; raise-on-failure), 6 trigger sources, "
            "manual one-call-all-triggers wiring (ADR-0011 posture), rollback = detach trigger; "
            "Part A Python → Part B DevOps | 2026-09-03 |"
        )
        registry = insert_after_line_starting(
            registry, "| [TEAM-INVITE-2 Design Doc]", reg_row, "registry design row"
        )
        REGISTRY.write_text(registry, encoding="utf-8")
        print("registry: design-doc row added.")

    print(
        "DONE — COGNITO-EMAIL-1 open recorded (launch plan v7.29 + pilot-docs-list.md)."
    )


if __name__ == "__main__":
    main()
