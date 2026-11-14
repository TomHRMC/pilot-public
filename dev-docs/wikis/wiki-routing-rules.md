# Pilot Project: Global Knowledge Base Routing Rules

You are working on the Pilot For Trades application. To ensure architectural consistency, strict adherence to project requirements, and optimal token usage, you MUST consult the local project wikis BEFORE relying on your pre-trained (public LLM) knowledge.

## When to use Local Wikis vs. Public Knowledge
- **USE LOCAL WIKIS FIRST:** For ANY question regarding the Pilot app's existing architecture, database schema, API endpoints, internal UI standards, or DevOps infrastructure.
- **USE PUBLIC LLM:** Only for general programming syntax, debugging third-party library errors not covered in our docs, or standard language documentation (e.g., standard React hooks, Python standard library).

## The Wiki Directory Index
Use your `read_file` tool to read the `index.md` of the relevant wiki below to find your answers:

* **DevOps & Infra:** `dev-docs/wikis/devops/wiki/index.md` (AWS ECS, Terraform, CI/CD, Secrets)
* **Frontend & UI:** `dev-docs/wikis/frontend/wiki/index.md` (Next.js, Expo, Zustand, Shadcn)
* **Backend & API:** `dev-docs/wikis/backend/wiki/index.md` (FastAPI routes, Python ORM, QBO Integrations)
* **Voice AI Logic:** `dev-docs/wikis/voice-ai/wiki/index.md` (Whisper/Ollama pipeline, Audio Streaming)
* **Testing & QA:** `dev-docs/wikis/qa/wiki/index.md` (Pytest harnesses, SLO targets, Data Integrity)
* **Electrical (NEC):** `dev-docs/wikis/nec/wiki/index.md` (Code compliance, Trade slang, Assemblies)

**Workflow Directive:** Do not guess database schemas or API shapes. Always read the appropriate wiki index, navigate to the specific concept page, and base your code strictly on that local documentation.