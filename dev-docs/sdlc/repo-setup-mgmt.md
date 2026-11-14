# Pilot for Trades GitHub.com Repo Setup & Configuration

**Purpose:** Setup & configuration steps for the Pilot for Trades repo in github.com.

**Last Updated:** 2026-03-28  

### Step 0: Push all local changes to github (main)

Before you touch anything in the GitHub interface, run this on your laptop:

```bash
# Make sure you are on your current main branch
git checkout main

# Review changes, add all files for commit, double check files, stage and commit any pending work
git status
git add .
git status
git commit -m "chore: final commit to main before restructuring branches"

# Push it all up to GitHub
git push origin main
```

### Step 1: Rename `main` to `prod`
Since you want a dedicated `prod` branch, the cleanest approach is to rename your existing `main` branch. This preserves your entire commit history exactly as it is.

1. Go to your repository on **GitHub.com**.
2. Click on **Settings** (the gear icon tab at the top).
3. In the left sidebar, click on **General** (it should be the default page).
4. Scroll down to the **Default branch** section.
5. Click the **pencil icon** (Rename default branch) next to `main`.
6. Type `prod` and click **Rename**.

### Step 2: Create Your New Branches
Now we will create the pipeline branches, branching them off of `prod` so they all start with the exact same history.

1. Go back to the main **Code** tab of your repository.
2. Click the **branch dropdown menu** (it now says `prod` with a little branching icon).
3. In the text box, type `demo`.
4. Click the text that appears saying **Create branch: demo from 'prod'**.
5. Repeat this process two more times:
   * Type `qa` and click **Create branch: qa from 'prod'**.
   * Type `dev` and click **Create branch: dev from 'prod'**.

### Step 3: Change the Default Branch to `dev`
This is a critical, often-missed step. By making `dev` the default branch, any future feature branches you push will automatically request to merge into `dev` instead of `prod`.

1. Go back to **Settings**.
2. In the left sidebar, click on **General**.
3. Scroll down to the **Default branch** section.
4. Click the **two arrows icon** (Switch default branch) next to `prod`.
5. Select `dev` from the dropdown and click **Update**. Click **I understand, update default branch** on the warning prompt.

### Step 4: Apply Branch Protection Rules
Now we lock down the environment branches so you are forced to use Pull Requests, preventing accidental direct pushes from your laptop.

1. In **Settings**, click on **Branches** in the left sidebar (under "Code and automation").
2. Click the **Add branch protection rule** button.
3. **Rule 1: Production**
   * **Branch name pattern:** Type `prod`
   * Check **Require a pull request before merging**. (Since you are solo, you can leave "Require approvals" unchecked or set to 0, which still forces a PR but doesn't block you waiting for another human).
   * Check **Require status checks to pass before merging**. (We will leave the specific checks blank for now until we build your Actions).
   * Check **Do not allow bypassing the above settings**. (This forces *you*, even as the admin, to follow the rules).
   * Click **Create** at the bottom.
4. **Rule 2: Demo**
   * Click **New rule**.
   * **Branch name pattern:** Type `demo`
   * Check the exact same three boxes as you did for `prod`.
   * Click **Create**.
5. **Rule 3: QA**
   * Click **New rule**.
   * **Branch name pattern:** Type `qa`
   * Check the exact same three boxes.
   * Click **Create**.
6. **Rule 4: Dev**
   * Click **New rule**.
   * **Branch name pattern:** Type `dev`
   * Check the exact same three boxes.
   * Click **Create**.

### Step 5: Sync Your Local Laptop
Your GitHub repo is now perfectly structured, but your laptop still thinks there is only a `main` branch. Open your terminal on your laptop, navigate to your `pilot` folder, and run these commands:

```bash
# Fetch all the new branches and remove the remote tracking for 'main'
git fetch origin --prune

# Rename your local 'main' to 'prod' and link it to the remote 'prod'
git branch -m main prod
git branch -u origin/prod prod

# Pull down your new working branch, 'dev'
git checkout dev
```
