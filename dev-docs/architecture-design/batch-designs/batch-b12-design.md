# Batch B12 Design Document — Voice Persona

**Batch**: B12  
**Theme**: Voice Persona Tone Renderer + Preview Audio Generation + Per-User Resolution  
**Items**: A67 (single-item batch)  
**Prerequisites**: B2 (voice intent handlers), B9 (three-tier resolver + settings infrastructure)  
**Gates**: None  
**Estimated Effort**: 4–6 days  
**Test Subfolder**: `tests/batch_b12/`  
**Design Date**: 2026-05-02  

---

## A. MIGRATION PLAN

### DB State Verified (via MCP postgres-local query, 2026-05-02)

- `tenant_settings` currently has **38 columns** — confirmed `voice_persona_tone` and `voice_persona_tone_user_override_allowed` do **not** exist.
- `user_setting_override` exists with columns: `tenant_id` (UUID, NOT NULL), `user_id` (UUID, NOT NULL), `setting_key` (TEXT, NOT NULL), `value` (JSONB, NOT NULL), `created_at` (TIMESTAMPTZ, NOT NULL), `updated_at` (TIMESTAMPTZ, NOT NULL), `created_by` (UUID, nullable), `updated_by` (UUID, nullable). **No new columns needed — this table already handles user-level tone overrides.**
- `conversation_session` already has `title` (TEXT, nullable), `title_auto_generated` (BOOLEAN, NOT NULL, default `false`), `archived_at` (TIMESTAMPTZ, nullable). **No schema changes needed.**

### Migration 1 — `phase_fe_1_batch_b12_voice_persona_settings`

**Target table**: `tenant_settings`  
**Action**: Add two columns

| Column | Type | Nullable | Default | Notes |
|:---|:---|:---|:---|:---|
| `voice_persona_tone` | TEXT | YES | NULL | NULL resolves to system default `balanced` at runtime; enum constraint: `conservative \| balanced \| playful` |
| `voice_persona_tone_user_override_allowed` | BOOLEAN | NO | `TRUE` | Tenant meta-toggle; NOT NULL; server default TRUE so existing tenants automatically allow user override |

**Check constraint** (add on `voice_persona_tone` column):
```sql
CONSTRAINT tenant_settings_voice_persona_tone_chk
CHECK (voice_persona_tone IS NULL OR voice_persona_tone IN ('conservative', 'balanced', 'playful'))
```

**No index** — single-row-per-tenant table; indexed on `tenant_id` PK already.

**No new tables** — `user_setting_override` is the existing per-user storage for all user-level setting overrides; this batch writes `voice_persona_tone` rows into that table using the existing schema.

### Non-DB Artifacts Created by A67 (not migrations but must be tracked)

| Artifact | Path | Description |
|:---|:---|:---|
| Prompt template | `backend/prompts/voice/voice_response_conservative.md` | Ollama response prompt — conservative tone |
| Prompt template | `backend/prompts/voice/voice_response_balanced.md` | Ollama response prompt — balanced tone (refactored from current inline prompts) |
| Prompt template | `backend/prompts/voice/voice_response_playful.md` | Ollama response prompt — playful tone |
| Prompt template | `backend/prompts/voice/session_title_conservative.md` | Session title generation prompt — conservative |
| Prompt template | `backend/prompts/voice/session_title_balanced.md` | Session title generation prompt — balanced |
| Prompt template | `backend/prompts/voice/session_title_playful.md` | Session title generation prompt — playful |
| S3 static asset | `s3://pilot-static/voice-preview/conservative.mp3` | Preview audio — one-time generation at deployment |
| S3 static asset | `s3://pilot-static/voice-preview/balanced.mp3` | Preview audio |
| S3 static asset | `s3://pilot-static/voice-preview/playful.mp3` | Preview audio |

---

## B. EXECUTION ORDER

