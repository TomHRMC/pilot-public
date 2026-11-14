# Git Workflow v1.6 - Analysis & Recommendations

**Date:** 2026-03-28  
**Reviewer:** Pilot for Trades Architect  
**Status:** Pending Approval

---

## Executive Summary

Your original `dev-git-commands-reference.md` (v1.5) was excellent for **feature branch workflows** but had critical gaps for your new **four-tier branch structure** (`dev/qa/demo/prod`). The proposed v1.6 addresses these gaps with **environment promotion workflows** and **hotfix strategies**.

---

## Critical Issues in v1.5

### 1. **Outdated Branch References** 🔴 HIGH PRIORITY
- **Lines 16, 96:** Referenced `master` instead of `prod`
- **Missing:** `demo` branch entirely absent from documentation
- **Impact:** Confusing for new team members; doesn't match actual repo structure

### 2. **Missing Branch Promotion Workflows** 🔴 HIGH PRIORITY
- **Gap:** No instructions for `dev` → `qa` → `demo` → `prod` promotions
- **Current state:** Document only covers feature → `dev` merges
- **Impact:** You're working by default on `dev`, but how do you deploy to QA? Demo? Prod?
- **Risk:** Ad-hoc promotions lead to inconsistent deploys and potential production issues

### 3. **No Hotfix Strategy** 🟠 MEDIUM PRIORITY
- **Gap:** No workflow for emergency production fixes
- **Impact:** Critical bugs in prod require bypassing the normal pipeline
- **Risk:** Without a documented hotfix process, you may:
  - Deploy untested code to prod
  - Forget to backport fixes to `dev/qa/demo`
  - Create divergent branch histories

### 4. **Unclear Merge Strategies** 🟡 LOW PRIORITY
- **Gap:** Doesn't specify when to use squash vs. merge commit vs. rebase
- **Impact:** Inconsistent git history makes troubleshooting harder
- **Best practice:**
  - **Squash merge:** Feature → `dev` (clean history)
  - **Merge commit:** Environment promotions (preserve deployment history)
  - **Rebase:** Pre-PR cleanup (linear history)

---

## What's New in v1.6

### ✅ **Section 2: Branch Structure Table**
Added a comprehensive table mapping branches to:
- AWS environments
- Protection status
- Merge strategies
- Purpose/use case

**Why it matters:** Single source of truth for "which branch maps to which environment."

### ✅ **Section 6: Branch Promotion Workflows** (NEW)
Detailed step-by-step instructions for:

1. **`dev` → `qa` Promotion**
   - When to promote (features merged, tests pass)
   - How to create PR via GitHub UI
   - Merge strategy (merge commit, not squash)
   - Post-deployment verification

2. **`qa` → `demo` Promotion**
   - QA sign-off required
   - Demo data integrity checks
   - Stakeholder notification

3. **`demo` → `prod` Promotion**
   - Critical production checklist
   - Rollback plan requirement
   - Manual approval gates
   - Post-deployment monitoring
   - Git tagging for releases (`v1.2.3`)

4. **CLI Alternative**
   - Commands for local merge preparation
   - Still requires PR approval (GitHub protections)

**Why it matters:** You now have a repeatable, documented process for deploying through all environments.

### ✅ **Section 7: Hotfix Workflows** (NEW)
Emergency production fix process:

1. Branch from `prod` (not `dev`)
2. Minimal fix, thorough testing
3. Deploy to `prod` via PR
4. **Backport to `demo/qa/dev`** using cherry-pick
5. Clean up hotfix branch

**Why it matters:** Prevents "hotfix amnesia" where emergency fixes are forgotten in lower environments, causing regressions on the next normal release.

### ✅ **Updated Section 4: Syncing Shared Branches**
- Changed `master` → `prod`
- Added `demo` to examples
- Included one-liner commands for all four environment branches

### ✅ **Expanded Section 9: Troubleshooting**
- Added "undo a promotion" scenario (rollback `qa` or `demo`)
- Warning about never force-pushing to `prod`

---

## Architectural Alignment

### Cost-Optimized MVP Principle ✅
The git workflow supports your infrastructure constraints:
- **Four environments** align with your Terraform-managed AWS resources
- **PR-based promotions** prevent accidental deployments that could spin up unintended resources
- **Merge commit strategy** for promotions preserves audit trail for cost tracking

### Scaling Logic ✅
- **Hotfix process** enables rapid fixes without full pipeline traversal
- **Branch protection** prevents direct commits that could bypass CI/CD cost controls
- **Tagging** (`v1.2.3`) enables infrastructure versioning for Terraform state management

---

## Recommended Next Steps

