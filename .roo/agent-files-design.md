# Pilot for Trades: Roo Agent Files & Context Design

> **Design-time agent rule** — written to steer the AI agents during the build and published as last used. Where it differs from the as-built system, [`PROVENANCE.md`](../PROVENANCE.md) and [`dev-docs/diligence/`](../dev-docs/diligence/README.md) are correct.

Below is the verified mapping of specialized Roo modes to their automatically loaded context rule files, matching the `.roo/` directory structure.

### 1. 🏗️ Pilot Architect (`pilot-architect`)
**Context Folder:** `.roo/rules-pilot-architect/`
* `infrastructure-constraints.md`: Defines the hard cap of $1,000/month and the "Fargate-first" compute policy.
* `scaling-logic.md`: Rules for sub-linear scaling (e.g., when to trigger a second GPU instance at 1,000 customers).

### 2. 🪃 Pilot Orchestrator (`pilot-orchestrator`)
**Context Folder:** `.roo/rules-pilot-orchestrator/`
* `mission-control.md`: Guidepost file that lists Key Metrics (e.g., ~$8.88/customer cost, 99.9% availability) ensuring the Orchestrator rejects any plan that is too expensive or complex for an MVP.

### 3. 🚀 Pilot Python Engineer (`pilot-python-engineer`)
**Context Folder:** `.roo/rules-pilot-python-engineer/`
* `80-20-prioritization.md`: A rule to flag any feature that isn't required for "Mike the Solo Contractor" to finish a quote, prioritizing rapid velocity.

### 4. ♾️ DevOps Engineer (`devops-engineer`)
**Context Folder:** `.roo/rules-devops-engineer/`
* `blue-green-constraints.md`: Steps for the 10% → 50% → 100% traffic shift logic in ECS.
* `secret-management-policy.md`: Prohibits hardcoded strings; enforces AWS Secrets Manager for all environment variables.

### 5. ⚡ Electrical Domain Expert (`electrical-domain-expert`)
**Context Folder:** `.roo/rules-electrical-domain-expert/`
* `nec-compliance-rules.md`: Constraints requiring all material suggestions to meet NEC 2023/2026 standards.
* `trade-shorthand-lexicon.md`: A dictionary of electrical slang (e.g., "romex," "pigtail," "home run") to improve Ollama's parsing.

### 6. 🔄 Integrations Lead (`integrations-lead`)
**Context Folder:** `.roo/rules-integrations-lead/`
* `conflict-resolution-flow.md`: Logic for the "Master" record selection (User choice vs. QB Master).
* `sync-idempotency.md`: Implementation rules requiring `X-Idempotency-Key` for all financial POSTs.

### 7. 🧪 QA Python Engineer (`qa-python-engineer`)
**Context Folder:** `.roo/rules-qa-python-engineer/`
* `data-integrity-checks.md`: Integration test requirements for "Zero duplicate entries" in QuickBooks.
* `slv-verification-tests.md`: Rules for automated tests that fail if API latency exceeds 500ms.

### 8. 🎙️ Voice AI Specialist (`voice-ai-specialist`)
**Context Folder:** `.roo/rules-voice-ai-specialist/`
* `entity-resolution.md`: Rules for multi-turn context (e.g., always check `conversation_sessions` table before creating a new record).
* `latency-budget.md`: Strict rules for the 2000ms p95 budget, breaking down allowed time for Whisper vs. Ollama.

### 9. 🎨 Voice UI Designer (`voice-ui-designer`)
**Context Folder:** `.roo/rules-voice-ui-designer/`
* `glove-friendly-ui.md`: Constraints on minimum touch targets (44x44px) and high-contrast color palettes (WCAG AAA).
* `voice-feedback-patterns.md`: Rules for visual "listening" states to prevent user frustration in 70dB noise.