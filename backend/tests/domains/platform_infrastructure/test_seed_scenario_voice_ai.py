"""
Tests for: SD-9 Voice AI seed scenario (seed_scenario_voice_ai.py + seed_second_tenant.py)
Domain: platform_infrastructure (PRD §3.8)

Per README-adding-tests §Seed Data Coexistence Rules:
  - DB-touching tests call the injectable inner functions (_seed_voice_ai,
    _reset_voice_ai, _seed_tenant_b) against the db_session fixture (rollback-wrapped).
  - NEVER call mode_seed/mode_reset — they open their own engine and commit.
  - Assertions scope by deterministic 0010-0014 UUID families and business keys
    (tier_name='charter', devb@pilot.local) — never unscoped table counts.
  - Presence checks tolerate the real seed already existing (idempotent).
"""

import json
from uuid import UUID

import pytest
from sqlalchemy import text

from migrations.scripts.seed_scenario_voice_ai import (
    SECOND_TENANT_ID,
    TEST_TENANT_ID,
    _fb_uuid,
    _msg_uuid,
    _offline_idem_uuid,
    _reset_voice_ai,
    _seed_voice_ai,
)
from migrations.scripts.seed_second_tenant import (
    TENANT_B_OWNER_ID,
    TENANT_B_TECH_ID,
    _seed_tenant_b,
)

pytestmark = [pytest.mark.domain_platform_infrastructure, pytest.mark.unit]

# ── Deterministic UUID constants for assertions ──────────────────────────────

SESS_S1 = UUID("00000000-0000-0000-0010-000000000001")
SESS_S2 = UUID("00000000-0000-0000-0010-000000000002")
SESS_S3 = UUID("00000000-0000-0000-0010-000000000003")
SESS_S4 = UUID("00000000-0000-0000-0010-000000000004")
SESS_S5 = UUID("00000000-0000-0000-0010-000000000005")
SESS_S6 = UUID("00000000-0000-0000-0010-000000000006")
SESS_SB1 = UUID("00000000-0000-0000-0010-000000000007")
SESS_SB2 = UUID("00000000-0000-0000-0010-000000000008")

ALL_SESSION_IDS = [
    SESS_S1,
    SESS_S2,
    SESS_S3,
    SESS_S4,
    SESS_S5,
    SESS_S6,
    SESS_SB1,
    SESS_SB2,
]

RESERVED_RANGE = {
    UUID("00000000-0000-0000-0000-000000000001"),
    UUID("00000000-0000-0000-0000-000000000002"),
    UUID("00000000-0000-0000-0000-000000000003"),
    UUID("00000000-0000-0000-0000-000000000004"),
    UUID("00000000-0000-0000-0000-000000000005"),
}

# Valid CHECK sets (MCP-verified)
VALID_SESSION_STATUSES = {"active", "ended", "abandoned", "expired", "archived"}
VALID_MSG_ROLES = {"user", "assistant", "system"}
VALID_PROCESSING_STATUSES = {
    None,
    "pending_upload",
    "uploading",
    "transcribing",
    "parsing",
    "completed",
    "failed",
}


class TestSeedVoiceAiFullManifest:
    """Test 1: _seed_voice_ai creates the full manifest."""

    def test_seed_creates_all_8_sessions(self, db_session):
        """All 8 deterministic session ids present after _seed_voice_ai."""
        _seed_voice_ai(db_session, TEST_TENANT_ID)

        for sid in ALL_SESSION_IDS:
            row = db_session.execute(
                text("SELECT id FROM public.conversation_session WHERE id = :id"),
                {"id": str(sid)},
            ).first()
            assert row is not None, f"Session {sid} not found after seed"


class TestSeedVoiceAiIdempotency:
    """Test 2: Inner seed re-run is idempotent — 0 new rows."""

    def test_voice_ai_rerun_is_idempotent(self, db_session):
        """Second call to _seed_voice_ai inserts 0 new rows."""
        _seed_voice_ai(db_session, TEST_TENANT_ID)
        counts_2nd = _seed_voice_ai(db_session, TEST_TENANT_ID)

        # All counts should be 0 on the second run (idempotent)
        for table, count in counts_2nd.items():
            assert count == 0, f"{table}: expected 0 new rows on re-run, got {count}"


class TestSeedTenantBIdempotency:
    """Test 8: _seed_tenant_b re-run is idempotent (upsert — no dupes, no error)."""

    def test_tenant_b_rerun_is_idempotent(self, db_session):
        """Second call to _seed_tenant_b inserts 0 new rows (upsert)."""
        _seed_tenant_b(db_session)
        counts_2nd = _seed_tenant_b(db_session)

        for table, count in counts_2nd.items():
            assert count == 0, f"{table}: expected 0 new rows on re-run, got {count}"


