"""
Voice Persona Renderer — tone-aware Ollama response and session title generation.

Established in B12 (A67). Called by every voice intent handler in
services/voice_action_router.py after the refactor pass, and by the A11
session title generation task in services/voice_session_service.py.

Prompt templates are loaded once per worker process from disk (module-level cache).
Effective-tone resolution is performed per-request via get_effective_setting_for_user().
An optional tone_cache dict can be passed across multiple render() calls in one
request to avoid repeated DB hits.

Resolution chain (§21 three-tier):
    User override (if tenant allows) → Tenant override → System default ('balanced')
"""

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlmodel import Session

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_TONES = ("conservative", "balanced", "playful")
DEFAULT_TONE = "balanced"

# CDN base for preview audio assets (static S3-backed content)
PREVIEW_AUDIO_BASE_URL = "https://cdn.pilotfortrades.com/voice-preview"

# Static empty-state copy map (not LLM-generated — instantaneous, no network call)
EMPTY_STATE_COPY: dict[str, str] = {
    "conservative": "No voice sessions yet. Tap the mic to begin.",
    "balanced": "Ready when you are. Tap the mic to start a voice session.",
    "playful": "Nothing here yet — let's change that! Tap the mic 🎙️",
}

# Template type identifiers
_TEMPLATE_VOICE_RESPONSE = "voice_response"
_TEMPLATE_SESSION_TITLE = "session_title"

# Path to prompt templates directory (relative to this file's location)
_PROMPTS_DIR = Path(__file__).parent.parent / "prompts" / "voice"


# ---------------------------------------------------------------------------
# Template loading (cached per worker process)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=32)
def _load_template(tone: str, template_type: str) -> str:
    """
    Load a prompt template from disk. Cached per worker process via lru_cache.

    Args:
        tone:          One of VALID_TONES.
        template_type: "voice_response" | "session_title"

    Returns:
        str — Raw template content.

    Raises:
        FileNotFoundError if the template file is missing.
    """
    if tone not in VALID_TONES:
        raise ValueError(f"Invalid tone '{tone}'. Must be one of {VALID_TONES}")

    filename = f"{template_type}_{tone}.md"
    path = _PROMPTS_DIR / filename

    if not path.exists():
        raise FileNotFoundError(
            f"Voice persona template not found: {path}. "
            f"Ensure prompts/voice/{filename} exists in the repository."
        )

    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Internal: tone resolution
# ---------------------------------------------------------------------------


def _resolve_tone(
    user_id: UUID,
    db: Session,
    tenant_id: UUID,
    cache: dict[str, str] | None = None,
) -> str:
    """
    Resolve the effective tone for a user using the three-tier chain.

    Calls get_effective_setting_for_user() from services/setting_resolver.py.
    Falls back to DEFAULT_TONE ('balanced') if resolution returns None.

    Args:
        user_id:   The user whose tone to resolve.
        db:        Active SQLModel session.
        tenant_id: The active tenant.
        cache:     Optional per-request dict keyed by user_id str for memoization.

    Returns:
        str — One of VALID_TONES.
    """
    cache_key = str(user_id)
    if cache is not None and cache_key in cache:
        return cache[cache_key]

    from services.setting_resolver import get_effective_setting_for_user

    tone, _scope = get_effective_setting_for_user(
        db=db,
        tenant_id=tenant_id,
        user_id=user_id,
        setting_key="voice_persona_tone",
        fallback=DEFAULT_TONE,
    )

    # Validate — if an unexpected value slipped in, fall back gracefully
    if tone not in VALID_TONES:
        logger.warning(
            "Resolved tone '%s' is not valid; falling back to '%s'",
            tone,
            DEFAULT_TONE,
        )
        tone = DEFAULT_TONE

    if cache is not None:
        cache[cache_key] = tone

    return tone


# ---------------------------------------------------------------------------
# Internal: Ollama call helper
# ---------------------------------------------------------------------------


