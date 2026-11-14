# Pilot for Trades - Git Commands Reference

**Version:** 1.6 (PROPOSED)
**Last Updated:** 2026-03-28
**Status:** Pending Review

---

## Table of Contents

- [1. Core Concepts](#1-core-concepts)
- [2. Branch Structure](#2-branch-structure)
- [3. Daily Workflows](#3-daily-workflows)
  - [Starting a New Feature](#starting-a-new-feature)
  - [Saving Your Work (Commit & Push)](#saving-your-work-commit--push)
- [4. Syncing & Updating](#4-syncing--updating)
  - [Updating Shared Branches (dev, qa, demo, prod)](#updating-shared-branches-dev-qa-demo-prod)
- [5. Before Submitting PR](#5-before-submitting-pr)
  - [Check: Do I Need to Rebase?](#check-do-i-need-to-rebase)
  - [Updating Your Feature Branch (Rebase)](#updating-your-feature-branch-rebase)
- [6. Branch Promotion Workflows](#6-branch-promotion-workflows)
  - [Promoting dev → qa](#promoting-dev--qa)
  - [Promoting qa → demo](#promoting-qa--demo)
  - [Promoting demo → prod](#promoting-demo--prod)
- [7. Hotfix Workflows](#7-hotfix-workflows)
  - [Emergency Production Fixes](#emergency-production-fixes)
- [8. Advanced Feature Management](#8-advanced-feature-management)
  - [Cleaning Up Commit History (The "Reset & Cherry-Pick" Method)](#cleaning-up-commit-history-the-reset--cherry-pick-method)
  - [Checking Your Branch Status](#checking-your-branch-status)
- [9. Troubleshooting & Fixes](#9-troubleshooting--fixes)
  - [Resolving Conflicts (The "Theirs" vs "Ours" Way)](#resolving-conflicts-the-theirs-vs-ours-way)
  - [Force Pushing Safely](#force-pushing-safely)
  - [Common Scenarios](#common-scenarios)
- [10. Configuration](#10-configuration)
- [11. Revision Log](#11-revision-log)

---

## 1. Core Concepts

### `git switch` vs. `git checkout`
*   **`git switch` (Modern):** Use this for **changing branches**. It's safer and clearer.
    *   `git switch dev`
    *   `git switch -c feature/new-thing` (Create & Switch)
*   **`git checkout` (Legacy):** Do not use for switching branches. Use only for restoring files if needed (though `git restore` is preferred).

### `git restore`
*   **Use this to discard local changes** to files.
    *  Reverts file to last commit state
    ```bash
    git restore backend/app/main.py
    ```

---

## 2. Branch Structure

Pilot for Trades uses a **four-tier promotional pipeline** to ensure code quality and enable safe deployments:

| Branch | Purpose | AWS Environment | Protected | Merge Strategy |
|--------|---------|-----------------|-----------|----------------|
| **`prod`** | Stable, customer-facing code | Production | ✅ Yes | Merge Commit (from `demo`) |
| **`demo`** | Stable code with pristine mock data | Demo / Sales | ✅ Yes | Merge Commit (from `qa`) |
| **`qa`** | Release candidates for testing | QA / Staging | ✅ Yes | Merge Commit (from `dev`) |
| **`dev`** | Integration branch for all features | Development | ⚠️ Partial | Squash (from `feature/*`) |
| **`feature/*`** | Short-lived branches for specific tasks | Local Laptop | ❌ No | N/A |
| **`hotfix/*`** | Emergency production fixes | Local Laptop | ❌ No | Cherry-pick to `prod` |

### Key Rules:
1. **Never commit directly** to `prod`, `demo`, or `qa` — use PRs only.
2. **Always work on `dev`** by default (or `feature/*` branches from `dev`).
3. **Promotion is unidirectional:** `dev` → `qa` → `demo` → `prod` (except hotfixes).
4. **Feature branches merge into `dev` only** (never into `qa`, `demo`, or `prod`).

---

## 3. Daily Workflows

### Starting a New Feature
1.  **Sync your base branch** (always start fresh).
    *  This is preferred over `git pull` as it ensures you are 100% in sync with remote dev.
    *  We run `git fetch` first to update our local knowledge of the server, then `reset` to match it exactly.
    ```bash
    git switch dev
    git fetch origin
    git reset --hard origin/dev
    ```
2.  **Create your branch.**
    *  This both creates the branch using the `-c` flag and then switches to it.
    ```bash
    git switch -c feature/my-new-feature
    ```

### Saving Your Work (Commit & Push)
1.  **Stage files** (prepare them for commit).
    *   Moves changes from your working directory to the "staging area", ready to be saved.
    *   Using the `.` takes all files that are tracked and untracked and stages them.
    ```bash
    git add .
    # OR you can stage specific files: git add backend/api/routes/voice.py
    ```
2.  **Check Status** (check that the files were added successfully).
    *   Double check that the git add . worked.
    ```bash
    git status
    ```
3.  **Commit** (save history locally).
    *   Creates a local permanent snapshot of your staged changes with a message describing the work.
    ```bash
    git commit -m "feat: add voice intent classification"
    ```
4.  **Push** (send to server).
    *   Uploads your local commits to the remote repository so others can see them.
    *   The `-u` flag links your local branch to the remote one.
    ```bash
    git push -u origin feature/my-new-feature
    ```
    > **Tip:** If the `dev` branch has been updated by others since you started, you must **Rebase** (Section 5) before your PR can be merged. If `dev` hasn't changed, you can skip rebasing.

---

## 4. Syncing & Updating

### Updating Shared Branches (dev, qa, demo, prod)
**Rule:** Never manually merge or commit to these local branches. Always make them match the remote server exactly.

1.  **Switch to the branch.**
    ```bash
    git switch dev  # or qa, demo, prod
    ```
2.  **Reset to match remote** (safest method for shared branches).
    *   `fetch` gets the latest updates from the server without merging.
    *   `reset --hard` forces your local branch to match the remote exactly, discarding any local divergence.
    ```bash
    git fetch origin
    git reset --hard origin/dev  # or origin/qa, origin/demo, origin/prod
    ```

**Example for all environment branches:**
```bash
# Update dev
git switch dev
git fetch origin && git reset --hard origin/dev

# Update qa
git switch qa
git fetch origin && git reset --hard origin/qa

# Update demo
git switch demo
git fetch origin && git reset --hard origin/demo

# Update prod
git switch prod
git fetch origin && git reset --hard origin/prod
```

---

## 5. Before Submitting PR

### Check: Do I Need to Rebase?
Before you rebase, verify if the `dev` branch has actually changed since you started.

1.  **Fetch the latest data:**
    ```bash
    git fetch origin
    ```
2.  **Check for new commits on dev:**
    *   This command asks: "Show me commits in `origin/dev` that are NOT in my current branch".
    ```bash
    git log --oneline HEAD..origin/dev
    ```

**Scenario A: Output is Empty (No Rebase Needed)**
*   **Result:** No output is returned (just returns to command prompt).
*   **Meaning:** `origin/dev` has NO new commits. You are up to date.
*   **Action:** Skip rebase. You can just `push`.

**Scenario B: Output Shows Commits (Rebase Needed)**
*   **Result:** A list of commits appears.
    ```
    a1b2c3d feat: updated login logic
    e5f6g7h fix: corrected typo in header
    ```
*   **Meaning:** `origin/dev` has advanced (moved ahead). Your branch is "behind".
*   **Action:** Proceed to **Updating Your Feature Branch (Rebase)** below.

### Updating Your Feature Branch (Rebase)
This brings new changes from `dev` into your branch by "replaying" your work on top of them. **You only need to do this if Scenario B (above) occurred.**

1.  **Update local dev first** (see Section 4).
    *   Ensures you are rebasing onto the latest stable code.
2.  **Rebase your feature branch.**
    *   Rewrites your branch history so your commits appear *after* the latest dev changes. This keeps history clean.
    ```bash
    git switch feature/my-feature
    git rebase origin/dev
    ```
3.  **If conflicts occur:** See Section 9.
4.  **Finish:** You must force push after rebasing.
    *   Required because rebasing rewrites commit history.
    *   It performs a check before force-pushing: "Is the remote branch still where I think it is?"
    ```bash
    git push --force-with-lease
    ```

---

## 6. Branch Promotion Workflows

### Overview
Once your features are merged into `dev`, you'll need to **promote code through the pipeline** to reach production. These promotions happen via **Pull Requests** and trigger AWS deployments via GitHub Actions.

### Promoting dev → qa

**When:** After features are merged into `dev` and you're ready for QA testing.

1.  **Ensure `dev` is stable:**
    *   All feature PRs are merged.
    *   Local tests pass.
    ```bash
    git switch dev
    git pull origin dev
    # Run tests locally if needed
    ```

2.  **Create PR via GitHub:**
    *   Go to GitHub → Pull Requests → New Pull Request
    *   Base: `qa` ← Compare: `dev`
    *   Title: `Release: [Date] - Dev to QA`
    *   Description: List major features/fixes included
    
3.  **Review & Merge:**
    *   Review the changeset (should show all commits since last QA deployment)
    *   Use **"Create a merge commit"** strategy (NOT squash)
    *   Merge the PR
    
4.  **Verify deployment:**
    *   GitHub Actions will deploy to AWS QA environment
    *   Check CloudWatch logs if needed

### Promoting qa → demo

**When:** After QA testing passes and you want to update the demo environment for sales/stakeholders.

1.  **Ensure `qa` is tested:**
    *   All QA tests pass
    *   No critical bugs
    
2.  **Create PR via GitHub:**
    *   Base: `demo` ← Compare: `qa`
    *   Title: `Release: [Date] - QA to Demo`
    *   Description: Summarize what's new for demo environment
    
3.  **Review & Merge:**
    *   Use **"Create a merge commit"** strategy
    *   Merge the PR
    
4.  **Verify deployment:**
    *   Check demo environment is updated
    *   Verify pristine demo data is intact

### Promoting demo → prod

**When:** After stakeholder sign-off and readiness for production release.

⚠️ **CRITICAL: This deploys to customer-facing production.**

1.  **Final checks:**
    *   Demo environment tested by stakeholders
    *   All acceptance criteria met
    *   Database migrations tested
    *   Rollback plan documented
    
2.  **Create PR via GitHub:**
    *   Base: `prod` ← Compare: `demo`
    *   Title: `Release: v[X.Y.Z] - Demo to Production`
    *   Description: 
        - Full changelog
        - Migration steps (if any)
        - Rollback plan
        - Monitoring checklist
    
3.  **Review & Merge (with approval):**
    *   GitHub will require manual approval (see Environment Protection Rules)
    *   Use **"Create a merge commit"** strategy
    *   Merge the PR
    
4.  **Post-deployment:**
    *   Monitor CloudWatch for errors
    *   Verify critical paths (login, voice AI, QuickBooks sync)
    *   Tag the release: `git tag v1.2.3 && git push origin v1.2.3`

### Local Commands for Promotion (Alternative)

If you prefer CLI-based promotions (still requires PR approval in GitHub):

```bash
# Promote dev → qa
git switch qa
git fetch origin
git reset --hard origin/qa
git merge origin/dev --no-ff -m "chore: promote dev to qa [DATE]"
git push origin qa

# Promote qa → demo
git switch demo
git fetch origin
git reset --hard origin/demo
git merge origin/qa --no-ff -m "chore: promote qa to demo [DATE]"
git push origin demo

# Promote demo → prod
git switch prod
git fetch origin
git reset --hard origin/prod
git merge origin/demo --no-ff -m "release: promote demo to prod v[X.Y.Z]"
git push origin prod
git tag -a v1.2.3 -m "Release v1.2.3: [description]"
git push origin v1.2.3
```

> ⚠️ **Note:** Even with local commands, GitHub branch protections will still require PRs. This approach is useful for preparing the merge locally before opening the PR.

---

## 7. Hotfix Workflows

### Emergency Production Fixes

**When:** Critical bug in production that can't wait for the normal `dev` → `qa` → `demo` → `prod` pipeline.

1.  **Create hotfix branch from `prod`:**
    ```bash
    git switch prod
    git fetch origin
    git reset --hard origin/prod
    git switch -c hotfix/critical-voice-ai-crash
    ```

2.  **Make minimal fix:**
    *   Change only what's necessary
    *   Test thoroughly locally
    ```bash
    # Make your fix
    git add .
    git commit -m "hotfix: prevent crash when Whisper API times out"
    git push -u origin hotfix/critical-voice-ai-crash
    ```

3.  **Deploy to production (PR to prod):**
    *   GitHub: Create PR from `hotfix/*` → `prod`
    *   Get emergency approval
    *   Merge using **"Create a merge commit"**
    *   Tag immediately: `git tag v1.2.4-hotfix`

4.  **Backport to other branches:**
    *   The fix must also go to `demo`, `qa`, and `dev` to prevent regression.
    
    **Option A: Cherry-pick (preferred):**
    ```bash
    # Get the hotfix commit SHA
    git log --oneline -1 origin/prod
    # (Copy the SHA, e.g., abc1234)
    
    # Apply to demo
    git switch demo
    git fetch origin && git reset --hard origin/demo
    git cherry-pick abc1234
    git push origin demo
    
    # Apply to qa
    git switch qa
    git fetch origin && git reset --hard origin/qa
    git cherry-pick abc1234
    git push origin qa
    
    # Apply to dev
    git switch dev
    git fetch origin && git reset --hard origin/dev
    git cherry-pick abc1234
    git push origin dev
    ```
    
    **Option B: Merge hotfix branch (if cherry-pick fails):**
    ```bash
    git switch dev
    git merge --no-ff hotfix/critical-voice-ai-crash
    git push origin dev
    ```

5.  **Clean up:**
    ```bash
    git branch -d hotfix/critical-voice-ai-crash
    git push origin --delete hotfix/critical-voice-ai-crash
    ```

---

## 8. Advanced Feature Management

### Cleaning Up Commit History (The "Reset & Cherry-Pick" Method)
Use this if your branch has messy history, merged old commits, or you want to combine everything into one clean commit.

1.  **Identify the commit(s) you want to keep.**
    *   Find the unique SHA hash for your specific work commits.
    ```bash
    git log --oneline
    # Copy the SHA (e.g., a1b2c3d) of your work
    ```
2.  **Reset your branch to the latest `dev`.**
    *   This wipes your branch clean and makes it identical to the latest dev branch. Your work is removed from the branch history but still exists in Git's "reflog" memory.
    ```bash
    git reset --hard origin/dev
    ```
3.  **Retrieve lost commit hashes (if needed).**
    *   If you cleared your terminal or forgot the SHA from Step 1, use the "Reference Log" to find where your branch pointer was before the reset.
    ```bash
    git reflog
    # Look for the commit before "reset: moving to origin/dev"
    ```
4.  **Cherry-pick your work back.**
    *   Re-applies your specific commit onto the clean branch.
    ```bash
    git cherry-pick a1b2c3d
    ```
5.  **Verify.**
    *   Ensures only your intended commit(s) are on top of dev.
    ```bash
    git log --oneline origin/dev..HEAD
    ```

### Checking Your Branch Status
Verify exactly what you are about to push or PR.

*   **Count commits ahead of dev:**
    *   Quick number check (should be 1 or small number).
    ```bash
    git rev-list --count origin/dev..HEAD
    ```
*   **See the actual commits:**
    *   Lists the specific commits that will be in your Pull Request.
    ```bash
    git log --oneline origin/dev..HEAD
    ```
*   **Check sync status (Ahead/Behind):**
    *   Verifies if your local branch matches the remote tracking branch.
    ```bash
    git branch -vv
    ```

---

## 9. Troubleshooting & Fixes

### Resolving Conflicts (The "Theirs" vs "Ours" Way)
When a rebase pauses for conflicts:

1.  **Accept YOUR changes (Incoming/Theirs):**
    *   "Theirs" refers to the branch you are applying (your feature branch) during a rebase.
    ```bash
    git checkout --theirs path/to/file.ts
    ```
2.  **Accept DEV changes (Current/Ours):**
    *   "Ours" refers to the base branch you are rebasing onto (dev).
    ```bash
    git checkout --ours path/to/file.ts
    ```
3.  **After choosing:**
    *   Mark the conflict as resolved and continue the rebase process.
    ```bash
    git add path/to/file.ts
    git rebase --continue
    ```

### Force Pushing Safely
When you rebase or amend commits, you rewrite history. You cannot do a normal push.

*   **Command:**
    *   This is the safe alternative to `--force`. It checks if anyone else has pushed to the branch before overwriting it.
    ```bash
    git push --force-with-lease
    ```

### Common Scenarios

#### "I started work on `dev` by accident"
You have uncommitted changes on `dev`, but you should be on a feature branch.

1.  **Stash your changes with a message:**
    ```bash
    git stash push -u -m "WIP: My new feature work"
    ```
    *   `-u` includes new (untracked) files.
    *   `-m` gives it a name so you can find it later.

2.  **Reset `dev` to match remote:** (Clean slate)
    ```bash
    git fetch origin
    git reset --hard origin/dev
    ```

3.  **Create your new feature branch:**
    ```bash
    git switch -c feature/my-new-feature
    ```

4.  **Pop your stash:** (Bring changes back)
    ```bash
    git stash pop
    ```
    *Your changes are now on the new branch, ready to commit.*

#### "My PR shows 10+ commits but I only made 1"
**Cause:** Your branch was based on an old version of `dev`.
**Fix:** Rebase onto the current `origin/dev` (Section 5) or use the "Reset & Cherry-Pick" method (Section 8).

#### "Git status says I have diverged branches"
**Cause:** You rebased locally, so your local history is different from remote.
**Fix:** Trust your local rebased version and force push (`git push --force-with-lease`).

#### "I need to undo a promotion (e.g., rollback qa)"
**Cause:** Bad code was promoted to `qa` and needs to be reverted.
**Fix:** Reset the environment branch to a previous good commit.

```bash
# Find the last good commit
git switch qa
git log --oneline -20  # Find the SHA before the bad merge

# Reset qa to that commit
git reset --hard abc1234  # Use the good commit SHA
git push --force-with-lease origin qa
```

⚠️ **Warning:** This rewrites history. Only do this for `qa` or `demo`. Never force-push to `prod`.

---

## 10. Configuration

### Setup Identity
```bash
git config --global user.name "Your Name"
git config --global user.email "you@company.com"
```

### Auto-CRLF (Line Endings)
Create a `.gitattributes` file in root:
```
* text=auto
```

### Ignored Files
Add to `.gitignore`:
```
.vscode/
.env
node_modules/
bin/
obj/
__pycache__/
*.pyc
.pytest_cache/
.coverage
```

---

## 11. Revision Log

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-03-28 | 1.6 | Tom Lang | **MAJOR UPDATE:** Updated for four-tier branch structure (`dev/qa/demo/prod`). Added Section 6 (Branch Promotion Workflows) with detailed promotion instructions for each tier. Added Section 7 (Hotfix Workflows) for emergency production fixes. Updated Section 2 with branch structure table. Changed all `master` references to `prod`. Added `demo` to all shared branch lists. Expanded troubleshooting scenarios. Renumbered subsequent sections. |
| 2026-02-06 | 1.5 | Tom Lang | Restructured document to create a dedicated "Before Submitting PR" section (Section 4), moving rebase checks and instructions there. Renumbered subsequent sections. |
| 2026-02-06 | 1.4 | Tom Lang | Added "Check: Do I Need to Rebase?" section with specific commands (`git log HEAD..origin/dev`) and example outputs for both scenarios. |
| 2026-02-06 | 1.3 | Tom Lang | Clarified that rebasing is conditional on `dev` having new changes since feature start. Added tips to "Saving Your Work". |
| 2026-02-03 | 1.2 | Tom Lang | Added `git fetch origin` to "Starting a New Feature" workflow to ensure local remote references are up-to-date before resetting. |
| 2026-02-03 | 1.1 | Tom Lang | Added rebase workflows, shared branch reset patterns, conflict resolution strategies (`checkout --theirs`), history cleanup methods (including reflog), and detailed stashing examples. Added explanatory notes to command steps. |
| 2026-01-XX | 1.0 | Tom Lang | Initial creation. |
