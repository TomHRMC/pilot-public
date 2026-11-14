"""
Help AI agent service.

Responsible for:
- Loading tone-specific prompt templates from prompts/help/
- Constructing the full RAG-injected prompt
- Calling Ollama via generate_text_sync()

B16/A84 — Established in Batch B16.
"""

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Path to prompt templates: backend/prompts/help/
_PROMPTS_DIR = Path(__file__).parent.parent / "prompts" / "help"

_VALID_TONES = frozenset({"conservative", "balanced", "playful"})

_FALLBACK_TEMPLATE = """You are Pilot, an AI assistant built to help electrical contractors use Pilot for Trades.
Be helpful, accurate, and concise. Answer based on the provided help article excerpts.
If you don't know the answer from the provided context, say so honestly.

{rag_context}

{conversation_history}

User: {user_message}
Assistant:"""


def generate_help_response(
    user_message: str,
    retrieved_chunks: list[dict[str, Any]],
    conversation_history: list[dict[str, str]],
    context_payload: dict[str, Any] | None,
    tone: str,
) -> str:
    """
    Build help agent prompt and generate AI response via Ollama.

    Args:
        user_message:          The user's current question text.
        retrieved_chunks:      Top-K chunks from help_retrieval.retrieve_chunks().
                               Each dict has keys: article_id, section_title, chunk_text, score.
        conversation_history:  Prior turns as [{"role": "user"|"assistant", "content": str}, ...].
                               Used to maintain conversational context.
        context_payload:       Surface context from client (route, recent_actions, user_role,
                               tenant_metadata). May be None for voice-only help invocations.
        tone:                  'conservative' | 'balanced' | 'playful'. Selects prompt template
                               variant from prompts/help/help_agent_{tone}.md.

    Returns:
        The AI assistant's response text. Callers are responsible for persisting
        to help_chat_message.

    Raises:
        ValueError: If tone is not one of the three allowed values.
        httpx.HTTPError: If the Ollama API is unavailable (propagates for caller to handle).
    """
    if tone not in _VALID_TONES:
        raise ValueError(
            f"Invalid tone '{tone}'. Must be one of: {sorted(_VALID_TONES)}"
        )

    template = _load_prompt_template(tone)
    prompt = _render_prompt(
        template, user_message, retrieved_chunks, conversation_history, context_payload
    )

    from services.ai_service import generate_text_sync

    return generate_text_sync(prompt=prompt, max_tokens=512)


def _load_prompt_template(tone: str) -> str:
    """
    Load the help agent prompt template for the given tone.

    Template files live at backend/prompts/help/help_agent_{tone}.md.
    Falls back to inline template if file not found (dev convenience).
    """
    template_path = _PROMPTS_DIR / f"help_agent_{tone}.md"
    if template_path.exists():
        return template_path.read_text(encoding="utf-8")

    logger.debug(f"Prompt template not found at {template_path} — using fallback")
    return _FALLBACK_TEMPLATE


def _render_prompt(
    template: str,
    user_message: str,
    chunks: list[dict[str, Any]],
    history: list[dict[str, str]],
    context: dict[str, Any] | None,
) -> str:
    """
    Fill the template with RAG chunks, history, and context payload.
    Returns the fully assembled prompt string ready for generate_text_sync().
    """
    # Build RAG context block
    if chunks:
        rag_parts = []
        for i, chunk in enumerate(chunks, 1):
            rag_parts.append(
                f"[{i}] {chunk['article_id']} — {chunk['section_title']}\n{chunk['chunk_text']}"
            )
        rag_context = "Relevant help content:\n\n" + "\n\n---\n\n".join(rag_parts)
    else:
        rag_context = "No relevant help articles found for this question."

    # Build conversation history block (last 6 turns max to keep context window small)
    if history:
        recent = history[-6:]
        history_parts = []
        for turn in recent:
            role_label = "User" if turn["role"] == "user" else "Assistant"
            history_parts.append(f"{role_label}: {turn['content']}")
        conversation_history = "Previous conversation:\n" + "\n".join(history_parts)
    else:
        conversation_history = ""

    # Build context hint from payload
    context_hint = ""
    if context:
        route = context.get("route")
        recent_actions = context.get("recent_actions", [])
        if route:
            context_hint = f"[User is currently on page: {route}"
            if recent_actions:
                context_hint += f", recent actions: {', '.join(recent_actions[:3])}"
            context_hint += "]"

    # Compose full user message with context hint
    full_user_message = user_message
    if context_hint:
        full_user_message = f"{context_hint}\n{user_message}"

    # Try template substitution, fallback to simple format
    try:
        return template.format(
            rag_context=rag_context,
            conversation_history=conversation_history,
            user_message=full_user_message,
        )
    except KeyError:
        # Template has different placeholders — use as-is with appended context
        return (
            f"{template}\n\n{rag_context}\n\n{conversation_history}\n\n"
            f"User: {full_user_message}\nAssistant:"
        )
