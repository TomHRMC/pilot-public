# LLM Wiki Implementation Plan for SaaS Development

This document outlines the formal methodology for implementing the **LLM Wiki Pattern** (pioneered by Andrej Karpathy and the AI developer community) tailored to your SaaS app's final frontend development, AWS deployment, and beta testing workstreams. 

The goal is to transition your local Llama agent from reading static, heavy raw files to querying pre-compiled, interconnected, and token-efficient markdown wikis.

---

## 1. Architecture Overview
The LLM Wiki pattern relies on a 3-layer directory structure:
1. **Layer 1: Raw Sources (`/raw`)** - Your immutable source of truth. The LLM reads these but never edits them.
2. **Layer 2: The Wiki (`/wiki`)** - LLM-generated markdown files (summaries, entity pages, concept cross-references).
3. **Layer 3: The Schema (`schema.md`)** - The constitution that tells the LLM how to behave, parse, and structure the wiki.

---

## 2. The Wiki Sequence & Content Strategy
Based on your workstreams (AWS Setup -> Pre-launch Hygiene -> Beta Testing -> Soft Launch) and the specialized agents in your `.roomodes` configuration, here is the rollout plan and the exact files needed in each wiki's `/raw` folder.

### 2.1 Development Wikis (Internal / Roo Code Agents)
These wikis act as the "Knowledge API" for your local development agents to prevent hallucination and ensure strict adherence to your architecture and constraints.

**Phase 1: DevOps & Infra Wiki (For Workstream 2)**
**Goal:** Assist the `pilot-devops-engineer` and `pilot-architect` with AWS QA/PROD setup (ECS Fargate, CI/CD, Terraform).
**`/raw` folder contents:**
* `db_schema-v1.0.md` or `.sql` dump (sanitized)
* `backend_openapi-v1.0.json`
* `architecture_diagram_notes-v1.0.md` (Ports, VPC needs, blue-green deployment constraints)
* `env_vars_template-v1.0.env` (No secrets, just keys)
* `infrastructure-constraints-v1.0.md` (Cost-Optimized MVP targets)

**Phase 2: API & Backend Wiki (For Workstreams 2 & 4)**
**Goal:** Assist the `pilot-python-engineer` and `pilot-integrations-lead` with backend logic, database schemas, and external data syncs.
**`/raw` folder contents:**
* `backend_openapi-v1.0.json` (Re-used here)
* `python_orm_schemas-v1.0.md` (Pydantic/SQLAlchemy models)
* `sync-idempotency-v1.0.md` (QuickBooks Online conflict resolution logic)
* `error_handling_specs-v1.0.md`

**Phase 3: Frontend State & UI Wiki (For Workstream 4)**
**Goal:** Assist the `pilot-react-engineer` and `pilot-voice-ui-designer` with component mapping, offline capabilities, and client-side architecture.
**`/raw` folder contents:**
* `product_requirements_document-v1.0.md` (PRD)
* `frontend_designs-v1.0.md` (Glove-friendly UI rules, component hierarchy)
* `state_management-v1.0.md` (Zustand flows, React Query caching)
* `watermelon_db_sync-v1.0.md` (Offline-first data handling)

**Phase 4: Voice AI & Pipeline Wiki (For Workstreams 2 & 4)**
**Goal:** Assist the `pilot-voice-ai-specialist` with the multi-turn conversational AI pipeline.
**`/raw` folder contents:**
* `latency-budget-v1.0.md` (<2s end-to-end targets)
* `entity-resolution-v1.0.md` (Pronoun/context management rules)
* `audio_streaming_logic-v1.0.md` (WebSockets, Web Audio API, expo-av specs)
* `voice-feedback-patterns-v1.0.md` (UI listening/processing states)