### 1. **Review & Approve v1.6** (This Document)
- [ ] Review proposed changes in `dev-git-commands-reference-v1.6-PROPOSED.md`
- [ ] Decide: Adopt v1.6 or request modifications

### 2. **Update GitHub Branch Protections** (If Not Already Set)
Ensure GitHub settings match v1.6 documentation:

```
Branch: prod
- Require pull request before merging: ✅
- Require approvals: 1
- Dismiss stale reviews: ✅
- Require status checks: ✅ (GitHub Actions: deploy-prod)
- Restrict pushes: ✅ (Only admins)

Branch: demo
- Require pull request before merging: ✅
- Require status checks: ✅ (GitHub Actions: deploy-demo)

Branch: qa
- Require pull request before merging: ✅
- Require status checks: ✅ (GitHub Actions: deploy-qa)

Branch: dev
- Require pull request before merging: ⚠️ (Recommended but optional for solo dev)
- Allow squash merging: ✅
```

### 3. **Test the Promotion Workflow** (Dry Run)
Before relying on v1.6 in production, do a test run:

1. Create a test feature branch
2. Merge to `dev`
3. Promote `dev` → `qa` (verify GitHub Actions trigger)
4. Promote `qa` → `demo`
5. Promote `demo` → `prod` (verify approval gate works)

### 4. **Document AWS Environment Mapping** (Complement to v1.6)
Create a companion doc:
- **`dev-docs/sdlc/aws-environment-mapping.md`**
- Maps each branch to specific AWS resources:
  - `dev` → ECS cluster: `pilot-dev`, RDS: `pilot-db-dev`, etc.
  - `qa` → ECS cluster: `pilot-qa`, RDS: `pilot-db-qa`, etc.
  - `demo` → ECS cluster: `pilot-demo`, RDS: `pilot-db-demo`, etc.
  - `prod` → ECS cluster: `pilot-prod`, RDS: `pilot-db-prod`, etc.

### 5. **Consider GitHub Actions Workflow Updates**
Your `.github/workflows/deploy.yml` should match the v1.6 promotion strategy:

```yaml
name: Deploy to AWS

on:
  push:
    branches:
      - dev
      - qa
      - demo
      - prod

jobs:
  deploy-dev:
    if: github.ref == 'refs/heads/dev'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Dev ECS
        uses: aws-actions/amazon-ecs-deploy-task-definition@v1
        # ... deploy to dev environment

  deploy-qa:
    if: github.ref == 'refs/heads/qa'
    runs-on: ubuntu-latest
    environment: QA  # Requires GitHub Environment setup
    steps:
      - name: Deploy to QA ECS
        # ... deploy to qa environment

  deploy-demo:
    if: github.ref == 'refs/heads/demo'
    runs-on: ubuntu-latest
    environment: Demo
    steps:
      - name: Deploy to Demo ECS
        # ... deploy to demo environment

  deploy-prod:
    if: github.ref == 'refs/heads/prod'
    runs-on: ubuntu-latest
    environment: Production  # Requires manual approval
    steps:
      - name: Deploy to Prod ECS
        # ... deploy to prod environment
      - name: Create GitHub Release
        # ... tag release with version
```

---

## Decision Matrix

| Action | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **Adopt v1.6 as-is** | Comprehensive coverage, production-ready | May be overkill for solo dev | ✅ **Recommended** |
| **Adopt v1.6 with simplifications** | Tailored to current team size | Still need to define simplifications | ⚠️ Consider if overwhelmed |
| **Keep v1.5** | No change required | Missing critical promotion workflows | ❌ **Not Recommended** |

---

## Conclusion

Your v1.5 documentation was solid for **feature development**, but your new four-tier branch structure requires **environment promotion workflows** to be production-ready. The proposed v1.6 addresses these gaps with:

1. **Section 6:** Step-by-step promotion guides
2. **Section 7:** Hotfix workflows for emergencies
3. **Updated branch references** (`master` → `prod`, added `demo`)
4. **Merge strategy clarity** (squash vs. merge commit)

**Next Action:** Review `dev-git-commands-reference-v1.6-PROPOSED.md` and decide whether to adopt it.

---

## Questions for Consideration

1. **Approval Gates:** Do you want manual approval for `demo` → `prod` only, or also for `qa` → `demo`?
2. **Hotfix Frequency:** How often do you anticipate needing hotfixes? (Affects whether Section 7 needs more detail)
3. **Squash Strategy:** Should feature → `dev` always be squash-merged, or allow merge commits for multi-commit features?
4. **Version Tagging:** Do you want semantic versioning (`v1.2.3`) or date-based (`v2026.03.28`)?

Let me know if you'd like me to adjust any of these recommendations!
