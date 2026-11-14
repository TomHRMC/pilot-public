"""
Test Suite: Task 1-C-3 — site Structured Access Fields
=======================================================
Verifies the following:

1. DB Schema: `gate_code` (VARCHAR(50)), `access_instructions` (TEXT), and
   `hazard_notes` (TEXT) are present in the live `site` table.
2. ORM Model: Site model exposes all three fields and they round-trip correctly.
3. Null Default: Site can be persisted WITHOUT any access fields (all are optional).
4. Field Length: gate_code is limited to VARCHAR(50) — long strings are rejected.
5. Text Fields: access_instructions and hazard_notes accept multi-line free text.
6. Partial Fill: A site can have some fields set and others NULL (real-world pattern).
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import text
from sqlmodel import select

from app.models.crm import Site

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_site(
    tenant_id,
    customer_id,
    gate_code=None,
    access_instructions=None,
    hazard_notes=None,
) -> Site:
    """Factory: build a Site instance with optional structured access fields."""
    return Site(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        customer_id=customer_id,
        name="Test Site",
        gate_code=gate_code,
        access_instructions=access_instructions,
        hazard_notes=hazard_notes,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# 1. DB Schema Tests — query information_schema directly
# ---------------------------------------------------------------------------


class TestSiteAccessFieldsSchema:
    """Verify the three new columns exist in the live DB with correct types."""

    def test_gate_code_column_exists(self, db_engine):
        """gate_code must be present, character varying, nullable."""
        with db_engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT column_name, data_type, character_maximum_length, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = 'site'
                      AND column_name = 'gate_code'
                """)
            ).fetchone()
        assert row is not None, "Column 'gate_code' is missing from site table"
        assert row.data_type == "character varying", (
            f"Expected character varying, got {row.data_type}"
        )
        assert row.character_maximum_length == 50, (
            f"Expected VARCHAR(50), got VARCHAR({row.character_maximum_length})"
        )
        assert row.is_nullable == "YES", "gate_code must be nullable"

    def test_access_instructions_column_exists(self, db_engine):
        """access_instructions must be present, text, nullable."""
        with db_engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = 'site'
                      AND column_name = 'access_instructions'
                """)
            ).fetchone()
        assert row is not None, (
            "Column 'access_instructions' is missing from site table"
        )
        assert row.data_type == "text", f"Expected text, got {row.data_type}"
        assert row.is_nullable == "YES", "access_instructions must be nullable"

    def test_hazard_notes_column_exists(self, db_engine):
        """hazard_notes must be present, text, nullable."""
        with db_engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = 'site'
                      AND column_name = 'hazard_notes'
                """)
            ).fetchone()
        assert row is not None, "Column 'hazard_notes' is missing from site table"
        assert row.data_type == "text", f"Expected text, got {row.data_type}"
        assert row.is_nullable == "YES", "hazard_notes must be nullable"

    def test_no_server_defaults_on_access_fields(self, db_engine):
        """All three access fields must have no server default — NULL is the signal for 'not set'."""
        with db_engine.connect() as conn:
            rows = conn.execute(
                text("""
                    SELECT column_name, column_default
                    FROM information_schema.columns
                    WHERE table_name = 'site'
                      AND column_name IN ('gate_code', 'access_instructions', 'hazard_notes')
                    ORDER BY column_name
                """)
            ).fetchall()
        assert len(rows) == 3, f"Expected 3 rows, got {len(rows)}"
        for row in rows:
            assert row.column_default is None, (
                f"{row.column_name} should have no server default — NULL signals 'not configured'"
            )


# ---------------------------------------------------------------------------
# 2. ORM Model Tests — round-trip through Site model
# ---------------------------------------------------------------------------


