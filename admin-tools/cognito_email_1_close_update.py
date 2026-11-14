#!/usr/bin/env python3
"""
cognito_email_1_close_update.py — Close COGNITO-EMAIL-1 in the launch plan
(v7.29 → v7.30) per ADR-0018 status-flip-only close protocol.

Evidence verified before authoring (2026-09-04):
- Part A (Python) appendix: 4787→4829 passed (+42 tests), handler + templates +
  test file shipped, alembic head unchanged, completed 2026-09-03.
- Part B (DevOps) appendix: LIVE 2026-09-03 — Lambda + alarm + IAM role deployed;
  one-call wiring (all 3 triggers + KMSKeyID; EmailSendingAccount + Sms/Device
  unchanged); smoke evidence DKIM/SPF/DMARC PASS + inbox placement (ForgotPassword
  + SignUp). 5 design deviations recorded (AWS Encryption SDK envelope decrypt,
  CommitmentPolicy, api_key secret key, 512 MB, CLI dict syntax).
- §7 gate row text requires "branded; inbox placement + DKIM/SPF smoke" — met by
  the captured evidence → gate row flips ✅.

House pattern: assertion-guarded, idempotent Python edits. Every mutation asserts
exact match counts. Re-running after a successful run is a no-op.

Edits (pilot-launch-plan.md):
 1. Version 7.29 → 7.30
 2. v7.30 changelog line before "**Archives**:"
 3. §1.1 Ord 15 row 🔄 → ✅ 2026-09-03 (rewritten with counts)
 4. §3.15 card heading marked ✅ Closed 2026-09-03 + Closed line inserted
 5. §7 gate row "COGNITO-EMAIL-1 closed…" ☐ → ✅ 2026-09-03
 6. Appendix A-3 registry row (after the Prod seed re-converge row)

No registry (pilot-docs-list.md) edit — design row already added at open; prompt
files are indexed at folder level per §6.

Usage: python3 admin-tools/cognito_email_1_close_update.py
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PLAN = REPO / "dev-docs/analysis/pilot-launch-plan.md"


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

    if "v7.30 changes" in plan:
        print("v7.30 changelog already present — close already applied. No-op.")
        return

    # 1. Version bump
    plan = replace_once(plan, "**Version**: 7.29", "**Version**: 7.30", "version bump")

    # 2. Changelog before **Archives**:
    changelog = (
        "**v7.30 changes (2026-09-04)**: **COGNITO-EMAIL-1 ✅ closed** (Ord 15; **§7 gate row ✅**) — "
        "**Part A (Python, 2026-09-03)**: 4787→4829 passed (+42 tests) — self-contained "
        "`custom_email_sender` Lambda (trigger routing → KMS decrypt → branded template → SendGrid, "
        "tracking disabled; §G.4 raise-on-failure) + 3 flows × HTML/plaintext + full test matrix; "
        "AWS doc contract verified (no divergence). **Part B (DevOps, 2026-09-03 — LIVE)**: build "
        "script + Terraform (Lambda + least-privilege role + KMS decrypt + permission + CloudWatch "
        "`Errors≥1/5min` alarm → SNS) applied green behind the plan-gate; **one-call wiring** "
        "(PostConfirmation + PostAuthentication + CustomEmailSender + KMSKeyID — EmailSendingAccount "
        "+ Sms/Device verified unchanged); smokes: ForgotPassword + SignUp branded, **inbox placement "
        "+ DKIM/SPF/DMARC PASS**, alarm OK. **5 design deviations resolved at implementation** "
        "(design-doc post-implementation note + DevOps appendix): Cognito encrypts via the **AWS "
        "Encryption SDK envelope** (not raw `kms.decrypt` → `InvalidCiphertextException`), "
        "CommitmentPolicy `REQUIRE_ENCRYPT_ALLOW_DECRYPT`, sendgrid secret JSON key is `api_key`, "
        "512 MB for the crypto footprint, `CustomEmailSender` CLI takes a `{LambdaArn,LambdaVersion}` "
        "dict. Docs flipped LIVE by the engineer (cognito-prod-setup, runbook §14.5, env-mgmt, "
        "as-built). Rollback documented: detach trigger → instant `COGNITO_DEFAULT` fallback.\n\n"
    )
    plan = replace_once(
        plan, "\n**Archives**:", "\n" + changelog + "**Archives**:", "v7.30 changelog"
    )

    # 3. Ord 15 row → ✅
    row15 = (
        "| 15 | **COGNITO-EMAIL-1** 🆕 | Cognito auth emails via SendGrid custom sender "
        "(signup/forgot/invite, branded) — **✅ 2026-09-03 (A: 4787→4829 +42; B: LIVE, "
        "DKIM/SPF/DMARC PASS; §7 gate row ✅)** | Python → DevOps | none | ✅ 2026-09-03 |"
    )
    plan = rewrite_line_starting(
        plan, "| 15 | **COGNITO-EMAIL-1**", row15, "Ord 15 row"
    )

    # 4. Card §3.15 heading + Closed line
    plan = replace_once(
        plan,
        "### 3.15 — COGNITO-EMAIL-1 🆕: Cognito Auth Emails via SendGrid Custom Sender",
        "### 3.15 — COGNITO-EMAIL-1 🆕: Cognito Auth Emails via SendGrid Custom Sender ✅ Closed 2026-09-03",
        "§3.15 heading",
    )
    closed_line = (
        "**Closed 2026-09-03** — Part A: 4787→4829 (+42 tests; handler + 3 branded flows). Part B: "
        "LIVE — Lambda + alarm + IAM role deployed; one-call wiring (all 3 triggers + KMSKeyID; "
        "EmailSendingAccount + Sms/Device unchanged). Smokes: ForgotPassword + SignUp branded, inbox "
        "placement, DKIM/SPF/DMARC PASS. **Design deviations resolved at implementation** (design-doc "
        "post-implementation note + DevOps appendix): AWS Encryption SDK envelope decrypt (not raw "
        "KMS), CommitmentPolicy, secret JSON key `api_key`, 512 MB, CLI dict syntax. §7 gate row ✅. "
        "Completion summaries: [`batch-cognito-email-1-python-engr-prompt.md`](../implementation-prompts/fe-be-mob-batch-prompts/batch-cognito-email-1-python-engr-prompt.md) (Part A) · "
        "[`batch-cognito-email-1-devops-prompt.md`](../devops/prompts/batch-cognito-email-1-devops-prompt.md) (Part B)."
    )
    plan = insert_after_line_starting(
        plan,
        "### 3.15 — COGNITO-EMAIL-1 🆕: Cognito Auth Emails via SendGrid Custom Sender ✅ Closed 2026-09-03",
        closed_line,
        "§3.15 closed line",
    )

    # 5. §7 gate row → ✅
    plan = rewrite_line_starting(
        plan,
        "| COGNITO-EMAIL-1 closed —",
        "| COGNITO-EMAIL-1 closed — signup/invite auth emails via SendGrid custom sender (branded; "
        "inbox placement + DKIM/SPF smoke) | Python + DevOps | ✅ 2026-09-03 |",
        "§7 gate row",
    )

    # 6. Appendix A-3 row after the Prod seed re-converge row
    a3_row = (
        "| COGNITO-EMAIL-1 | 2026-09-03 | Cognito auth emails via SendGrid Custom Email Sender — "
        "branded signup/forgot/invite; DKIM/SPF/DMARC PASS; §7 gate row ✅ | "
        "[design](../architecture-design/batch-designs/batch-cognito-email-1-design.md) · "
        "[BE](../implementation-prompts/fe-be-mob-batch-prompts/batch-cognito-email-1-python-engr-prompt.md) · "
        "[DevOps](../devops/prompts/batch-cognito-email-1-devops-prompt.md) |"
    )
    plan = insert_after_line_starting(
        plan, "| Prod seed re-converge (ops)", a3_row, "A-3 row"
    )

    PLAN.write_text(plan, encoding="utf-8")
    print(
        "DONE — COGNITO-EMAIL-1 closed (launch plan v7.30: Ord 15 ✅, card closed, §7 gate ✅, A-3 row)."
    )


if __name__ == "__main__":
    main()
