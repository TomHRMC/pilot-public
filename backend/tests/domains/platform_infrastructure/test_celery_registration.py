"""Guard: every module in backend/tasks/ must be registered in celery_app.conf.imports.

Incident class 2026-08-10 (and again design-time 2026-08-27: tasks/tenant_site_emails.py
was missing — event-driven .delay() publishes from the API container, but the worker only
imports modules listed in celery_app.conf.imports, so messages never execute).

This is a mechanical ratchet: any new task module added to backend/tasks/ that is not
also appended to the imports list in core/celery_app.py will fail this test, surfacing
the omission before it reaches prod.
"""

from pathlib import Path

import pytest

from core.celery_app import celery_app

pytestmark = [
    pytest.mark.domain_platform_infrastructure,
    pytest.mark.unit,
]

TASKS_DIR = Path(__file__).parents[3] / "tasks"


def _task_modules_on_disk() -> set[str]:
    """Every importable module in backend/tasks/ (excl. __init__), as 'tasks.<name>'."""
    return {f"tasks.{p.stem}" for p in TASKS_DIR.glob("*.py") if p.stem != "__init__"}


def test_every_task_module_is_registered_in_celery_imports() -> None:
    """2026-08-10 incident class: worker silently never registers an unlisted module."""
    registered = set(celery_app.conf.imports or ())
    missing = _task_modules_on_disk() - registered
    assert not missing, (
        f"Task modules missing from celery_app.conf.imports: {sorted(missing)}. "
        "Add them or the worker will never register their tasks."
    )
