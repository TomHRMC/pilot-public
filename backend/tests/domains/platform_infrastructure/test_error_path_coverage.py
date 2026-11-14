"""API error-path coverage ratchet (TEST-UPLIFT-1A, scope item 1).

Mechanical audit + checked-in baseline + meta-test that fails on any NEW gap.

How it works
------------
1. ``_mutating_operations()`` parses ``openapi.json`` and returns every
   ``post``/``put``/``patch``/``delete`` operation, **excluding** paths ending
   in ``/test`` (coverage counts on the canonical twin) and paths under
   ``/api/v1/webhooks/`` (machine-consumed, own suites).

2. ``_endpoints_with_error_tests()`` is a grep-based heuristic over
   ``backend/tests/**/*.py``: an endpoint counts as covered when a test file
   contains the endpoint's path string **and** a 4xx/5xx status assertion
   (``status_code == 4``, ``== 401/403/404/409/410/422/500``, ``HTTP_4``,
   ``HTTP_5``). This is a **ratchet, not a proof** — false positives (a test
   file mentions the path and a 4xx code for an unrelated reason) are
   acceptable in the baseline; false negatives (a real error test that uses a
   different assertion style) are not, because the baseline captures them and
   the ratchet only fails on the *delta*.

3. ``test_no_new_error_path_gaps_vs_baseline()`` fails when:
   - (a) an uncovered mutating endpoint is **absent** from the baseline
     (new gap — someone added an endpoint without an error test and without
     adding it to the baseline), or
   - (b) a baseline entry has **become covered** (stale entry — prune the
     baseline so the ratchet stays tight).

The baseline file lives at ``backend/tests/baselines/error_path_coverage.json``
and may only **shrink** in a batch (design §G Q7). Growing it requires
Architect/Tom sign-off.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.domain_platform_infrastructure,
    pytest.mark.unit,
]

OPENAPI = Path(__file__).parents[3] / "openapi.json"
BASELINE = Path(__file__).parents[2] / "baselines" / "error_path_coverage.json"
TESTS_DIR = Path(__file__).parents[3] / "tests"

_MUTATING_METHODS = {"post", "put", "patch", "delete"}

# Regex for 4xx/5xx status assertions in test files.
# Matches: status_code == 4xx/5xx, HTTP_4xx/5xx, == 401, == 403, etc.
_STATUS_ASSERTION_RE = re.compile(
    r"(?:status_code\s*==\s*(?:4\d\d|5\d\d)"
    r"|HTTP_4\d\d|HTTP_5\d\d"
    r"|==\s*40[0-9]|==\s*4[1-9]\d|==\s*5\d\d)",
    re.IGNORECASE,
)


def _mutating_operations() -> list[dict]:
    """Return [{method, path, key}] for post/put/patch/delete ops.

    Excludes ``/test`` mirrors and ``/api/v1/webhooks/*``.
    """
    spec = json.loads(OPENAPI.read_text())
    ops: list[dict] = []
    for path, methods in spec.get("paths", {}).items():
        if path.startswith("/api/v1/webhooks/"):
            continue
        if path.endswith("/test"):
            continue
        for method, _spec in methods.items():
            if method.lower() in _MUTATING_METHODS:
                key = f"{method.upper()} {path}"
                ops.append({"method": method.upper(), "path": path, "key": key})
    return ops


def _endpoints_with_error_tests() -> set[str]:
    """Grep-based heuristic: endpoints evidenced by a test file containing the
    path string AND a 4xx/5xx status assertion.

    Fuzzy by design — see module docstring. Errs toward listing (false
    positives acceptable; false negatives captured by the baseline).
    """
    covered: set[str] = set()
    test_files = list(TESTS_DIR.rglob("*.py"))

    for op in _mutating_operations():
        path = op["path"]
        for tf in test_files:
            try:
                content = tf.read_text()
            except Exception:
                continue
            if path in content and _STATUS_ASSERTION_RE.search(content):
                covered.add(op["key"])
                break

    return covered


def test_no_new_error_path_gaps_vs_baseline() -> None:
    """Ratchet: fail on new uncovered endpoints or stale baseline entries."""
    all_ops = {op["key"] for op in _mutating_operations()}
    covered = _endpoints_with_error_tests()
    uncovered = all_ops - covered

    baseline: dict[str, str] = {}
    if BASELINE.exists():
        baseline = json.loads(BASELINE.read_text())

    # (a) New gap: uncovered endpoint absent from baseline.
    new_gaps = uncovered - set(baseline.keys())
    assert not new_gaps, (
        f"New uncovered mutating endpoints (no error test AND not in baseline): "
        f"{sorted(new_gaps)}. Add an error-path test or add to the baseline "
        f"with Architect sign-off."
    )

    # (b) Stale entry: baseline entry has become covered — prune it.
    stale = set(baseline.keys()) & covered
    # Only flag entries that are still valid ops (not deleted endpoints).
    stale_and_valid = stale & all_ops
    assert not stale_and_valid, (
        f"Baseline entries now covered by tests (prune the baseline): "
        f"{sorted(stale_and_valid)}."
    )

    # (c) Deleted endpoint still in baseline — prune.
    deleted_in_baseline = set(baseline.keys()) - all_ops
    assert not deleted_in_baseline, (
        f"Baseline references deleted endpoints (prune the baseline): "
        f"{sorted(deleted_in_baseline)}."
    )
