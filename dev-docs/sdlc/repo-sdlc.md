## 1. The Architectural Plan: Monorepo vs. Polyrepo
Since you’re adding a front end, you have a choice:
* **The Monorepo (Recommended):** Keep the frontend and backend in the same GitHub repo (e.g., folders `/client` and `/server`). This makes it easier to manage "atomic" changes where a frontend feature depends on a new backend API endpoint.
* **The Polyrepo:** Separate repos. This is better if the teams are different, but for a solo dev or small team, it adds significant overhead in syncing versions.

**Verdict:** Stick to a **Monorepo** for now to keep your deployment logic (GitHub Actions) in one place.

---

## 2. The Branching Strategy
You’ve already outlined a solid hierarchy. Here is how to map that to GitHub’s features:

| Branch | Purpose | AWS Environment |
| :--- | :--- | :--- |
| **`prod`** | Stable, customer-facing code. | Production |
| **`demo`** | Stable code with "pristine" mock data. | Demo / Sales |
| **`qa`** | Release candidates for testing. | QA / Staging |
| **`dev`** | Integration branch for all features. | Development |
| **`feature/*`** | Short-lived branches for specific tasks. | Local Laptop |

### Implementation Steps in GitHub:
**Reference doc**: `dev-docs/sdlc/repo-setup-mgmt.md`

1.  **Rename/Create Branches:** Ensure all these branches exist in your GitHub settings.
2.  **Branch Protection Rules:** This is the most important step. Go to **Settings > Branches** and protect `prod`, `demo`, and `qa`. 
    * Require a **Pull Request** before merging.
    * Require **Status Checks** (like passing tests) to pass before merging.
    * Restrict who can push to these branches (likely just you, but it prevents accidental `git push` from your laptop).

---

## 3. The Development Workflow
To keep your repo clean, follow the **"Promotional Flow."** You don't "push" to QA or Prod; you **merge** into them.

### Step 1: Local Development
Never code directly on `dev`.
```bash
git checkout dev
git pull origin dev
git checkout -b feature/add-login-ui
# ... do work ...
git commit -m "feat: added login screen"
git push origin feature/add-login-ui
```

### Step 2: Integration
Open a **Pull Request (PR)** on GitHub from `feature/add-login-ui` → `dev`. 
Once you (or a teammate) review it and the tests pass, merge it.

### Step 3: Promotion (The Release Train)
When `dev` feels stable and you want to test in AWS QA:
1.  Open a PR from `dev` → `qa`.
2.  Merging this PR triggers your **GitHub Action** to deploy to the AWS QA environment.
3.  If QA looks good, open a PR from `qa` → `demo` (or `prod`).

---

## 4. Managing Environments with GitHub Actions
To make this work seamlessly with AWS, use **GitHub Environments** (**Settings > Environments**). You can create environments named `QA`, `Demo`, and `Production`.

* **Secrets:** Store your `AWS_ACCESS_KEY` and `AWS_SECRET_KEY` inside each specific environment.
* **Deployment Protection:** You can set a "Required Reviewer" for the `Production` environment. Even if you merge code into the `prod` branch, GitHub Actions will wait for you to click "Approve" before it actually touches your AWS servers.

### Example GitHub Action Logic:
Create a `.github/workflows/deploy.yml` file. You can set triggers like this:
```yaml
on:
  push:
    branches:
      - dev
      - qa
      - prod
```
The script will then check `if: github.ref == 'refs/heads/prod'` to decide which AWS credentials and S3 buckets/EC2 instances to target.

---

## 5. Summary Checklist
1.  [ ] **Organize Folders:** Move existing code into a `/backend` folder and start the frontend in `/frontend`.
2.  [ ] **Create Branches:** Initialize `dev`, `qa`, and `demo` from your current `main`.
3.  [ ] **Set Protections:** Lock the `prod` branch so you can't accidentally break it.
4.  [ ] **Configure AWS Secrets:** Add your AWS credentials to GitHub Actions Secrets.
5.  [ ] **Write the Workflow:** Create your first GitHub Action to automate the "Laptop to QA" push.

**Would you like me to help you draft a basic GitHub Actions workflow file to handle the deployment to your AWS QA environment?**