| # | Item | Rationale |
|:---|:---|:---|
| 1 | **A67 — Schema migration** (`phase_fe_1_batch_b12_voice_persona_settings`) | Foundation: all downstream code requires `tenant_settings` to have the new columns before any route reads or writes them. |
| 2 | **A67 — Extend `SETTING_CATALOG` + `SYSTEM_DEFAULTS`** in `core/setting_catalog.py` and `core/system_defaults.py` | Must exist before the renderer and API routes resolve settings, because `get_effective_setting_for_user()` reads `SETTING_CATALOG` to determine `allows_user_override`. |
| 3 | **A67 — Update `setting_allows_user_override_for_tenant()`** in `services/setting_resolver.py` | The meta-toggle (`voice_persona_tone_user_override_allowed`) is a per-setting tenant policy not covered by the base catalog flag alone; the resolver must check this secondary column before returning the user tier. |
| 4 | **A67 — Create `services/voice_persona_renderer.py`** | New central module; must exist before the refactor pass modifies all intent handlers to call it. Also must exist before the `voice_session_service.py` A11 title generation update. |
| 5 | **A67 — Create prompt template files** (`prompts/voice/*.md`) | Loaded at worker startup by the renderer; must exist in the repo before step 4 runs in any environment. In practice these can land in the same commit. |
| 6 | **A67 — Create `services/voice_preview_audio.py`** | Preview audio generation utility. Depends on renderer prompt templates existing. One-time deployment invocation; not a hot path. |
| 7 | **A67 — Create `api/routes/voice_persona.py`** (dedicated route file for 7 endpoints) | Depends on renderer (step 4) and resolver (step 3); must register with the app router before tests. |
| 8 | **A67 — Refactor pass: update `INTENT_HANDLERS` in `services/voice_action_router.py`** | Each handler's return `message` string is now produced via `voice_persona_renderer.render()`; depends on renderer existing. Backwards-compatible because `balanced` is the fallback default. |
| 9 | **A67 — Update A11 session title generation** in `services/voice_session_service.py` | A11 title generation must switch from an inline prompt to the tone-specific session title template via the renderer; depends on step 4 and step 5. |
| 10 | **A67 — Register RBAC permissions** | Add three new permission strings to platform role seed data; confirm `require_permission()` wiring in new route file. |

---

## C. NEW API ENDPOINTS

All endpoints live in the new router file `backend/api/routes/voice_persona.py` and are mounted at prefix `/api/v1/settings`.

---

### C1. `GET /api/v1/settings/voice-persona-tone`

**Auth**: JWT required  
**RBAC**: No explicit permission check — any authenticated user may read their own effective tone  

**Request**: No body. Authenticated user identity from JWT.

**Response `200 OK`**:
```json
{
  "effective_tone": "playful",
  "effective_scope": "user",
  "user_override": "playful",
  "tenant_default": "balanced",
  "system_default": "balanced",
  "user_override_allowed": true,
  "available_tones": ["conservative", "balanced", "playful"],
  "preview_audio_urls": {
    "conservative": "https://cdn.pilotfortrades.com/voice-preview/conservative.mp3",
    "balanced":     "https://cdn.pilotfortrades.com/voice-preview/balanced.mp3",
    "playful":      "https://cdn.pilotfortrades.com/voice-preview/playful.mp3"
  }
}
```

**Logic**: Calls `get_effective_setting_for_user(db, tenant_id, user_id, "voice_persona_tone", "balanced")` from `services/setting_resolver.py`. Additionally queries `tenant_settings.voice_persona_tone_user_override_allowed` to populate `user_override_allowed`. Reads user override directly from `user_setting_override` to populate `user_override` field (may be `null` if no override exists).

---

### C2. `PUT /api/v1/settings/voice-persona-tone`

**Auth**: JWT required  
**RBAC**: `voice_persona_tone.user_override.edit` — all authenticated roles (when tenant policy allows)

**Request body**:
```json
{
  "value": "playful"
}
```

**Response `200 OK`**:
```json
{
  "setting_key": "voice_persona_tone",
  "value": "playful",
  "scope": "user",
  "updated_at": "2026-05-02T18:00:00Z"
}
```

**Error cases**:
- `403 Forbidden` — `tenant_settings.voice_persona_tone_user_override_allowed` is `FALSE` (checked via `setting_allows_user_override_for_tenant()` extended in B12)
- `422 Unprocessable` — `value` not in `["conservative", "balanced", "playful"]`

