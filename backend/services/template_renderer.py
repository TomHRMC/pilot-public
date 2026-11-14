import logging
from typing import Any

from jinja2 import Environment, TemplateError

logger = logging.getLogger(__name__)

# Setup Jinja2 environment with autoescape
jinja_env = Environment(autoescape=True)


def render_template(template_string: str, context: dict[str, Any]) -> str:
    """
    Render a Jinja2 template string with the given context.

    Args:
        template_string: The Jinja2 template string
        context: Dictionary of variables to inject

    Returns:
        Rendered string

    Raises:
        ValueError: If template rendering fails
    """
    if not template_string:
        return ""

    try:
        template = jinja_env.from_string(template_string)
        return template.render(**context)
    except TemplateError as e:
        logger.error(f"Template rendering error: {e}")
        # In a production system, we might want to return the raw string
        # or a fallback, but raising allows the caller to handle it (e.g., mark failed)
        raise ValueError(f"Failed to render template: {e}")
    except Exception as e:
        logger.error(f"Unexpected template error: {e}")
        raise ValueError(f"Unexpected error rendering template: {e}")


def render_subject(subject_string: str, context: dict[str, Any]) -> str:
    """
    Render a subject line (same as body, but often simpler).
    """
    return render_template(subject_string, context)
