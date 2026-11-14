"""
B17 — Unit tests for has_permission() wildcard behaviour.

Verifies that:
  1. Full wildcard ("*") grants any permission
  2. Resource wildcard ("quotes.*") grants any action on that resource
  3. Action wildcard ("*.view") grants view on any resource
  4. Exact match still works
  5. Missing permissions are correctly denied

Domain: identity_access
Batch: B17 Part A
"""

import pytest

from core.permissions import has_permission

pytestmark = [
    pytest.mark.domain_identity_access,
    pytest.mark.unit,
]


class TestHasPermissionWildcard:
    """B17/A1 — has_permission() wildcard matching regression suite."""

    # ── Full wildcard "*" ──────────────────────────────────────────────────

    def test_full_wildcard_grants_any_permission(self):
        """has_permission(['*'], X) must be True for any X."""
        assert has_permission(["*"], "communications.view") is True

    def test_full_wildcard_grants_invoices_view(self):
        assert has_permission(["*"], "invoices.view") is True

    def test_full_wildcard_grants_arbitrary_permission(self):
        assert has_permission(["*"], "any.permission") is True

    def test_full_wildcard_grants_complex_permission(self):
        assert has_permission(["*"], "owner.field_issue.resolve") is True

    # ── Resource wildcard "resource.*" ────────────────────────────────────

    def test_resource_wildcard_grants_create(self):
        assert has_permission(["quotes.*"], "quotes.create") is True

    def test_resource_wildcard_grants_view(self):
        assert has_permission(["quotes.*"], "quotes.view") is True

    def test_resource_wildcard_does_not_grant_other_resource(self):
        assert has_permission(["quotes.*"], "invoices.create") is False

    # ── Action wildcard "*.action" ─────────────────────────────────────────

    def test_action_wildcard_grants_view_on_any_resource(self):
        assert has_permission(["*.view"], "quotes.view") is True

    def test_action_wildcard_grants_view_on_invoices(self):
        assert has_permission(["*.view"], "invoices.view") is True

    def test_action_wildcard_does_not_grant_different_action(self):
        assert has_permission(["*.view"], "quotes.create") is False

    # ── Exact match ────────────────────────────────────────────────────────

    def test_exact_match(self):
        assert has_permission(["quotes.view"], "quotes.view") is True

    def test_exact_match_different_permission_denied(self):
        assert has_permission(["quotes.view"], "quotes.create") is False

    # ── Empty / missing permissions ────────────────────────────────────────

    def test_empty_permissions_denied(self):
        assert has_permission([], "quotes.view") is False

    def test_unrelated_permission_denied(self):
        assert has_permission(["jobs.view", "jobs.update"], "quotes.create") is False

    # ── Owner use-case (all B17 permissions that were returning 403) ───────

    def test_owner_can_view_communications(self):
        """B17/A3 root cause — owner with ['*'] must not 403 on communications.view."""
        assert has_permission(["*"], "communications.view") is True

    def test_owner_can_view_field_issues(self):
        assert has_permission(["*"], "field_issue.view") is True

    def test_owner_can_resolve_field_issues(self):
        assert has_permission(["*"], "field_issue.resolve") is True
