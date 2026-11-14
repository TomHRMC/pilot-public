"""Tenant site template renderer — C-B16 Part A.

Uses stdlib ``string.Template`` (``${field}`` tokens) — no new dependency.
Templates are code-resident (``v1/{landing,privacy,terms}.md``); a future
language revision = new ``v2/`` directory + re-publish flow.

The renderer returns pre-escaped plain text with paragraphs split on blank
lines. The frontend renders without a markdown parser and with zero HTML
injection surface (§G-6).
"""

from __future__ import annotations

import importlib.resources as resources
from string import Template


def _load_template(page: str, version: str) -> str:
    """Load the raw template text for a page/version pair."""
    pkg = f"services.tenant_site_templates.{version}"
    filename = f"{page}.md"
    try:
        return resources.files(pkg).joinpath(filename).read_text(encoding="utf-8")
    except (FileNotFoundError, ModuleNotFoundError) as exc:
        raise ValueError(
            f"Unknown template page={page!r} version={version!r}: {exc}"
        ) from exc


def _escape_plain_text(value: str | None) -> str:
    """Escape HTML-special characters and normalize whitespace.

    The frontend renders this as plain text (no markdown), so we strip
    any HTML injection surface by escaping <, >, &.
    """
    if value is None:
        return ""
    # Escape HTML entities
    safe = value.replace("&", "&").replace("<", "<").replace(">", ">")
    # Normalize internal whitespace but preserve content
    return safe.strip()


def _split_paragraphs(text: str) -> list[str]:
    """Split rendered template text into paragraphs on blank lines.

    Each paragraph is stripped of leading/trailing whitespace. Empty
    paragraphs are removed.
    """
    paragraphs: list[str] = []
    for chunk in text.split("\n\n"):
        cleaned = chunk.strip()
        if cleaned:
            paragraphs.append(cleaned)
    return paragraphs


def render_template(page: str, version: str, context: dict) -> str:
    """Render a template page with the given context.

    Args:
        page: 'landing', 'privacy', or 'terms'.
        version: template version directory (e.g. 'v1').
        context: dict of ``${field}`` token values. All values are
            escaped to plain text before substitution.

    Returns:
        Rendered plain-text string (paragraph-split by the caller).

    Raises:
        ValueError: if the page/version combination is unknown.
    """
    raw = _load_template(page, version)
    # Escape all context values to plain text
    safe_context: dict[str, str] = {}
    for key, val in context.items():
        if isinstance(val, str):
            safe_context[key] = _escape_plain_text(val)
        elif val is None:
            safe_context[key] = ""
        else:
            safe_context[key] = _escape_plain_text(str(val))
    tmpl = Template(raw)
    return tmpl.safe_substitute(safe_context)


def render_page_paragraphs(page: str, version: str, context: dict) -> list[str]:
    """Render a template and return it as a list of paragraph strings."""
    rendered = render_template(page, version, context)
    return _split_paragraphs(rendered)


__all__ = [
    "render_page_paragraphs",
    "render_template",
]