**Phase 5: Testing & QA Wiki (For Workstreams 4 & 5)**
**Goal:** Assist the `pilot-qa-python-engineer` in validating system reliability and voice AI accuracy.
**`/raw` folder contents:**
* `qa-python-engineer-methods-v1.0.md` (Pytest design patterns)
* `slv-verification-tests-v1.0.md` (API and Voice latency benchmarking)
* `data-integrity-checks-v1.0.md` (Anti-duplication checks)

**Phase 6: Business Logic & Launch Wiki (For Workstream 5)**
**Goal:** Assist the `pilot-orchestrator` and `pilot-marketing-ui-designer` in managing the marketing site, compliance, and soft launch signals.
**`/raw` folder contents:**
* `market_analysis-v1.0.md`
* `marketing_copy_drafts-v1.0.md`
* `10DLC_registration_specs-v1.0.md`
* `stripe_product_catalog-v1.0.json`
* `launch_readiness_checklist-v1.0.md`

---

### 2.2 Production Wikis (End-User / Application AI)
These wikis are heavily optimized for accuracy and strict compliance. They feed the local Llama instance answering user queries in production to ensure trade-specific questions are answered safely and correctly.

**App Help & Features Wiki**
**Goal:** Generate the help corpus, provide tooltips, and answer user questions like "How do I create an invoice?"
**`/raw` folder contents:**
* `beta_testing_notes-v1.0.md` (Manual testing feedback)
* `customer_support_handoff-v1.0.md`
* `feature_explanations-v1.0.md` (Simplified PRD extracts)

**Electrical Standards (NEC) Wiki**
**Goal:** Ensure code-compliant logic for wire sizing, conduit fill, and voltage drops.
**`/raw` folder contents:**
* `nec-compliance-rules-v1.0.md` (NEC 2023 summaries and tables)
* `trade-shorthand-lexicon-v1.0.md` (Mapping slang like "Romex" to technical specs)
* `electrical_assemblies-v1.0.md`

**Plumbing Standards (IPC/UPC) Wiki**
**Goal:** Assist users with plumbing codes, pipe sizing, and venting requirements.
**`/raw` folder contents:**
* `ipc_upc_summaries-v1.0.md` (Pipe sizing charts and venting rules)
* `fixture_regulations-v1.0.md`
* `plumbing_trade_lexicon-v1.0.md`

**HVAC Standards (IMC/EPA) Wiki**
**Goal:** Provide quick lookups for refrigerant handling, ventilation rates, and duct sizing.
**`/raw` folder contents:**
* `imc_compliance_rules-v1.0.md` (Ventilation and duct sizing)
* `epa_608_guidelines-v1.0.md` (Refrigerant handling protocols)
* `hvac_trade_lexicon-v1.0.md`

**Estimating & Materials Wiki**
**Goal:** Help users generate rapid estimates based on standard task durations and material dictionaries.
**`/raw` folder contents:**
* `standard_job_durations-v1.0.md` (e.g., time to replace a 200A panel)
* `common_parts_dictionary-v1.0.md`
* `material_cost_structures-v1.0.md`

---

## 3. Directory Structure
For each phase, you will set up a dedicated directory. For example, for the DevOps Wiki:
```text
devops-wiki/
├── schema.md          # The LLM prompt/rules file
├── raw/               # Drop your OpenAPI, DB schemas here
│   ├── backend_openapi.json
│   └── ...
└── wiki/              # The LLM generates these
    ├── index.md       # Master catalog of all pages
    ├── log.md         # Append-only log of operations
    ├── concepts/      # e.g., "AWS_VPC_Setup", "Database_Connections"
    └── entities/      # e.g., "EC2_Instance_QA", "PostgreSQL_DB"

```

---

## 4. The `schema.md` File (Template)

*Save this as `schema.md` at the root of your wiki directory. It is heavily inspired by Karpathy's original idea and open-source community templates.*

