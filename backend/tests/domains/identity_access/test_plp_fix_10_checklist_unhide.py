"""
PLP-FIX-10 / INV-BUG-14 — Checklist unhide persistence regression test.

Domain: identity_access (PRD §3.5 — onboarding)

Root cause: PUT /api/v1/tenants/{tenant_id}/onboarding/checklist/hidden only
called hide_checklist() when payload.hidden was True — the False branch
returned {"checklist_hidden": false} WITHOUT persisting anything. The FE
optimistic expand would re-collapse on next refetch because the server flag
never cleared.

This test reproduces the exact prod scenario:
  PUT hidden=true  → GET shows checklist_hidden=true
  PUT hidden=false → GET shows checklist_hidden=false  (was true before the fix)
"""

import pytest
from sqlalchemy import text

pytestmark = [
    pytest.mark.domain_identity_access,
    pytest.mark.unit,
]


def _delete_checklist(db_session, tenant_id):
    """Remove any pre-existing checklist row so tests start from a clean state."""
    db_session.execute(
        text("DELETE FROM public.tenant_onboarding_checklist WHERE tenant_id = :tid"),
        {"tid": str(tenant_id)},
    )
    db_session.commit()


class TestChecklistUnhidePersistence:
    """INV-BUG-14: the unhide path must persist checklist_hidden=false."""

    def test_hide_then_unhide_persists_across_refetch(
        self, client, db_session, test_tenant
    ):
        """PUT hidden=true → GET true → PUT hidden=false → GET false (the prod repro)."""
        _delete_checklist(db_session, test_tenant.id)

        # Step 1: Hide the checklist.
        resp_hide = client.put(
            f"/api/v1/tenants/{test_tenant.id}/onboarding/checklist/hidden/test",
            json={"hidden": True},
        )
        assert resp_hide.status_code == 200
        assert resp_hide.json()["checklist_hidden"] is True

        # Step 2: GET confirms the server persisted hidden=true.
        resp_get_hidden = client.get(
            f"/api/v1/tenants/{test_tenant.id}/onboarding/checklist/test"
        )
        assert resp_get_hidden.status_code == 200
        assert resp_get_hidden.json()["checklist_hidden"] is True

        # Step 3: Unhide the checklist (the path that was broken before the fix).
        resp_unhide = client.put(
            f"/api/v1/tenants/{test_tenant.id}/onboarding/checklist/hidden/test",
            json={"hidden": False},
        )
        assert resp_unhide.status_code == 200
        assert resp_unhide.json()["checklist_hidden"] is False

        # Step 4: GET confirms the server persisted hidden=false.
        # Before the fix, this returned True — the exact prod repro.
        resp_get_unhidden = client.get(
            f"/api/v1/tenants/{test_tenant.id}/onboarding/checklist/test"
        )
        assert resp_get_unhidden.status_code == 200
        assert resp_get_unhidden.json()["checklist_hidden"] is False

    def test_unhide_on_fresh_checklist(self, client, db_session, test_tenant):
        """Unhide on a fresh checklist (already false) is idempotent."""
        _delete_checklist(db_session, test_tenant.id)

        resp = client.put(
            f"/api/v1/tenants/{test_tenant.id}/onboarding/checklist/hidden/test",
            json={"hidden": False},
        )
        assert resp.status_code == 200
        assert resp.json()["checklist_hidden"] is False

        # GET confirms it's still false.
        resp_get = client.get(
            f"/api/v1/tenants/{test_tenant.id}/onboarding/checklist/test"
        )
        assert resp_get.json()["checklist_hidden"] is False