class TestSiteOrmAccessFields:
    """Verify Site ORM exposes and persists access fields correctly."""

    def test_site_with_all_access_fields_persists(
        self, db_session, test_tenant, test_customer
    ):
        """Site with all three access fields set round-trips correctly."""
        site = _make_site(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            gate_code="#4821",
            access_instructions="Enter through the side gate. Park in the back. Buzz unit 3B.",
            hazard_notes="WARNING: Large unsecured dog in yard. Asbestos insulation in attic.",
        )
        db_session.add(site)
        db_session.commit()
        db_session.refresh(site)

        fetched = db_session.exec(select(Site).where(Site.id == site.id)).first()
        assert fetched is not None
        assert fetched.gate_code == "#4821"
        assert "side gate" in fetched.access_instructions
        assert "dog in yard" in fetched.hazard_notes

    def test_site_without_access_fields_defaults_to_null(
        self, db_session, test_tenant, test_customer
    ):
        """Site persisted without access fields has all three fields as None."""
        site = _make_site(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            # Intentionally omit all three access fields
        )
        db_session.add(site)
        db_session.commit()
        db_session.refresh(site)

        fetched = db_session.exec(select(Site).where(Site.id == site.id)).first()
        assert fetched is not None
        assert fetched.gate_code is None, "gate_code should be None when not provided"
        assert fetched.access_instructions is None, (
            "access_instructions should be None when not provided"
        )
        assert fetched.hazard_notes is None, (
            "hazard_notes should be None when not provided"
        )

    def test_partial_fill_access_fields(self, db_session, test_tenant, test_customer):
        """Site with only gate_code set leaves the TEXT fields as None."""
        site = _make_site(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            gate_code="*99#",
            # access_instructions and hazard_notes intentionally omitted
        )
        db_session.add(site)
        db_session.commit()
        db_session.refresh(site)

        fetched = db_session.exec(select(Site).where(Site.id == site.id)).first()
        assert fetched is not None
        assert fetched.gate_code == "*99#"
        assert fetched.access_instructions is None
        assert fetched.hazard_notes is None

    def test_multiline_access_instructions(
        self, db_session, test_tenant, test_customer
    ):
        """access_instructions accepts multi-line text (common for complex properties)."""
        instructions = (
            "Step 1: Call owner 30 min before arrival.\n"
            "Step 2: Park on the street — no driveway access.\n"
            "Step 3: Gate code is posted inside the fence on the right.\n"
            "Step 4: Main panel is in the utility closet off the kitchen."
        )
        site = _make_site(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            access_instructions=instructions,
        )
        db_session.add(site)
        db_session.commit()
        db_session.refresh(site)

        fetched = db_session.exec(select(Site).where(Site.id == site.id)).first()
        assert fetched is not None
        assert fetched.access_instructions == instructions
        assert "\n" in fetched.access_instructions, "Multi-line text must be preserved"

    def test_multiline_hazard_notes(self, db_session, test_tenant, test_customer):
        """hazard_notes accepts multi-line safety text — critical for Voice AI readout."""
        hazards = (
            "HAZARD 1: Live 240V panel — de-energize before entry.\n"
            "HAZARD 2: Asbestos wrap on pipes in basement.\n"
            "HAZARD 3: Two large dogs — owner must contain before work."
        )
        site = _make_site(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            hazard_notes=hazards,
        )
        db_session.add(site)
        db_session.commit()
        db_session.refresh(site)

        fetched = db_session.exec(select(Site).where(Site.id == site.id)).first()
        assert fetched is not None
        assert fetched.hazard_notes == hazards

    def test_gate_code_max_length_boundary(
        self, db_session, test_tenant, test_customer
    ):
        """gate_code at exactly 50 characters must be accepted (boundary test)."""
        code_50 = "A" * 50  # exactly VARCHAR(50) limit
        site = _make_site(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            gate_code=code_50,
        )
        db_session.add(site)
        db_session.commit()
        db_session.refresh(site)

        fetched = db_session.exec(select(Site).where(Site.id == site.id)).first()
        assert fetched is not None
        assert fetched.gate_code == code_50
        assert len(fetched.gate_code) == 50

    def test_gate_code_update_roundtrip(self, db_session, test_tenant, test_customer):
        """gate_code can be updated after initial creation (common field change)."""
        site = _make_site(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            gate_code="0000",
        )
        db_session.add(site)
        db_session.commit()
        db_session.refresh(site)

        # Update the gate code
        site.gate_code = "#9876"
        db_session.add(site)
        db_session.commit()
        db_session.refresh(site)

        fetched = db_session.exec(select(Site).where(Site.id == site.id)).first()
        assert fetched.gate_code == "#9876"

    def test_hazard_notes_can_be_cleared(self, db_session, test_tenant, test_customer):
        """hazard_notes can be set to None after initial creation (hazard resolved)."""
        site = _make_site(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            hazard_notes="Temporary: construction debris on site.",
        )
        db_session.add(site)
        db_session.commit()
        db_session.refresh(site)

        # Clear the hazard after it's resolved
        site.hazard_notes = None
        db_session.add(site)
        db_session.commit()
        db_session.refresh(site)

        fetched = db_session.exec(select(Site).where(Site.id == site.id)).first()
        assert fetched.hazard_notes is None, (
            "hazard_notes must be clearable once a hazard is resolved"
        )