```markdown
# LLM Wiki Schema

You are an expert AI librarian and systems architect. Your job is to maintain a persistent, interconnected knowledge base (a "wiki") based on raw source files.

## Directory Structure
- `raw/`: Immutable source documents. READ ONLY. Never modify these. Filenames include version numbers (e.g., `user_flows-v1.0.md`).
- `wiki/`: Your maintained knowledge base. You have full read/write access.
- `wiki/index.md`: The master catalog of all wiki pages.
- `wiki/log.md`: Append-only chronological record of your operations.
- `wiki/file-version.md`: The ledger tracking the latest ingested versions of raw files.

## Core Operations

### 1. INGEST (The Smart Sync)
When commanded to INGEST, you must follow this exact logic:
1. **Check for State:** Look for `wiki/file-version.md`.
2. **If `wiki/file-version.md` DOES NOT exist (First Run):**
   - Delete all existing contents of the `/wiki` directory (if any).
   - Read all files in `/raw/`.
   - Build out the wiki (summaries, concepts, entities).
   - Create `wiki/index.md` and `wiki/log.md`.
   - Create `wiki/file-version.md` and list every processed filename.
3. **If `wiki/file-version.md` DOES exist (Incremental Run):**
   - Compare the filenames in `/raw/` against the ledger in `wiki/file-version.md`.
   - Identify the "diff" (new files, or files with updated version suffixes like `-v1.1`).
   - Read ONLY the changed files.
   - Update the existing wiki pages, concepts, and `index.md` to reflect the new information.
   - Overwrite `wiki/file-version.md` with the updated list of filenames.
   - Append a summary of updates to `wiki/log.md`.

### 2. QUERY (When asked a question)
- DO NOT read the `raw/` folder unless explicitly forced. 
- Read `wiki/index.md` to locate relevant pages.
- Read those specific pages and synthesize an answer.

### 3. LINT (Health Check)
- Scan the entire `wiki/` directory.
- Identify and report: 
  - Orphan pages (no inbound links).
  - Unresolved contradictions (e.g., data from an older file version conflicting with a newer one).
  - Missing frontmatter tags.

## Formatting Conventions
- Use Obsidian-style wikilinks: `[[page-name]]`.
- Every page in `wiki/` MUST have YAML frontmatter with `title`, `tags`, `last_updated`, and `source_ids` (including the specific version suffix).

```

---

## 5. Workflow and Prompts

When you are ready to process a wiki, you will run your local Llama agent from the root of that specific wiki's directory.

**Prompt 1: Initialize & Ingest**

> "Execute the INGEST operation as defined in schema.md. Check the /raw folder for versioned files, compare them against your state, and either build the wiki from scratch, including the `index.md`, `log.md`, and the associated concept/entity pages, or process the incremental updates. Log your actions. Let me know when you are done."

**Prompt 2: Querying (During Workstreams)**

> "Based ONLY on the `wiki/index.md` and related wiki pages, how should I configure the CORS settings in my AWS API Gateway to properly connect with the frontend state management? Cite the wiki pages you used."

**Prompt 3: Linting (Maintenance)**

> "Execute the LINT operation as defined in `schema.md`. Scan the `/wiki` folder and give me a report on orphan pages, missing cross-references, or contradictions."

---

## 6. Linting Frequency

* **During active development/testing (Workstreams 2 & 4):** Lint **twice a week**. You will be modifying code heavily and taking notes. The wiki can get out of sync quickly.
* **During stable phases (Workstreams 3 & 5):** Lint **once every two weeks**, or immediately after a major batch of new documents is dropped into the `/raw` folder.

---

## 7. References and Inspiration

This architecture is directly adapted from open-source patterns developed by AI researchers:

* **Andrej Karpathy's LLM Wiki Gist:** The foundational idea of treating LLMs as librarians that compile raw sources into interconnected markdown.
* **`nvk/llm-wiki` & `SamurAIGPT/llm-wiki-agent` (GitHub):** Open-source implementations that utilize the `schema.md` pattern to manage AI file ingestion, indexing, and linting logic.
* **LLM Wiki v2 (agentmemory):** Extensions on the pattern that introduce typed relationships and contradiction flagging, incorporated into your `schema.md`.