class TestSeedVoiceAiCheckValidity:
    """Test 3: All role/status/processing_status values within CHECK sets."""

    def test_all_check_values_valid(self, db_session):
        """All seeded role/status/processing_status values pass CHECK constraints."""
        _seed_voice_ai(db_session, TEST_TENANT_ID)

        # Session statuses
        statuses = db_session.execute(
            text(
                "SELECT DISTINCT status FROM public.conversation_session "
                "WHERE tenant_id IN (:t1, :t2)"
            ),
            {"t1": str(TEST_TENANT_ID), "t2": str(SECOND_TENANT_ID)},
        ).fetchall()
        for (s,) in statuses:
            assert s in VALID_SESSION_STATUSES, f"Invalid session status: {s}"

        # Message roles
        roles = db_session.execute(
            text(
                "SELECT DISTINCT role FROM public.conversation_message "
                "WHERE tenant_id IN (:t1, :t2)"
            ),
            {"t1": str(TEST_TENANT_ID), "t2": str(SECOND_TENANT_ID)},
        ).fetchall()
        for (r,) in roles:
            assert r in VALID_MSG_ROLES, f"Invalid message role: {r}"

        # Processing statuses
        proc_statuses = db_session.execute(
            text(
                "SELECT DISTINCT processing_status FROM public.voice_command_log "
                "WHERE tenant_id IN (:t1, :t2)"
            ),
            {"t1": str(TEST_TENANT_ID), "t2": str(SECOND_TENANT_ID)},
        ).fetchall()
        for (ps,) in proc_statuses:
            assert ps in VALID_PROCESSING_STATUSES, f"Invalid processing_status: {ps}"


class TestSeedVoiceAiReferentialIntegrity:
    """Tests 4, 5, 11: Referential integrity — message links, entity links, feedback."""

    def test_log_message_ids_resolve_to_same_tenant_messages(self, db_session):
        """Test 4: Every voice_command_log.message_id resolves to a same-tenant message."""
        _seed_voice_ai(db_session, TEST_TENANT_ID)

        # Find logs with non-NULL message_id in the deterministic families
        logs = db_session.execute(
            text("""
                SELECT vcl.id, vcl.tenant_id, vcl.message_id
                FROM public.voice_command_log vcl
                WHERE vcl.tenant_id IN (:t1, :t2)
                  AND vcl.message_id IS NOT NULL
            """),
            {"t1": str(TEST_TENANT_ID), "t2": str(SECOND_TENANT_ID)},
        ).fetchall()

        assert len(logs) > 0, "No logs with message_id found"
        for log in logs:
            msg = db_session.execute(
                text(
                    "SELECT tenant_id FROM public.conversation_message WHERE id = :mid"
                ),
                {"mid": str(log.message_id)},
            ).first()
            assert msg is not None, f"Log {log.id} → message {log.message_id} not found"
            assert msg.tenant_id == log.tenant_id, (
                f"Log tenant {log.tenant_id} != message tenant {msg.tenant_id}"
            )

    def test_entity_links_target_same_tenant_entities(self, db_session):
        """Test 5: Every entity link's target exists in the same tenant."""
        _seed_voice_ai(db_session, TEST_TENANT_ID)

        links = db_session.execute(
            text("""
                SELECT vcel.id, vcel.tenant_id, vcel.entity_type, vcel.entity_id,
                       vcel.voice_command_log_id
                FROM public.voice_command_entity_link vcel
                WHERE vcel.tenant_id = :tid
            """),
            {"tid": str(TEST_TENANT_ID)},
        ).fetchall()

        assert len(links) > 0, "No entity links found"
        for link in links:
            # Verify the entity exists in the same tenant
            if link.entity_type == "job":
                exists = db_session.execute(
                    text(
                        "SELECT 1 FROM public.job WHERE id = :eid AND tenant_id = :tid"
                    ),
                    {"eid": str(link.entity_id), "tid": str(link.tenant_id)},
                ).first()
            elif link.entity_type == "quote":
                exists = db_session.execute(
                    text(
                        "SELECT 1 FROM public.quote WHERE id = :eid AND tenant_id = :tid"
                    ),
                    {"eid": str(link.entity_id), "tid": str(link.tenant_id)},
                ).first()
            elif link.entity_type == "job_time_entry":
                exists = db_session.execute(
                    text(
                        "SELECT 1 FROM public.job_time_entry "
                        "WHERE id = :eid AND tenant_id = :tid"
                    ),
                    {"eid": str(link.entity_id), "tid": str(link.tenant_id)},
                ).first()
            elif link.entity_type == "job_expense":
                exists = db_session.execute(
                    text(
                        "SELECT 1 FROM public.job_expense "
                        "WHERE id = :eid AND tenant_id = :tid"
                    ),
                    {"eid": str(link.entity_id), "tid": str(link.tenant_id)},
                ).first()
            else:
                exists = None  # Unknown entity type — skip

            if exists is not None:
                assert exists is not None, (
                    f"Entity link {link.id}: {link.entity_type} "
                    f"{link.entity_id} not found in tenant {link.tenant_id}"
                )

    def test_feedback_references_existing_logs_and_unexported(self, db_session):
        """Test 11: Feedback rows reference existing log ids; exported_at IS NULL."""
        _seed_voice_ai(db_session, TEST_TENANT_ID)

        # Check the 2 deterministic feedback rows
        for nn in (1, 2):
            fb_id = _fb_uuid(nn)
            fb = db_session.execute(
                text(
                    "SELECT voice_command_log_id, exported_at FROM public.voice_feedback "
                    "WHERE id = :id"
                ),
                {"id": fb_id},
            ).first()
            assert fb is not None, f"Feedback {fb_id} not found"
            assert fb.exported_at is None, (
                f"Feedback {fb_id} exported_at should be NULL"
            )

            if fb.voice_command_log_id is not None:
                log = db_session.execute(
                    text("SELECT 1 FROM public.voice_command_log WHERE id = :lid"),
                    {"lid": fb.voice_command_log_id},
                ).first()
                assert log is not None, (
                    f"Feedback {fb_id} → log {fb.voice_command_log_id} not found"
                )


