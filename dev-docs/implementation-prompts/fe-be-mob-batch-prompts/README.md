# FE / BE / Mobile Batch Implementation Prompts

**Purpose**: Home of all engineer implementation prompts. A prompt is the batch's execution contract **and** its permanent record — when the engineer finishes, they append the full completion summary to the prompt's own ending `## Appendix — Completion Summary` (ADR-0017).

**Status model (ADR-0017)**: batch status is tracked **only** in `pilot-launch-plan.md` — §2.0 (open) and Appendix A (complete, one line + links). This README intentionally carries **no per-batch status list**; the folder listing is the file index. Do not re-add status annotations here.

---

## Naming Conventions

### Design Docs

All batch design docs live in `dev-docs/architecture-design/batch-designs/`:

| Batch type | Design doc name |
|---|---|
| Backend-only | `batch-{id}-design.md` |
| Frontend-only (web) | `batch-fe-{id}-design.md` (legacy; newer batches use `batch-{id}-design.md`) |
| Mobile-only | `batch-mob-{id}-design.md` (legacy) |
| Mixed (BE + FE in one batch) | `batch-{id}-design.md` — contains both a Backend section and a Frontend section |
| UI design specs (designer-mode output) | `batch-{id}-ui-design-spec.md` (web) · `batch-{id}-mobile-ui-design-spec.md` · `mkt-{id}-design-spec.md` (marketing, in `dev-docs/marketing-analysis/design-specs/` (private, not in this snapshot)) |

### Prompt Files

All prompt files live in this folder. **Mixed batches get one prompt per engineer:**

| Prompt type | File naming pattern |
|---|---|
| Python Engineer | `batch-{id}-python-engr-prompt.md` |
| React Engineer (web) | `batch-{id}-react-engr-prompt.md` |
| React Native Engineer (mobile) | `batch-{id}-react-native-engr-prompt.md` |
| Web UI Designer (spec prerequisite) | `batch-{id}-web-ui-designer-prompt.md` |
| Voice UI Designer (mobile spec prerequisite) | `batch-{id}-voice-ui-designer-prompt.md` |
| Marketing UI Designer | `batch-{id}-mkt-ui-designer-prompt.md` |

DevOps prompts live in `dev-docs/devops/prompts/` as `batch-{id}-devops-prompt.md`.

**Rule**: for mixed batches the Python Engineer prompt always runs first. The React/RN prompt references the new/changed endpoints from the BE half and depends on `pnpm sync-api-types` being run after the BE half closes.

---

## Lifecycle Per Batch (v6.0 model — ADR-0017)

1. **Architect — open**: add a §2.0 row + a card in `pilot-launch-plan.md`.
2. **Architect — design**: write the design doc (A–G sections per `pilot-architect-methods.md`; H–I for frontend batches). New/changed UI surface? A designer-mode spec comes **first** and must be Tom-approved before any engineer prompt (Rule 1.5).
3. **Architect — prompt**: write the prompt file(s) here. Required sections come from `backend/python-engr-std-prompt-inclusions.md` / `frontend/react-engr-std-prompt-inclusions.md` — read them every time. **Every prompt ends with an empty `## Appendix — Completion Summary` template.**
4. **Engineer — execute**: run the prompt. On completion: append the completion summary to the prompt's ending appendix; update any source-spec task headers (e.g. `README-seed-data.md` §10) to ✅. Backend change? Run `python export_openapi_json.py` and `cd frontend && pnpm sync-api-types` — that is the BE→FE handoff signal.
5. **Architect — close**: read the prompt-doc summary, then update the launch plan **status only**: §2.0 ✅ + a one-line Appendix A row (outcome + links) + §5 if a gate item. **Never paste summaries into the launch plan.**
6. **Archive**: when Appendix A exceeds ~80 rows, run the light archive cycle in launch plan Appendix B.

---

## Standing Rules (summary — the inclusion files govern the full set)

1. **All POST/PATCH mutations** use `apiClient` from `@pilot/shared-api` — never raw `fetch()` (documented PLAT-DEBT exceptions aside).
2. **All new API hooks** verify exact endpoint path + params against `backend/openapi.json` before coding.
3. **All SSE connections** use centralized `useSseChannel` with the `getToken` prop.
4. **All customer-facing create/send actions** follow the `always-preview-before-send` pattern (PRD §4.1).
5. **All create forms** use `Idempotency-Key: UUID` headers via the `apiClient` interceptor.
6. **After any backend change**: `cd frontend && pnpm sync-api-types` regenerates `packages/shared-types/src/api-schema.d.ts`.
