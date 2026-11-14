# QA Workflow Logs

This directory stores **implementation task logs** for each Cosmic Ray mutation testing remediation session.

## What Goes Here

One markdown file per QA workflow run, tracking:
- The session report that triggered the work
- Baseline test count and pass status before changes
- Each surviving mutant occurrence group and how it was addressed
- Each new test written (file, function name, what it asserts)
- Final validation results (all tests passing, score before → after)

## Git-Tracked (NOT gitignored)

Unlike `sessions/` (which is gitignored), these files are **committed to the repository**. They serve as the permanent implementation record that can be reviewed, referenced, and linked to PRs.

## Naming Convention

```
YYYY-MM-DD_<tier>-<type>-<slug>_qa-workflow.md
```

The slug must match the session directory slug for cross-referencing:
- `2026-05-30_tier1-group-sms-quota_qa-workflow.md`
- `2026-05-30_tier1-file-billing-rate-service_qa-workflow.md`

OR

The slug must match the session file slug for smoke tests:
- `2026-05-29_18-51-10_smoke-sms-quota_qa-workflow.md`

## For Full Instructions

See [`backend/README-cosmic-ray.md`](../../../README-cosmic-ray.md) → **QA Workflow Log Files** section.