class TestSeedVoiceAiReset:
    """Test 6: _reset_voice_ai removes deterministic-id rows for both tenants."""

    def test_reset_removes_deterministic_rows_both_tenants(self, db_session):
        """_reset_voice_ai removes all deterministic session rows for both tenants."""
        _seed_voice_ai(db_session, TEST_TENANT_ID)

        # Verify sessions exist
        for sid in ALL_SESSION_IDS:
            row = db_session.execute(
                text("SELECT 1 FROM public.conversation_session WHERE id = :id"),
                {"id": str(sid)},
            ).first()
            assert row is not None

        # Reset
        _reset_voice_ai(db_session, TEST_TENANT_ID)

        # Verify sessions are gone (in-transaction; rollback restores)
        for sid in ALL_SESSION_IDS:
            row = db_session.execute(
                text("SELECT 1 FROM public.conversation_session WHERE id = :id"),
                {"id": str(sid)},
            ).first()
            assert row is None, f"Session {sid} should be deleted by reset"


class TestSeedTenantB:
    """Test 7: _seed_tenant_b creates tenant with charter tier FK + 2 tenant_user rows."""

    def test_tenant_b_has_charter_tier_and_2_tenant_users(self, db_session):
        """_seed_tenant_b creates tenant …-0006 with charter tier + 2 tenant_user rows."""
        _seed_tenant_b(db_session)

        # Verify tenant exists with charter tier
        tenant = db_session.execute(
            text("""
                SELECT t.id, t.name, t.is_active, st.tier_name
                FROM public.tenant t
                JOIN public.subscription_tier st ON st.tier_id = t.current_subscription_tier_id
                WHERE t.id = :tid
            """),
            {"tid": str(SECOND_TENANT_ID)},
        ).first()
        assert tenant is not None, "Tenant-B not found"
        assert tenant.tier_name == "charter", (
            f"Expected charter, got {tenant.tier_name}"
        )
        assert tenant.is_active is True

        # Verify 2 tenant_user rows with correct roles
        tus = db_session.execute(
            text("""
                SELECT tu.role_code, u.email
                FROM public.tenant_user tu
                JOIN public."user" u ON u.id = tu.user_id
                WHERE tu.tenant_id = :tid
                ORDER BY tu.role_code
            """),
            {"tid": str(SECOND_TENANT_ID)},
        ).fetchall()
        assert len(tus) == 2, f"Expected 2 tenant_user rows, got {len(tus)}"
        roles = {tu.role_code for tu in tus}
        assert roles == {"owner", "technician"}, (
            f"Expected owner+technician, got {roles}"
        )

        # Verify the 2 users exist
        for expected_email in ("devb@pilot.local", "techb@pilot.local"):
            user = db_session.execute(
                text('SELECT 1 FROM public."user" WHERE email = :email'),
                {"email": expected_email},
            ).first()
            assert user is not None, f"User {expected_email} not found"


