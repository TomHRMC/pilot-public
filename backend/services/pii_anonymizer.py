"""
PII detection and replacement utility for the anonymization pipeline.

Used exclusively by anonymize_help_sessions Celery task (B16/A88).
Conservative approach: when uncertain, strip rather than preserve.
Regex-only for MVP — NER deferred to Phase 2 per design doc §F.6.
"""

import re
from typing import Any

# ──────────────────────────────────────────────────────────────────────────────
# PII detection patterns
# ──────────────────────────────────────────────────────────────────────────────

_EMAIL_RE = re.compile(
    r"[\w._%+\-]+@[\w.\-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)

_PHONE_RE = re.compile(
    r"(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})",
)

_UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
)

# US street address: number + word(s) + suffix (St, Ave, Blvd, Rd, Dr, Ln, Way, Ct, etc.)
_ADDRESS_RE = re.compile(
    r"\b\d{1,5}\s+[A-Za-z][A-Za-z0-9\s]{1,30}"
    r"\s+(?:St(?:reet)?|Ave(?:nue)?|Blvd|Boulevard|Rd|Road|Dr(?:ive)?|"
    r"Ln|Lane|Way|Ct|Court|Pl|Place|Pkwy|Parkway)\b",
    re.IGNORECASE,
)

# Long alphanumeric account/token numbers (12+ chars without spaces)
_ACCOUNT_NUM_RE = re.compile(
    r"\b[A-Za-z0-9]{12,}\b",
)

# Order matters: UUID must run BEFORE phone to avoid partial UUID matches
# being replaced by phone regex first (UUID contains digit sequences)
_REPLACEMENTS = [
    (_EMAIL_RE, "[email]"),
    (_UUID_RE, "[id]"),
    (_PHONE_RE, "[phone]"),
    (_ADDRESS_RE, "[address]"),
]


def anonymize_text(text: str) -> str:
    """
    Detect and replace PII in a text string.

    Replacement map:
    - Email addresses      → [email]     (regex: email pattern)
    - US phone numbers     → [phone]     (regex: various US formats)
    - UUID/identifiers     → [id]        (regex: 8-4-4-4-12 hex UUID pattern)
    - Addresses            → [address]   (street number + word + street suffix)

    Note: NER-based name/business detection is deferred to Phase 2.
    Regex handles highest-risk PII for MVP.

    Args:
        text: Raw message content possibly containing PII.

    Returns:
        Anonymized text with PII replaced by bracketed placeholders.
    """
    if not text:
        return text

    result = text
    for pattern, replacement in _REPLACEMENTS:
        result = pattern.sub(replacement, result)

    return result


def anonymize_context_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Strip any PII from a context payload dict.

    Context payloads contain only action-type labels per the privacy boundary,
    but tenant_metadata.size / tenant_metadata.trade fields are safe to retain.
    This function is a safety pass to ensure no entity contents slipped through.

    Args:
        payload: Context payload dict from help_chat_message.context_payload.

    Returns:
        Sanitized copy of the payload dict.
    """
    if not payload:
        return payload

    import copy

    sanitized = copy.deepcopy(payload)

    # Route: keep path structure but strip query params if present
    if "route" in sanitized and isinstance(sanitized["route"], str):
        # Strip anything after ? (query params may contain entity IDs)
        sanitized["route"] = sanitized["route"].split("?")[0]

    # recent_actions: apply text anonymization to each action label
    if "recent_actions" in sanitized and isinstance(sanitized["recent_actions"], list):
        sanitized["recent_actions"] = [
            anonymize_text(str(action)) for action in sanitized["recent_actions"]
        ]

    # user_role: safe to retain (non-PII)

    # tenant_metadata: retain size/trade but anonymize anything else
    if "tenant_metadata" in sanitized and isinstance(
        sanitized["tenant_metadata"], dict
    ):
        safe_keys = {"size", "trade"}
        sanitized["tenant_metadata"] = {
            k: v for k, v in sanitized["tenant_metadata"].items() if k in safe_keys
        }

    # entity_type: safe to retain (e.g. "quote", "job")

    return sanitized
