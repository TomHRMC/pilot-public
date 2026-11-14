# How to Start a New Pilot Architect Chat Session

> **Snapshot note:** references to `pilot-launch-plan.md`, the batch registry and launch-gate docs point to private planning files that were curated out of this public snapshot. [`dev-docs/analysis/Pilot-Delivery-and-Governance.md`](../analysis/Pilot-Delivery-and-Governance.md) summarizes what they held.

This file gives you the exact prompt to paste at the start of every new `pilot-architect` mode chat, plus context on how to extend it for specific session types.

---

## Core Startup Prompt (use every time)

Paste this at the very beginning of every new Architect chat before giving any task:

```
Before doing any work, follow the Session Startup Checklist in §0 of your methods doc:

1. Read dev-docs/architecture-design/pilot-architect-methods.md in full — this is your operating manual for this project.
2. Read dev-docs/analysis/pilot-launch-plan.md — this is the primary execution tracker; it tells you what is done, what is open, and what the current P0/P1/P2 priorities are.
3. Read dev-docs/product-requirements/pilot-product-roadmap.md — Phase 1.0/1.5/2.0 product authority.
4. Read .roo/rules-pilot-architect/infrastructure-constraints.md — cost guardrails ($888/month target).

After completing those reads, confirm what you've read and summarize the current project state in 3-4 sentences. Then I'll tell you what we're working on today.
```

**Why the confirmation step matters**: If the agent just says "done" without summarizing, it may have skimmed. Asking for a 3–4 sentence summary forces it to actually process the current state of `pilot-launch-plan.md` and know where things stand before you give it a task.

---

## Session-Specific Extensions

Add these lines to the core prompt depending on what you're planning to work on:

### If writing Python Engineer prompts

```
Also: before writing any Python Engineer prompts today, read backend/python-engr-std-prompt-inclusions.md in full. After reading it, confirm you have read it and state the minimum required sections before writing anything.
```

### If writing React Engineer prompts

```
Also: before writing any React Engineer prompts today, read frontend/react-engr-std-prompt-inclusions.md in full. After reading it, confirm you have read it and state the minimum required sections before writing anything.
```

### If doing any database design work

```
Also: before any database schema work today, read dev-docs/db-design/postgres-mcp-guide.md, then run the following MCP query to confirm current DB state:
SELECT version_num FROM public.alembic_version;
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;
```

### If designing a new batch (any type)

```
Also: before designing any batch today, run MCP postgres-local queries to verify the current state of any tables we'll be modifying. Never guess column names — verify them before writing the design doc.
```

### If working on the marketing website (apps/marketing)

```
Also: before doing any marketing site work today, read frontend/apps/marketing/README.md for the current state of the site, its testing setup, and known constraints.
```

### If working on a pricing, plan, or billing change

```
Also: check dev-docs/analysis/pilot-launch-plan.md §P2 for the current pricing ($49/month flat, unlimited users) before designing anything related to subscriptions or billing.
```

---

## Full Combined Example Prompt

For a session where you're planning to design a new backend + web frontend batch and write both prompts:

```
Before doing any work, follow the Session Startup Checklist in §0 of your methods doc:

1. Read dev-docs/architecture-design/pilot-architect-methods.md in full.
2. Read dev-docs/analysis/pilot-launch-plan.md.
3. Read dev-docs/product-requirements/pilot-product-roadmap.md.
4. Read .roo/rules-pilot-architect/infrastructure-constraints.md.
5. Read backend/python-engr-std-prompt-inclusions.md in full (we will be writing Python prompts today).
6. Read frontend/react-engr-std-prompt-inclusions.md in full (we will be writing React prompts today).

After completing those reads, confirm what you've read and summarize the current project state in 3-4 sentences. Then I'll describe the new batch we need to design.
```

---

## What the Architect Reads and Why

| Doc | Why It Must Be Read |
|---|---|
| `pilot-architect-methods.md` | Operating manual: batch design workflow, project structure, prompt compliance rules, DB tooling, anti-patterns |
| `pilot-launch-plan.md` | Current state: what's done (✅), what's P0/P1/P2 (☐), what batches are in progress |
| `pilot-product-roadmap.md` | Product authority: which features are MVP, post-launch (1.5), or expansion (2.0) — prevents designing the wrong phase |
| `infrastructure-constraints.md` | Cost guardrails: $888/month target, Fargate-first, single GPU, no EKS — prevents expensive architecture suggestions |
| `python-engr-std-prompt-inclusions.md` | Required prompt sections for Python Engineer — prompts written without this always miss sections |
| `react-engr-std-prompt-inclusions.md` | Required prompt sections for React Engineer — same rationale |
| `postgres-mcp-guide.md` | Correct MCP query patterns — prevents guessing column names that break migrations |

---

## Four Sub-Projects the Architect Must Know

Every Architect session should understand that Pilot for Trades has four distinct codebases that work together:

| Sub-Project | Folder | What It Does |
|---|---|---|
| **Backend API** | `backend/` | Python / FastAPI — database, business logic, email, Celery tasks |
| **Web App** | `frontend/apps/web/` | Next.js — owner/office dashboard, authenticated, SSR on App Runner |
| **Mobile App** | `frontend/apps/mobile/` | React Native / Expo — field tech app, offline-first |
| **Marketing Site** | `frontend/apps/marketing/` | Next.js static — public site, blog, waitlist, contact, careers |

Each has its own batch naming sequence (B*, FE-B*, MOB-B*, MKT-B*), design doc location, and prompt file location. See `pilot-architect-methods.md` §8 for the full map.

---

## Quick Cheat Sheet — Batch File Locations

| What | Where |
|---|---|
| Backend design docs | `dev-docs/architecture-design/batch-designs/batch-b{N}-design.md` |
| Web FE design docs | `dev-docs/architecture-design/batch-designs/batch-fe-b{N}-design.md` |
| Mobile design docs | `dev-docs/architecture-design/batch-designs/batch-mob-b{N}-design.md` |
| Marketing design docs | `dev-docs/marketing-analysis/design-specs/mkt-b{N}-design-spec.md` |
| All implementation prompts | `dev-docs/implementation-prompts/fe-be-mob-batch-prompts/batch-[type]-b{N}-[engr]-prompt.md` |

---

*Keep this file in the project root. Update it if the startup protocol changes.*
