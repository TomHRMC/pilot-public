"""
tests/batch_b7b/test_a40_conflict_classification.py

Tests for B7b/A40 — Conflict Severity Classification Engine.

Test focus cases (per design doc):
  1. Platform default row lookup → correct SyncResolution returned
  2. Tenant override row takes priority over platform default
  3. Unknown operation_type+trigger falls back to tech_resolvable
  4. is_active=False rows are ignored (only active rows matched)
  5. SyncResolution flags are correctly derived from severity
  6. compute_field_diffs: identical dicts → all unchanged
  7. compute_field_diffs: modified field → both sides 'modified'
  8. compute_field_diffs: tech-only field → tech 'removed', server 'added'
  9. compute_field_diffs: server-only field → tech 'added', server 'removed'
  10. build_escalation_explainer: produces expected string
"""

from app.models.system import SyncConflictClassificationMatrix
from services.mobile_sync_conflict import (
    SyncResolution,
    build_escalation_explainer,
    classify_sync_conflict,
    compute_field_diffs,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _insert_matrix_row(
    db_session,
    operation_type: str,
    trigger_condition: str,
    severity: str,
    reason: str,
    tenant_id=None,
    is_active: bool = True,
) -> SyncConflictClassificationMatrix:
    row = SyncConflictClassificationMatrix(
        operation_type=operation_type,
        trigger_condition=trigger_condition,
        severity=severity,
        classification_reason=reason,
        tenant_id=tenant_id,
        is_active=is_active,
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


# ---------------------------------------------------------------------------
# classify_sync_conflict — platform default row lookup
# ---------------------------------------------------------------------------


class TestClassifySyncConflict:
    def test_platform_default_auto_silent(self, db_session, test_tenant):
        """Platform default row → auto_silent severity, correct flags."""
        # Seed from migration provides this row; we add an extra unique one to avoid
        # relying on migration seed UUIDs.
        _insert_matrix_row(
            db_session,
            operation_type="test_op_auto",
            trigger_condition="trigger_a",
            severity="auto_silent",
            reason="Test auto silent reason",
        )

        result = classify_sync_conflict(
            operation_type="test_op_auto",
            trigger_condition="trigger_a",
            tenant_id=test_tenant.id,
            db=db_session,
        )

        assert isinstance(result, SyncResolution)
        assert result.severity == "auto_silent"
        assert result.auto_resolved is True
        assert result.tech_action_required is False
        assert result.owner_escalation_required is False
        assert result.classification_reason == "Test auto silent reason"

    def test_platform_default_tech_resolvable(self, db_session, test_tenant):
        """Platform default → tech_resolvable flags."""
        _insert_matrix_row(
            db_session,
            operation_type="test_op_tech",
            trigger_condition="trigger_b",
            severity="tech_resolvable",
            reason="Tech must decide",
        )

        result = classify_sync_conflict(
            operation_type="test_op_tech",
            trigger_condition="trigger_b",
            tenant_id=test_tenant.id,
            db=db_session,
        )

        assert result.severity == "tech_resolvable"
        assert result.auto_resolved is False
        assert result.tech_action_required is True
        assert result.owner_escalation_required is False

    def test_platform_default_owner_escalation(self, db_session, test_tenant):
        """Platform default → owner_escalation flags."""
        _insert_matrix_row(
            db_session,
            operation_type="test_op_owner",
            trigger_condition="trigger_c",
            severity="owner_escalation",
            reason="Needs owner review",
        )

        result = classify_sync_conflict(
            operation_type="test_op_owner",
            trigger_condition="trigger_c",
            tenant_id=test_tenant.id,
            db=db_session,
        )

        assert result.severity == "owner_escalation"
        assert result.auto_resolved is False
        assert result.tech_action_required is False
        assert result.owner_escalation_required is True

    def test_tenant_override_takes_priority_over_platform_default(
        self, db_session, test_tenant
    ):
        """Tenant override row is selected over platform default for same op+trigger."""
        # Insert platform default
        _insert_matrix_row(
            db_session,
            operation_type="test_op_override",
            trigger_condition="trigger_d",
            severity="auto_silent",
            reason="Platform default reason",
            tenant_id=None,
        )
        # Insert tenant override with different severity
        _insert_matrix_row(
            db_session,
            operation_type="test_op_override",
            trigger_condition="trigger_d",
            severity="owner_escalation",
            reason="Tenant override reason",
            tenant_id=test_tenant.id,
        )

        result = classify_sync_conflict(
            operation_type="test_op_override",
            trigger_condition="trigger_d",
            tenant_id=test_tenant.id,
            db=db_session,
        )

        # Tenant override must win
        assert result.severity == "owner_escalation"
        assert result.classification_reason == "Tenant override reason"

    def test_unknown_op_trigger_fallback_to_tech_resolvable(
        self, db_session, test_tenant
    ):
        """No matching row → fallback to tech_resolvable with generic reason."""
        result = classify_sync_conflict(
            operation_type="completely_unknown_op",
            trigger_condition="completely_unknown_trigger",
            tenant_id=test_tenant.id,
            db=db_session,
        )

        assert result.severity == "tech_resolvable"
        assert result.tech_action_required is True
        assert "No classification rule found" in result.classification_reason

    def test_inactive_row_is_ignored(self, db_session, test_tenant):
        """is_active=False platform row is skipped; fallback is triggered."""
        _insert_matrix_row(
            db_session,
            operation_type="test_op_inactive",
            trigger_condition="trigger_e",
            severity="auto_silent",
            reason="This row is inactive",
            is_active=False,
        )

        result = classify_sync_conflict(
            operation_type="test_op_inactive",
            trigger_condition="trigger_e",
            tenant_id=test_tenant.id,
            db=db_session,
        )

        # Inactive row must not be matched; fallback applies
        assert result.severity == "tech_resolvable"

    def test_auto_notice_severity(self, db_session, test_tenant):
        """auto_notice → auto_resolved=True, other flags False."""
        _insert_matrix_row(
            db_session,
            operation_type="test_op_notice",
            trigger_condition="trigger_f",
            severity="auto_notice",
            reason="Category renamed",
        )

        result = classify_sync_conflict(
            operation_type="test_op_notice",
            trigger_condition="trigger_f",
            tenant_id=test_tenant.id,
            db=db_session,
        )

        assert result.severity == "auto_notice"
        assert result.auto_resolved is True
        assert result.tech_action_required is False
        assert result.owner_escalation_required is False


# ---------------------------------------------------------------------------
# Seeded platform defaults from migration (spot-check 3 rows)
# ---------------------------------------------------------------------------


class TestSeededMatrixRows:
    def test_time_entry_job_still_assigned_is_auto_silent(
        self, db_session, test_tenant
    ):
        """Seeded row: time_entry + job_still_assigned → auto_silent."""
        result = classify_sync_conflict(
            operation_type="time_entry",
            trigger_condition="job_still_assigned",
            tenant_id=test_tenant.id,
            db=db_session,
        )
        assert result.severity == "auto_silent"

    def test_time_entry_job_deleted_is_owner_escalation(self, db_session, test_tenant):
        """Seeded row: time_entry + job_deleted → owner_escalation."""
        result = classify_sync_conflict(
            operation_type="time_entry",
            trigger_condition="job_deleted",
            tenant_id=test_tenant.id,
            db=db_session,
        )
        assert result.severity == "owner_escalation"

    def test_expense_category_renamed_is_auto_notice(self, db_session, test_tenant):
        """Seeded row: expense + category_renamed → auto_notice."""
        result = classify_sync_conflict(
            operation_type="expense",
            trigger_condition="category_renamed",
            tenant_id=test_tenant.id,
            db=db_session,
        )
        assert result.severity == "auto_notice"


# ---------------------------------------------------------------------------
# compute_field_diffs
# ---------------------------------------------------------------------------


class TestComputeFieldDiffs:
    def test_identical_dicts_all_unchanged(self):
        """Both versions identical → all fields unchanged."""
        tech = {"job_id": "abc", "hours": 3.5}
        server = {"job_id": "abc", "hours": 3.5}
        diffs = compute_field_diffs(tech, server)

        assert len(diffs) == 2
        for d in diffs:
            assert d["tech_change"] == "unchanged"
            assert d["server_change"] == "unchanged"

    def test_modified_field(self):
        """Field exists in both but values differ → both marked 'modified'."""
        tech = {"hours": 3.5}
        server = {"hours": 4.0}
        diffs = compute_field_diffs(tech, server)

        assert len(diffs) == 1
        assert diffs[0]["field_name"] == "hours"
        assert diffs[0]["tech_change"] == "modified"
        assert diffs[0]["server_change"] == "modified"
        assert diffs[0]["tech_value"] == 3.5
        assert diffs[0]["server_value"] == 4.0

    def test_tech_only_field(self):
        """Field only in tech_version → tech 'removed', server 'added'."""
        tech = {"extra_field": "foo"}
        server = {}
        diffs = compute_field_diffs(tech, server)

        assert len(diffs) == 1
        assert diffs[0]["tech_change"] == "removed"
        assert diffs[0]["server_change"] == "added"

    def test_server_only_field(self):
        """Field only in server_version → tech 'added', server 'removed'."""
        tech = {}
        server = {"new_server_field": "bar"}
        diffs = compute_field_diffs(tech, server)

        assert len(diffs) == 1
        assert diffs[0]["tech_change"] == "added"
        assert diffs[0]["server_change"] == "removed"

    def test_none_inputs_return_empty_list(self):
        """None for both inputs → empty diff list (no crash)."""
        diffs = compute_field_diffs(None, None)
        assert diffs == []

    def test_mixed_changes(self):
        """Mixed: one unchanged, one modified, one tech-only."""
        tech = {"a": 1, "b": 99, "c": "old"}
        server = {"a": 1, "b": 100}
        diffs = compute_field_diffs(tech, server)

        by_field = {d["field_name"]: d for d in diffs}

        assert by_field["a"]["tech_change"] == "unchanged"
        assert by_field["b"]["tech_change"] == "modified"
        assert by_field["c"]["tech_change"] == "removed"
        assert by_field["c"]["server_change"] == "added"


# ---------------------------------------------------------------------------
# build_escalation_explainer
# ---------------------------------------------------------------------------


class TestBuildEscalationExplainer:
    def test_explainer_contains_operation_type(self):
        result = build_escalation_explainer(
            "time_entry", "job_deleted", "Job deleted while tech was working it"
        )
        assert "time_entry" in result

    def test_explainer_contains_trigger(self):
        result = build_escalation_explainer(
            "time_entry", "job_deleted", "Job deleted while tech was working it"
        )
        assert "job_deleted" in result

    def test_explainer_contains_reason(self):
        result = build_escalation_explainer(
            "time_entry", "job_deleted", "Job deleted while tech was working it"
        )
        assert "Job deleted while tech was working it" in result

    def test_explainer_contains_owner_action(self):
        """Explainer must signal owner action is required."""
        result = build_escalation_explainer("expense", "job_deleted", "Job deleted")
        assert "owner action required" in result