**Logic**: Upserts a row in `user_setting_override` with `setting_key="voice_persona_tone"`. Calls `_invalidate_user_settings_cache(tenant_id, user_id, role_code)` after write (import from `api/routes/settings.py`).

---

### C3. `DELETE /api/v1/settings/voice-persona-tone`

**Auth**: JWT required  
**RBAC**: `voice_persona_tone.user_override.edit`

**Request**: No body.

**Response `204 No Content`** (idempotent — no error if row doesn't exist)

**Logic**: Deletes `user_setting_override` row matching `(tenant_id, user_id, "voice_persona_tone")`. Calls cache invalidation.

---

### C4. `GET /api/v1/settings/tenant/voice-persona-tone`

**Auth**: JWT required  
**RBAC**: No permission check — any role may read tenant default (read-only for non-owners)

**Response `200 OK`**:
```json
{
  "tenant_default": "balanced",
  "tenant_default_scope": "tenant",
  "system_default": "balanced",
  "user_override_policy": true,
  "available_tones": ["conservative", "balanced", "playful"],
  "preview_audio_urls": {
    "conservative": "https://cdn.pilotfortrades.com/voice-preview/conservative.mp3",
    "balanced":     "https://cdn.pilotfortrades.com/voice-preview/balanced.mp3",
    "playful":      "https://cdn.pilotfortrades.com/voice-preview/playful.mp3"
  }
}
```

---

### C5. `PUT /api/v1/settings/tenant/voice-persona-tone`

**Auth**: JWT required  
**RBAC**: `voice_persona_tone.tenant_default.edit` — owner only

**Request body**:
```json
{
  "value": "conservative"
}
```

**Response `200 OK`**:
```json
{
  "setting_key": "voice_persona_tone",
  "value": "conservative",
  "scope": "tenant",
  "updated_at": "2026-05-02T18:00:00Z"
}
```

**Logic**: Sets `tenant_settings.voice_persona_tone = "conservative"` for the tenant row. Calls `_invalidate_settings_catalog_cache(tenant_id)`.

---

### C6. `DELETE /api/v1/settings/tenant/voice-persona-tone`

**Auth**: JWT required  
**RBAC**: `voice_persona_tone.tenant_default.edit` — owner only

**Request**: No body.

**Response `204 No Content`** — sets `tenant_settings.voice_persona_tone = NULL` (falls back to system default `balanced`)

**Logic**: Sets column to NULL, calls cache invalidation.

---

### C7. `PUT /api/v1/settings/tenant/voice-persona-tone-user-override-allowed`

**Auth**: JWT required  
**RBAC**: `voice_persona_tone.user_override_policy.edit` — owner only

**Request body**:
```json
{
  "value": false
}
```

**Response `200 OK`**:
```json
{
  "setting_key": "voice_persona_tone_user_override_allowed",
  "value": false,
  "scope": "tenant",
  "updated_at": "2026-05-02T18:00:00Z"
}
```

**Side effect**: Write an audit log entry (`audit_event` table) per A67 Decision 9. When set to `FALSE`, user-level overrides in `user_setting_override` are **ignored by the resolver** but **not deleted** — they are preserved so that if the owner re-enables the toggle, each user's previous preference is restored.

---

## D. PATTERN REUSE DECISIONS

### D1. Three-Tier Settings Resolver — §21 of `pilot-python-engineer-methods.md`

**Section cited**: §21 (Three-Tier Settings Resolver Pattern)  
**Source function**: `get_effective_setting_for_user()` in `services/setting_resolver.py`  
**Applied to**: A67 — every voice intent handler response and session title generation

**How B12 uses it**:
```python
from services.setting_resolver import get_effective_setting_for_user

tone, scope = get_effective_setting_for_user(
    db=db,
    tenant_id=current_user.tenant_id,
    user_id=current_user.id,
    setting_key="voice_persona_tone",
    fallback="balanced",
)
# tone = "conservative" | "balanced" | "playful"
# scope = "user" | "tenant" | "system" | "fallback"
```

**B12-specific extension**: The standard resolver already checks `SETTING_CATALOG[key].allows_user_override`. B12 adds a **meta-toggle check** in `setting_allows_user_override_for_tenant()` that also reads `tenant_settings.voice_persona_tone_user_override_allowed`. This is a B12 extension to the B9-established function — the docstring in B9's implementation already notes "per-setting meta-toggles like `voice_persona_tone_user_override_allowed` are handled in B12."

**Updated function signature** (extension, not replacement):
```python
def setting_allows_user_override_for_tenant(
    db: Session,
    tenant_id: UUID,
    setting_key: str,
) -> bool:
```

B12 will extend the body of this function to check the `voice_persona_tone_user_override_allowed` column when `setting_key == "voice_persona_tone"`, or more generically, to check a column named `{setting_key}_user_override_allowed` if it exists on `TenantSettings`.

---

### D2. System Default + Tenant Override Configuration — mvp-arch §16.5

**Section cited**: §16.5 (System Default + Tenant Override Two-Tier Configuration)  
**Source module**: `core/system_defaults.py` + `core/setting_catalog.py`  
**Applied to**: A67 — `voice_persona_tone` tenant setting resolution

B12 adds two entries to `SETTING_CATALOG`:
```python
"voice_persona_tone": {
    "label": "Voice AI persona tone",
    "description": "The personality tone of the AI voice assistant. Conservative = formal/brief; Balanced = friendly/professional; Playful = casual/upbeat.",
    "sub_surface_path": "/settings/voice/persona",
    "data_type": "string",
    "validation_rules": {"allowed_values": ["conservative", "balanced", "playful"]},
    "system_default": "balanced",
    "requires_role": "owner",          # Only owners may write tenant default
    "allows_user_override": True,       # Users may set their own override
    "revertible": True,
},
"voice_persona_tone_user_override_allowed": {
    "label": "Allow per-user voice persona override",
    "description": "When ON, each team member can set their own voice AI tone. When OFF, all users use the team default.",
    "sub_surface_path": "/settings/voice/persona",
    "data_type": "boolean",
    "validation_rules": {},
    "system_default": True,
    "requires_role": "owner",
    "allows_user_override": False,      # Meta-toggle is tenant-only
    "revertible": False,                # No meaningful "revert to system default"
},
```

B12 adds one entry to `SYSTEM_DEFAULTS`:
```python
"voice_persona_tone": "balanced",
```

---

### D3. INTENT_HANDLERS Refactor — mvp-arch §6.2

**Section cited**: §6.2 (Voice Intent Handlers)  
**Source registry**: `INTENT_HANDLERS` dict at line 3411 of `services/voice_action_router.py`  
**Applied to**: A67 — all 18 registered intent handlers

Every handler currently constructs the `message` string directly (e.g., `f"Created Quote #{quote_id_short} for {customer.display_name}. What would you like to add?"`). After the refactor pass, each handler passes a structured payload to `voice_persona_renderer.render(payload, user_id, db)`, which returns the tone-aware string.

The structured payload passed to the renderer:
```python
{
    "intent": "create_quote",
    "outcome": "success",
    "data": {
        "quote_id_short": quote_id_short,
        "customer_name": customer.display_name,
    }
}
```

The renderer selects the appropriate `voice_response_{tone}.md` template and returns the final TTS-ready string. All handlers' existing `message` strings are moved into the `balanced` template as the initial content.

---

### D4. A11 Session Title Generation Tone — mvp-arch §6.4

**Section cited**: §6.4 (Conversation Sessions & Structured Message Payload)  
**Source function**: `get_sessions_with_numbers()` and title generation logic in `services/voice_session_service.py`  
**Applied to**: A67 — Decision 7 (session titles use creator's tone, not viewer's tone)

The A11 session title Celery task currently uses a single Ollama prompt. B12 refactors it to call `voice_persona_renderer.generate_session_title(session_context, creator_user_id, db)`, which selects `session_title_{tone}.md` based on the **session creator's** resolved tone. The title is generated once; subsequent viewers see the creator's rendered title regardless of their own tone.

---

### D5. Backwards Compatibility Guarantee

No behavioral change for existing tenants. The `balanced` fallback is the system default and matches all current inline prompt behavior. All existing INTENT_HANDLERS tests must pass with zero modification after the refactor.

---

## E. SHARED MODULE INTERFACES

### E1. `services/voice_persona_renderer.py` (NEW)

```python
"""
Voice Persona Renderer — tone-aware Ollama response and session title generation.

Established in B12 (A67). Called by every voice intent handler in
services/voice_action_router.py after the refactor pass, and by the A11
session title generation task in services/voice_session_service.py.

Prompt templates are loaded once per worker process from disk.
Effective-tone resolution is cached per (user_id, tenant_id) for the
duration of a single request via a local dict passed through call context.
"""

from pathlib import Path
from typing import Any, Dict
from uuid import UUID

from sqlmodel import Session


# Tone enum values (mirrors SETTING_CATALOG validation_rules)
VALID_TONES = ("conservative", "balanced", "playful")
DEFAULT_TONE = "balanced"

# Static empty-state copy map (not LLM-generated)
EMPTY_STATE_COPY: Dict[str, str] = {
    "conservative": "No voice sessions yet. Tap the mic to begin.",
    "balanced": "Ready when you are. Tap the mic to start a voice session.",
    "playful": "Nothing here yet — let's change that! Tap the mic 🎙️",
}


def render(
    payload: Dict[str, Any],
    user_id: UUID,
    db: Session,
    tenant_id: UUID,
    tone_cache: Dict[str, str] | None = None,
) -> str:
    """
    Render a tone-aware TTS-ready response string for a voice intent outcome.

    Args:
        payload:     Structured dict from an intent handler:
                     {"intent": str, "outcome": str, "data": dict}
        user_id:     The user who issued the voice command (drives tone resolution).
        db:          Active SQLModel session (for settings lookup).
        tenant_id:   The active tenant.
        tone_cache:  Optional dict for per-request tone caching. Pass the same
                     dict across multiple render() calls in one request to avoid
                     repeated DB hits.

    Returns:
        str — The final TTS-ready response message string.
    """
    ...


def generate_session_title(
    session_context: str,
    creator_user_id: UUID,
    db: Session,
    tenant_id: UUID,
) -> str:
    """
    Generate a tone-aware session title using the creator's effective tone.

    Uses session_title_{tone}.md template with Ollama. Called by the A11
    Celery task after the first assistant turn of a new session.

    Args:
        session_context: Brief context string summarizing the session opening.
        creator_user_id: UUID of the user who created the session (tone source).
        db:              Active SQLModel session.
        tenant_id:       The active tenant.

    Returns:
        str — Generated title string (max 60 characters per template instruction).
    """
    ...


def get_empty_state_copy(
    user_id: UUID,
    db: Session,
    tenant_id: UUID,
) -> str:
    """
    Return the tone-appropriate empty-state copy for the Voice AI tab.

    Uses the **viewing user's** effective tone (per A67 Decision 8), distinct
    from session title generation which uses the creator's tone.

    Returns:
        str — Static empty-state string from EMPTY_STATE_COPY map.
    """
    ...


def _resolve_tone(
    user_id: UUID,
    db: Session,
    tenant_id: UUID,
    cache: Dict[str, str] | None,
) -> str:
    """
    Internal: resolve the effective tone for a user using the three-tier chain.

    Calls get_effective_setting_for_user() from services/setting_resolver.py.
    Returns one of ("conservative", "balanced", "playful").
    """
    ...


def _load_template(tone: str, template_type: str) -> str:
    """
    Internal: load a prompt template from disk. Cached per worker process.

    Args:
        tone:          One of VALID_TONES.
        template_type: "voice_response" | "session_title"

    Returns:
        str — Raw template content.

    Raises:
        FileNotFoundError if the template file is missing.
    """
    ...
```

**File path**: `backend/services/voice_persona_renderer.py`

---

### E2. `services/voice_preview_audio.py` (NEW)

```python
"""
Voice Preview Audio Generator — one-time S3 upload of persona preview MP3s.

Called via a CLI/deployment script: python -m services.voice_preview_audio
Not invoked at runtime; preview audio is static CDN-served content.

S3 output paths:
  s3://pilot-static/voice-preview/conservative.mp3
  s3://pilot-static/voice-preview/balanced.mp3
  s3://pilot-static/voice-preview/playful.mp3
"""


def generate_and_upload_preview_audio(
    tones: list[str] = ("conservative", "balanced", "playful"),
    s3_bucket: str = "pilot-static",
    s3_prefix: str = "voice-preview",
    overwrite: bool = False,
) -> dict[str, str]:
    """
    Generate preview audio files for each tone and upload to S3.

    Args:
        tones:     Tones to generate previews for.
        s3_bucket: Target S3 bucket name.
        s3_prefix: S3 key prefix (no trailing slash).
        overwrite: If False, skip tones that already have an S3 object.

    Returns:
        dict mapping tone → S3 URI of uploaded object.
    """
    ...
```

**File path**: `backend/services/voice_preview_audio.py`

---

## F. OPEN QUESTIONS RESOLVED

### F1. Does `voice_persona_tone` already exist on `tenant_settings`?

**Question**: The A13 entry "reserved" this field. Was it written as a DB column or just a design placeholder?  
**Resolution**: **Not yet in DB.** MCP query against the live local DB confirmed no `voice_persona_tone` or `voice_persona_tone_user_override_allowed` column exists on `tenant_settings`. Migration is required.

---

### F2. How should the meta-toggle interact with existing user overrides?

**Question**: When owner sets `voice_persona_tone_user_override_allowed = FALSE`, should existing `user_setting_override` rows for `voice_persona_tone` be deleted?  
**Resolution**: **Preserve, do not delete.** The resolver silently ignores user-tier values when the meta-toggle is `FALSE`. If the owner re-enables the toggle, each user's previous preference is immediately restored without requiring re-configuration. No Celery job needed. This matches the pattern used by `background_sync_enabled` in the catalog (user can override; the catalog flag gates it).

---

### F3. Where do voice persona API endpoints live — in `settings.py` or a new file?

**Question**: The existing `api/routes/settings.py` has 1,146 lines and a structured generic pattern. Do these tone endpoints belong there or in a dedicated file?  
**Resolution**: **New file `api/routes/voice_persona.py`**. The generic `PUT /settings/{key}` endpoint in `settings.py` could theoretically handle tenant writes, but the voice persona endpoints have custom response shapes (preview audio URLs, user_override_allowed status), custom 403 logic for the meta-toggle, and semantically belong to the Voice AI surface, not the generic settings surface. A dedicated route file avoids overloading `settings.py` and makes the B12 diff clean and reviewable.

---

### F4. Which file handles the A11 title generation Celery task?

**Question**: The B2 implementation plan mentioned A11 title generation. Is it in `voice_session_service.py` or a Celery task file?  
**Resolution**: The `voice_session_service.py` docstring already reads "Extended by B12 (A67) for persona tone rendering," confirming B9 and B2 already wired the extension point. The Celery task itself calls the service; B12 updates `generate_session_title()` in the service, and the task caller needs no change.

---

### F5. Should `voice_response_balanced.md` be genuinely new content or migrated from existing inline strings?

**Question**: Existing handler `message` strings are inline in `voice_action_router.py`. Should `voice_response_balanced.md` be a mechanical migration of those strings into a template, or newly authored?  
**Resolution**: **Mechanical migration first, review after.** The `balanced` template starts as the literal existing inline strings converted to a Jinja2-style template format (using `{{ variable }}` placeholders matching payload `data` keys). The `conservative` and `playful` variants are written as new content diverging from `balanced`. This keeps the refactor pass risk minimal (existing tests pass unchanged) while producing the full three-template set.

---

### F6. Preview audio: native TTS pipeline or third-party at MVP?

**Question**: The arch doc says "using the configured TTS pipeline (or a dedicated TTS service if voice synthesis isn't ready)." What's the MVP decision?  
**Resolution**: **Third-party TTS for preview audio only.** Preview audio is generated once at deployment — not at runtime. Using the Expo/browser `SpeechSynthesis` client-side API for live responses is confirmed MVP architecture (§6.1). For the preview MP3 generation script, the implementation can use any available TTS (OpenAI TTS, Google TTS, or even `gTTS` as a free fallback). The actual provider is implementation-time decision for the Python engineer — the generator script accepts the provider as a configurable parameter. **No production dependency on external TTS is introduced** since preview audio is static, one-time-generated.

---

### F7. Do the three new RBAC permission strings need to be seeded?

**Question**: `voice_persona_tone.tenant_default.edit`, `voice_persona_tone.user_override.edit`, `voice_persona_tone.user_override_policy.edit` are cited in the ledger. Are these in `permissions.py`?  
**Resolution**: MCP search confirmed `permissions.py` has **zero** `voice_persona` entries. These strings must be added to the platform role seed data. `voice_persona_tone.user_override.edit` goes to all roles (owner, accountant, tech). `voice_persona_tone.tenant_default.edit` and `voice_persona_tone.user_override_policy.edit` go to owner only. The Python engineer must add these strings during B12 implementation.

---

## G. EXTERNAL DEPENDENCY STATUS

### G1. Ollama (local GPU) — Prompt rendering

**Items requiring it**: A67 — all three `voice_response_{tone}.md` templates and three `session_title_{tone}.md` templates are Ollama prompts  
**Status**: Already in use (B2 established). No new external dependency.  
**Mock strategy**: Existing Ollama mock pattern from B2 tests applies. `voice_persona_renderer.render()` is unit-tested with a mock Ollama response; integration tests run against the real local Ollama container.  
**Tom action required**: None. GPU instance already running locally.

---

### G2. AWS S3 — Preview audio storage

**Items requiring it**: A67 — `s3://pilot-static/voice-preview/{tone}.mp3`  
**Status**: S3 is already used for photos and voice audio (established in earlier batches). The `pilot-static` bucket is a new static-assets bucket (separate from the per-tenant data bucket).  
**Mock strategy**: In CI/CD, `voice_preview_audio.py` is not invoked. Preview audio URLs in API responses are hardcoded CDN URLs; the endpoint does not check that the S3 object exists at request time.  
**Tom action required**: Create `pilot-static` S3 bucket with public-read policy for `voice-preview/*` prefix; configure CloudFront distribution to serve `cdn.pilotfortrades.com/voice-preview/*`. **One-time setup before production delivery of A67.** Lead time: ~30 minutes of AWS console work.

---

### G3. TTS provider — One-time preview audio generation

**Items requiring it**: A67 — `services/voice_preview_audio.py` script  
**Status**: Not yet integrated. Used only at deployment time (not a runtime dependency).  
**Mock strategy**: The CI pipeline does not run preview audio generation. The deployment script is a manual one-time invocation. For local development, placeholder MP3 files (silent 5-second clips) can be placed at `s3://pilot-static/voice-preview/` to satisfy URL resolution tests.  
**Tom action required**: Choose TTS provider for preview generation (options: OpenAI TTS API at ~$0.015/1K chars — preview scripts total < $0.05; Google TTS free tier; or `gTTS` free). Decision is implementation-time; no signup required before B12 coding starts. **Lead time if OpenAI TTS chosen**: Immediate (API key already assumed available from prior work).

---

### G4. No other external dependencies

B12 introduces no Stripe, Telnyx, 10DLC, SendGrid, Twilio, or Cognito dependencies. It is entirely a backend rendering logic + settings infrastructure batch.

---

*Design document produced after completing all six required reads: §6.B12 impl plan, A67 ledger entry, mvp-arch.md §6 + §16.5, pilot-python-engineer-methods.md §21, live MCP schema queries on `tenant_settings`/`user_setting_override`/`conversation_session`, and source reads of `voice_action_router.py`, `setting_resolver.py`, `settings.py`, `setting_catalog.py`, `system_defaults.py`, `voice_session_service.py`, and `db_models_map.md`.*