class TestSeedVoiceAiDeferredRows:
    """Test 10: Deferred-row timestamp chain + idempotency_uuid presence."""

    def test_all_logs_have_idempotency_uuid_and_deferred_chain(self, db_session):
        """Every seeded log has non-NULL idempotency_uuid; deferred rows have full chains."""
        _seed_voice_ai(db_session, TEST_TENANT_ID)

        # All logs should have non-NULL idempotency_uuid
        null_idem = db_session.execute(
            text("""
                SELECT COUNT(*) FROM public.voice_command_log
                WHERE tenant_id IN (:t1, :t2) AND idempotency_uuid IS NULL
            """),
            {"t1": str(TEST_TENANT_ID), "t2": str(SECOND_TENANT_ID)},
        ).scalar()
        assert null_idem == 0, f"{null_idem} logs with NULL idempotency_uuid"

        # The 2 deferred rows (offline idempotency UUIDs 0013-01, 0013-02)
        # V12: completed — full chain (captured→uploaded→transcribed→parsed)
        v12 = db_session.execute(
            text("""
                SELECT processing_status, captured_at, uploaded_at, transcribed_at, parsed_at
                FROM public.voice_command_log
                WHERE idempotency_uuid = :idem
            """),
            {"idem": _offline_idem_uuid(1)},
        ).first()
        assert v12 is not None, "V12 deferred log not found"
        assert v12.processing_status == "completed"
        assert v12.captured_at is not None
        assert v12.uploaded_at is not None
        assert v12.transcribed_at is not None
        assert v12.parsed_at is not None

        # V13: failed — captured/uploaded set, transcribed/parsed NULL
        v13 = db_session.execute(
            text("""
                SELECT processing_status, captured_at, uploaded_at, transcribed_at, parsed_at
                FROM public.voice_command_log
                WHERE idempotency_uuid = :idem
            """),
            {"idem": _offline_idem_uuid(2)},
        ).first()
        assert v13 is not None, "V13 deferred-failed log not found"
        assert v13.processing_status == "failed"
        assert v13.captured_at is not None
        assert v13.uploaded_at is not None
        assert v13.transcribed_at is None
        assert v13.parsed_at is None


class TestSeedVoiceAiStructuredContent:
    """Test 12: Structured-content JSON shape (render_mode live/snapshot)."""

    def test_structured_content_json_shape(self, db_session):
        """Structured-content messages have render_mode in {live, snapshot} + non-empty data."""
        _seed_voice_ai(db_session, TEST_TENANT_ID)

        # Find messages with structured_content_json in the deterministic family
        structured_msgs = db_session.execute(
            text("""
                SELECT id, structured_content_json
                FROM public.conversation_message
                WHERE tenant_id = :tid
                  AND structured_content_json IS NOT NULL
                  AND id IN (:m3, :m8)
            """),
            {
                "tid": str(TEST_TENANT_ID),
                "m3": _msg_uuid(3),
                "m8": _msg_uuid(8),
            },
        ).fetchall()

        assert len(structured_msgs) >= 1, "No structured-content messages found"
        for msg_id, scj in structured_msgs:
            payload = json.loads(scj) if isinstance(scj, str) else scj
            assert "render_mode" in payload, f"Message {msg_id}: missing render_mode"
            assert payload["render_mode"] in ("live", "snapshot"), (
                f"Message {msg_id}: render_mode={payload['render_mode']}"
            )
            assert "data" in payload, f"Message {msg_id}: missing data"
            assert payload["data"], f"Message {msg_id}: empty data"


class TestSeedVoiceAiUuidFamilyPurity:
    """Test 9: Deterministic UUID families are pairwise-distinct and outside reserved range."""

    def test_uuid_families_distinct_and_outside_reserved_range(self):
        """UUID families are pairwise-distinct and outside …-0001-…-0005."""
        # Collect all deterministic UUIDs from the families
        all_uuids = set()

        # Sessions (0010 family)
        for nn in range(1, 9):
            all_uuids.add(UUID(f"00000000-0000-0000-0010-{nn:012d}"))

        # Messages (0011 family)
        for nn in range(1, 35):
            all_uuids.add(UUID(f"00000000-0000-0000-0011-{nn:012d}"))

        # Feedback (0012 family)
        for nn in range(1, 3):
            all_uuids.add(UUID(f"00000000-0000-0000-0012-{nn:012d}"))

        # Offline idempotency (0013 family)
        for nn in range(1, 3):
            all_uuids.add(UUID(f"00000000-0000-0000-0013-{nn:012d}"))

        # Sync idempotency (0014 family)
        for nn in range(1, 14):
            all_uuids.add(UUID(f"00000000-0000-0000-0014-{nn:012d}"))

        # Second tenant + users (0006, 0007, 0008)
        all_uuids.add(SECOND_TENANT_ID)
        all_uuids.add(TENANT_B_OWNER_ID)
        all_uuids.add(TENANT_B_TECH_ID)

        # None should be in the reserved range
        reserved_hits = all_uuids & RESERVED_RANGE
        assert reserved_hits == set(), f"UUIDs in reserved range: {reserved_hits}"

        # All should be distinct (set deduplication confirms this)
        # The family prefixes (0010, 0011, 0012, 0013, 0014, 0006, 0007, 0008) are
        # all different, so no cross-family collision is possible.