def _call_ollama(prompt: str) -> str:
    """
    Send a prompt to the local Ollama instance and return the response text.

    Uses generate_text_sync() from ai_service (established in B2).
    Falls back to a safe empty string on error (voice handlers already have
    their own fallback message paths).
    """
    try:
        from services.ai_service import generate_text_sync

        return generate_text_sync(prompt)
    except Exception as exc:
        logger.error("Ollama call failed in voice_persona_renderer: %s", exc)
        return ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render(
    payload: dict[str, Any],
    user_id: UUID,
    db: Session,
    tenant_id: UUID,
    tone_cache: dict[str, str] | None = None,
) -> str:
    """
    Render a tone-aware TTS-ready response string for a voice intent outcome.

    The payload format mirrors what intent handlers already produce:
        {
            "intent":  str,    # e.g. "create_quote"
            "outcome": str,    # "success" | "error" | "pending"
            "data":    dict,   # intent-specific context for template interpolation
        }

    Template variables are substituted using simple str.format_map() against
    payload["data"]. The template file defines the exact variable names.

    Args:
        payload:     Structured dict from an intent handler.
        user_id:     The user who issued the voice command (drives tone resolution).
        db:          Active SQLModel session (for settings lookup).
        tenant_id:   The active tenant.
        tone_cache:  Optional dict for per-request tone caching. Pass the same
                     dict across multiple render() calls in one request to avoid
                     repeated DB hits.

    Returns:
        str — The final TTS-ready response message string.
    """
    tone = _resolve_tone(user_id, db, tenant_id, tone_cache)

    try:
        template = _load_template(tone, _TEMPLATE_VOICE_RESPONSE)
    except FileNotFoundError:
        logger.warning(
            "Template missing for tone '%s'; falling back to balanced template", tone
        )
        template = _load_template(DEFAULT_TONE, _TEMPLATE_VOICE_RESPONSE)

    # Build the full prompt by injecting the intent payload into the template
    intent = payload.get("intent", "unknown")
    outcome = payload.get("outcome", "success")
    data = payload.get("data", {})

    # Substitute {{variable}} placeholders (design doc uses Jinja-style {{}} but
    # the templates use {variable} Python format syntax for simplicity)
    try:
        prompt = template.format_map(
            {
                "intent": intent,
                "outcome": outcome,
                **data,
            }
        )
    except KeyError as exc:
        logger.warning(
            "Template variable %s missing for intent '%s'; using raw template",
            exc,
            intent,
        )
        prompt = template

    response = _call_ollama(prompt)

    if not response:
        # Graceful fallback: return a minimal safe string rather than empty
        fallback = data.get("fallback_message", "Done.")
        logger.warning(
            "Ollama returned empty response for intent '%s'; using fallback", intent
        )
        return str(fallback)

    return response.strip()


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

    The title is generated once using the **session creator's** tone (per A67
    Decision 7). Subsequent viewers see the creator's rendered title regardless
    of their own tone setting.

    Args:
        session_context: Brief context string summarizing the session opening
                         (e.g., "Create quote for Mike's Diner, 3 breaker panels").
        creator_user_id: UUID of the user who created the session.
        db:              Active SQLModel session.
        tenant_id:       The active tenant.

    Returns:
        str — Generated title string (max 60 characters per template instruction).
    """
    tone = _resolve_tone(creator_user_id, db, tenant_id)

    try:
        template = _load_template(tone, _TEMPLATE_SESSION_TITLE)
    except FileNotFoundError:
        logger.warning(
            "Session title template missing for tone '%s'; falling back to balanced",
            tone,
        )
        template = _load_template(DEFAULT_TONE, _TEMPLATE_SESSION_TITLE)

    try:
        prompt = template.format_map({"session_context": session_context})
    except KeyError:
        prompt = template

    title = _call_ollama(prompt)

    if not title:
        # Fallback: truncate session_context to 60 chars
        return session_context[:60].strip()

    # Enforce max 60-char contract from design doc
    title = title.strip()
    if len(title) > 60:
        title = title[:57].rstrip() + "..."

    return title


def get_empty_state_copy(
    user_id: UUID,
    db: Session,
    tenant_id: UUID,
) -> str:
    """
    Return the tone-appropriate empty-state copy for the Voice AI tab.

    Uses the **viewing user's** effective tone (per A67 Decision 8), distinct
    from session title generation which uses the creator's tone.

    This is a static lookup (no Ollama call) — instantaneous.

    Returns:
        str — Static empty-state string from EMPTY_STATE_COPY map.
    """
    tone = _resolve_tone(user_id, db, tenant_id)
    return EMPTY_STATE_COPY.get(tone, EMPTY_STATE_COPY[DEFAULT_TONE])


def get_preview_audio_urls() -> dict[str, str]:
    """
    Return a dict of tone → CDN URL for preview audio assets.

    Preview audio is static content served from CloudFront.
    The API does not verify that the S3 objects exist at request time.

    Returns:
        Dict mapping tone name → full CDN URL.
    """
    return {tone: f"{PREVIEW_AUDIO_BASE_URL}/{tone}.mp3" for tone in VALID_TONES}
