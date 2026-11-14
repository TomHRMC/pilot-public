"""
tests/batch_b20/test_a94_customer_comm_template_type.py

B20/A94 — customer_comm_template_type catalog table + FK swap (FIND-083)

Coverage (per design doc §F):
  TestCatalogSchema          — table existence, column structure, seed counts
  TestSeedData               — specific MVP + Phase 2 codes present
  TestFKEnforcement          — valid/invalid template_code on customer_communication
  TestCheckConstraintRemoval — old CHECK constraints no longer exist
  TestSoftDisable            — is_active=false: no cascade delete, excluded from API
  TestAuditTriggers          — audit.log rows on INSERT and UPDATE
  TestListEndpoint           — GET /api/v1/communications/comm-template-types
  TestCommunicationTemplateFk — FK enforcement on communication_template table
"""

import uuid
from datetime import UTC, datetime

import pytest
from fastapi import status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.communications import (
    CommunicationTemplate,
    CustomerCommTemplateType,
    CustomerCommunication,
)
from app.models.crm import Customer

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_customer(db, tenant_id) -> Customer:
    c = Customer(
        tenant_id=tenant_id,
        display_name="Test Customer A94",
        first_name="Test",
        last_name="A94",
        mobile_phone="+15125550099",
        email="a94test@example.com",
        preferred_contact_channel="sms",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _make_comm(
    db, tenant_id, customer_id, user_id, template_code: str
) -> CustomerCommunication:
    comm = CustomerCommunication(
        tenant_id=tenant_id,
        customer_id=customer_id,
        sender_user_id=user_id,
        template_code=template_code,
        rendered_message="Test message",
        channel="sms",
        actual_channel="sms",
        status="pending",
        created_by=user_id,
        updated_by=user_id,
    )
    db.add(comm)
    db.commit()
    db.refresh(comm)
    return comm


def _make_comm_template(
    db,
    tenant_id,
    user_id,
    template_code: str,
    channel: str = "sms",
    subject: str | None = None,
) -> CommunicationTemplate:
    ct = CommunicationTemplate(
        tenant_id=tenant_id,
        template_code=template_code,
        channel=channel,
        subject=subject,
        body_template="Hello {{customer_first_name}}",
        is_active=True,
        created_by=user_id,
        updated_by=user_id,
    )
    db.add(ct)
    db.commit()
    db.refresh(ct)
    return ct


# ---------------------------------------------------------------------------
# TestCatalogSchema — table structure and seed counts
# ---------------------------------------------------------------------------


class TestCatalogSchema:
    def test_catalog_table_exists(self, db_session: Session):
        """customer_comm_template_type table is present in DB."""
        result = db_session.exec(
            text(
                "SELECT EXISTS(SELECT 1 FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name='customer_comm_template_type')"
            )
        ).scalar()
        assert result is True

    def test_catalog_has_code_primary_key(self, db_session: Session):
        """code column is varchar primary key."""
        row = db_session.exec(
            text(
                "SELECT data_type FROM information_schema.columns "
                "WHERE table_name='customer_comm_template_type' AND column_name='code'"
            )
        ).first()
        assert row is not None
        assert "char" in row[0]  # character varying

    def test_catalog_has_slug_unique(self, db_session: Session):
        """slug column has a unique constraint."""
        result = db_session.exec(
            text(
                "SELECT COUNT(*) FROM information_schema.table_constraints tc "
                "JOIN information_schema.constraint_column_usage ccu USING (constraint_name, table_name) "
                "WHERE tc.table_name='customer_comm_template_type' "
                "AND tc.constraint_type='UNIQUE' AND ccu.column_name='slug'"
            )
        ).scalar()
        assert result >= 1

    def test_mvp_active_rows_count(self, db_session: Session):
        """14 rows with is_active=true are seeded (13 MVP + recurring_job_scheduled added later)."""
        count = db_session.exec(
            select(CustomerCommTemplateType).where(
                CustomerCommTemplateType.is_active == True
            )
        ).all()
        assert len(count) == 14

    def test_phase2_inactive_rows_count(self, db_session: Session):
        """Exactly 14 rows with is_active=false are seeded."""
        count = db_session.exec(
            select(CustomerCommTemplateType).where(
                CustomerCommTemplateType.is_active == False
            )
        ).all()
        assert len(count) == 14

    def test_total_seed_count(self, db_session: Session):
        """Total row count in catalog is 28 (27 original + recurring_job_scheduled)."""
        all_rows = db_session.exec(select(CustomerCommTemplateType)).all()
        assert len(all_rows) == 28


# ---------------------------------------------------------------------------
# TestSeedData — specific codes present and correct
# ---------------------------------------------------------------------------


class TestSeedData:
    LEGACY_CODES = [
        "on_my_way",
        "running_late",
        "arrived",
        "job_complete",
        "parts_delay",
        "confirm_appointment",
    ]
    NEW_MVP_CODES = [
        "tech_assigned",
        "invoice_sent",
        "payment_reminder",
        "payment_received",
        "change_order_approval",
        "quote_accepted",
        "quote_expiring",
    ]
    PHASE2_CODES = [
        "appointment_reminder_24h",
        "appointment_reminder_1h",
        "quote_follow_up",
        "quote_revised",
        "payment_overdue",
        "receipt",
        "warranty_info",
        "review_request",
        "referral_request",
        "annual_safety_check",
        "service_anniversary",
        "customer_cancellation_confirmed",
        "tech_cancellation",
        "no_show",
    ]

    def test_existing_6_codes_present(self, db_session: Session):
        """All 6 legacy codes exist in catalog and are active."""
        for code in self.LEGACY_CODES:
            row = db_session.exec(
                select(CustomerCommTemplateType).where(
                    CustomerCommTemplateType.code == code
                )
            ).first()
            assert row is not None, f"Legacy code '{code}' missing from catalog"
            assert row.is_active is True, (
                f"Legacy code '{code}' should be is_active=true"
            )

    def test_new_7_mvp_codes_present_and_active(self, db_session: Session):
        """All 7 new MVP codes exist and are is_active=true."""
        for code in self.NEW_MVP_CODES:
            row = db_session.exec(
                select(CustomerCommTemplateType).where(
                    CustomerCommTemplateType.code == code
                )
            ).first()
            assert row is not None, f"New MVP code '{code}' missing from catalog"
            assert row.is_active is True, (
                f"New MVP code '{code}' should be is_active=true"
            )

    def test_phase2_codes_exist_and_inactive(self, db_session: Session):
        """All 14 Phase 2 codes exist and are is_active=false."""
        for code in self.PHASE2_CODES:
            row = db_session.exec(
                select(CustomerCommTemplateType).where(
                    CustomerCommTemplateType.code == code
                )
            ).first()
            assert row is not None, f"Phase 2 code '{code}' missing from catalog"
            assert row.is_active is False, (
                f"Phase 2 code '{code}' should be is_active=false"
            )

    def test_sort_order_ascending_for_active_rows(self, db_session: Session):
        """Active rows have ascending sort_order matching design doc."""
        rows = db_session.exec(
            select(CustomerCommTemplateType)
            .where(CustomerCommTemplateType.is_active == True)
            .order_by(CustomerCommTemplateType.sort_order)
        ).all()
        sort_orders = [r.sort_order for r in rows]
        assert sort_orders == sorted(sort_orders)
        assert rows[0].code == "on_my_way"  # sort_order=10 is first

    def test_change_order_approval_requires_approval(self, db_session: Session):
        """change_order_approval has requires_approval=true."""
        row = db_session.exec(
            select(CustomerCommTemplateType).where(
                CustomerCommTemplateType.code == "change_order_approval"
            )
        ).first()
        assert row is not None
        assert row.requires_approval is True

    def test_initiator_values_correct(self, db_session: Session):
        """Sample initiator values match design doc."""
        checks = {
            "on_my_way": "tech",
            "invoice_sent": "system",
            "change_order_approval": "owner",
        }
        for code, expected_initiator in checks.items():
            row = db_session.exec(
                select(CustomerCommTemplateType).where(
                    CustomerCommTemplateType.code == code
                )
            ).first()
            assert row.initiator == expected_initiator, (
                f"{code}: expected initiator={expected_initiator}"
            )


# ---------------------------------------------------------------------------
# TestFKEnforcement — customer_communication.template_code FK
# ---------------------------------------------------------------------------


class TestFKEnforcement:
    def test_fk_enforcement_valid_code(
        self, db_session: Session, test_tenant, test_user
    ):
        """INSERT customer_communication with valid template_code succeeds."""
        customer = _make_customer(db_session, test_tenant.id)
        comm = _make_comm(
            db_session, test_tenant.id, customer.id, test_user.id, "on_my_way"
        )
        assert comm.id is not None
        assert comm.template_code == "on_my_way"

    def test_fk_enforcement_invalid_code(
        self, db_session: Session, test_tenant, test_user
    ):
        """INSERT customer_communication with invalid template_code raises IntegrityError."""
        customer = _make_customer(db_session, test_tenant.id)
        with pytest.raises(IntegrityError):
            comm = CustomerCommunication(
                tenant_id=test_tenant.id,
                customer_id=customer.id,
                sender_user_id=test_user.id,
                template_code="invalid_code_xyz_does_not_exist",
                rendered_message="Bad code",
                channel="sms",
                actual_channel="sms",
                status="pending",
                created_by=test_user.id,
                updated_by=test_user.id,
            )
            db_session.add(comm)
            db_session.commit()
        db_session.rollback()

    def test_phase2_codes_fk_valid(self, db_session: Session, test_tenant, test_user):
        """Phase 2 inactive codes are FK-valid (catalog row exists, is_active not enforced at DB)."""
        customer = _make_customer(db_session, test_tenant.id)
        comm = _make_comm(
            db_session,
            test_tenant.id,
            customer.id,
            test_user.id,
            "appointment_reminder_24h",
        )
        assert comm.id is not None
        assert comm.template_code == "appointment_reminder_24h"


# ---------------------------------------------------------------------------
# TestCheckConstraintRemoval — old CHECK constraints no longer exist
# ---------------------------------------------------------------------------


class TestCheckConstraintRemoval:
    def test_check_constraint_removed_from_customer_communication(
        self, db_session: Session
    ):
        """customer_communication_template_code_chk CHECK does NOT exist."""
        result = db_session.exec(
            text(
                "SELECT COUNT(*) FROM information_schema.table_constraints "
                "WHERE table_name='customer_communication' "
                "AND constraint_name='customer_communication_template_code_chk' "
                "AND constraint_type='CHECK'"
            )
        ).scalar()
        assert result == 0, (
            "Old CHECK constraint customer_communication_template_code_chk still present"
        )

    def test_check_constraint_removed_from_communication_template(
        self, db_session: Session
    ):
        """communication_template_code_chk CHECK does NOT exist."""
        result = db_session.exec(
            text(
                "SELECT COUNT(*) FROM information_schema.table_constraints "
                "WHERE table_name='communication_template' "
                "AND constraint_name='communication_template_code_chk' "
                "AND constraint_type='CHECK'"
            )
        ).scalar()
        assert result == 0, (
            "Old CHECK constraint communication_template_code_chk still present"
        )

    def test_fk_constraint_exists_on_customer_communication(self, db_session: Session):
        """fk_comm_template_type FK exists on customer_communication."""
        result = db_session.exec(
            text(
                "SELECT COUNT(*) FROM information_schema.table_constraints "
                "WHERE table_name='customer_communication' "
                "AND constraint_name='fk_comm_template_type' "
                "AND constraint_type='FOREIGN KEY'"
            )
        ).scalar()
        assert result == 1, (
            "FK fk_comm_template_type not found on customer_communication"
        )

    def test_fk_constraint_exists_on_communication_template(self, db_session: Session):
        """fk_communication_template_type FK exists on communication_template."""
        result = db_session.exec(
            text(
                "SELECT COUNT(*) FROM information_schema.table_constraints "
                "WHERE table_name='communication_template' "
                "AND constraint_name='fk_communication_template_type' "
                "AND constraint_type='FOREIGN KEY'"
            )
        ).scalar()
        assert result == 1, (
            "FK fk_communication_template_type not found on communication_template"
        )


# ---------------------------------------------------------------------------
# TestSoftDisable — is_active=false semantics
# ---------------------------------------------------------------------------


class TestSoftDisable:
    def test_soft_disable_does_not_cascade(
        self, db_session: Session, test_tenant, test_user
    ):
        """Set is_active=false on a catalog row — existing comm rows still FK-valid."""
        customer = _make_customer(db_session, test_tenant.id)
        comm = _make_comm(
            db_session, test_tenant.id, customer.id, test_user.id, "on_my_way"
        )
        assert comm.id is not None

        # Soft-disable the catalog row
        row = db_session.exec(
            select(CustomerCommTemplateType).where(
                CustomerCommTemplateType.code == "on_my_way"
            )
        ).first()
        row.is_active = False
        db_session.commit()

        # Existing comm row is still there — no cascade delete
        existing = db_session.exec(
            select(CustomerCommunication).where(CustomerCommunication.id == comm.id)
        ).first()
        assert existing is not None

        # Restore for other tests
        row.is_active = True
        db_session.commit()

    def test_soft_disable_excluded_from_api_list(self, client, db_session: Session):
        """After setting is_active=false on one code, GET /comm-template-types does not include it."""
        # First soft-disable
        row = db_session.exec(
            select(CustomerCommTemplateType).where(
                CustomerCommTemplateType.code == "arrived"
            )
        ).first()
        row.is_active = False
        db_session.commit()

        resp = client.get("/api/v1/communications/comm-template-types/test")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        codes = [item["code"] for item in data["items"]]
        assert "arrived" not in codes

        # Restore
        row.is_active = True
        db_session.commit()


# ---------------------------------------------------------------------------
# TestAuditTriggers — audit.log_changes() fires on INSERT and UPDATE
# ---------------------------------------------------------------------------


class TestAuditTriggers:
    def test_audit_trigger_fires_on_insert(self, db_session: Session):
        """INSERT new catalog row → audit.log row with action='INSERT'."""
        new_code = f"test_temp_{uuid.uuid4().hex[:6]}"
        row = CustomerCommTemplateType(
            code=new_code,
            slug=new_code,
            name="Temp Test Row",
            category="exception",
            initiator="system",
            send_mode="manual",
            is_active=False,
        )
        db_session.add(row)
        db_session.commit()

        audit_row = db_session.exec(
            text(
                "SELECT action FROM audit.event "
                "WHERE entity_name='customer_comm_template_type' "
                "AND action='INSERT' "
                "ORDER BY occurred_at DESC LIMIT 1"
            )
        ).first()
        assert audit_row is not None, "Audit INSERT row not found in audit.event"
        assert audit_row[0] == "INSERT"

        # Clean up
        db_session.delete(row)
        db_session.commit()

    def test_audit_trigger_fires_on_update(self, db_session: Session):
        """UPDATE sort_order on existing row → audit.log row with action='UPDATE'."""
        row = db_session.exec(
            select(CustomerCommTemplateType).where(
                CustomerCommTemplateType.code == "quote_expiring"
            )
        ).first()
        original_sort = row.sort_order
        row.sort_order = original_sort + 1
        db_session.commit()

        audit_row = db_session.exec(
            text(
                "SELECT action FROM audit.event "
                "WHERE entity_name='customer_comm_template_type' "
                "AND action='UPDATE' "
                "ORDER BY occurred_at DESC LIMIT 1"
            )
        ).first()
        assert audit_row is not None, "Audit UPDATE row not found in audit.event"
        assert audit_row[0] == "UPDATE"

        # Restore
        row.sort_order = original_sort
        db_session.commit()


# ---------------------------------------------------------------------------
# TestListEndpoint — GET /api/v1/communications/comm-template-types
# ---------------------------------------------------------------------------


class TestListEndpoint:
    def test_list_endpoint_returns_active_only(self, client):
        """GET /comm-template-types returns only is_active=true rows (14 after recurring_job_scheduled added)."""
        resp = client.get("/api/v1/communications/comm-template-types/test")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["total"] == 14
        assert len(data["items"]) == 14
        for item in data["items"]:
            # is_active not returned in response but all returned items are active
            assert "code" in item
            assert "slug" in item
            assert "sort_order" in item

    def test_list_endpoint_ordered_by_sort_order(self, client):
        """Response items are in ascending sort_order order."""
        resp = client.get("/api/v1/communications/comm-template-types/test")
        assert resp.status_code == status.HTTP_200_OK
        items = resp.json()["items"]
        sort_orders = [item["sort_order"] for item in items]
        assert sort_orders == sorted(sort_orders)

    def test_list_endpoint_first_item_is_on_my_way(self, client):
        """First item (sort_order=10) is on_my_way."""
        resp = client.get("/api/v1/communications/comm-template-types/test")
        items = resp.json()["items"]
        assert items[0]["code"] == "on_my_way"
        assert items[0]["sort_order"] == 10

    def test_list_endpoint_filter_by_category(self, client):
        """GET /comm-template-types?category=post_job returns only post_job rows."""
        resp = client.get(
            "/api/v1/communications/comm-template-types/test?category=post_job"
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        for item in data["items"]:
            assert item["category"] == "post_job"
        # Active post_job rows: job_complete, invoice_sent, payment_reminder, payment_received = 4
        assert data["total"] == 4

    def test_list_endpoint_filter_by_initiator_system(self, client):
        """GET /comm-template-types?initiator=system returns only system-initiated active rows."""
        resp = client.get(
            "/api/v1/communications/comm-template-types/test?initiator=system"
        )
        assert resp.status_code == status.HTTP_200_OK
        for item in resp.json()["items"]:
            assert item["initiator"] == "system"

    def test_list_endpoint_filter_by_initiator_tech(self, client):
        """GET /comm-template-types?initiator=tech returns only tech-initiated active rows."""
        resp = client.get(
            "/api/v1/communications/comm-template-types/test?initiator=tech"
        )
        assert resp.status_code == status.HTTP_200_OK
        items = resp.json()["items"]
        for item in items:
            assert item["initiator"] == "tech"

    def test_list_endpoint_requires_auth(self, client):
        """GET /comm-template-types (authenticated) without JWT returns 401 or test context failure."""
        # The non-test endpoint requires auth — test using the authenticated endpoint path
        # which will 422 without proper JWT (no auth header = 422 in FastAPI Depends chain)
        resp = client.get("/api/v1/communications/comm-template-types")
        # FastAPI returns 422 when required Depends cannot be resolved without a token
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            status.HTTP_403_FORBIDDEN,
        )

    def test_list_endpoint_response_schema_fields(self, client):
        """Response items contain all required CommTemplateTypeResponse fields."""
        resp = client.get("/api/v1/communications/comm-template-types/test")
        assert resp.status_code == status.HTTP_200_OK
        item = resp.json()["items"][0]
        required_fields = [
            "code",
            "slug",
            "name",
            "category",
            "preferred_channel",
            "initiator",
            "requires_approval",
            "send_mode",
            "trigger_event",
            "is_system",
            "sort_order",
        ]
        for field in required_fields:
            assert field in item, f"Missing field '{field}' in CommTemplateTypeResponse"


# ---------------------------------------------------------------------------
# TestCommunicationTemplateFk — FK enforcement on communication_template table
# ---------------------------------------------------------------------------


class TestCommunicationTemplateFk:
    def test_communication_template_fk_valid_new_code(
        self, db_session: Session, test_tenant, test_user
    ):
        """INSERT communication_template with new MVP code 'tech_assigned' succeeds."""
        ct = _make_comm_template(
            db_session, test_tenant.id, test_user.id, "tech_assigned"
        )
        assert ct.id is not None
        assert ct.template_code == "tech_assigned"

    def test_communication_template_fk_valid_legacy_code(
        self, db_session: Session, test_tenant, test_user
    ):
        """INSERT communication_template with legacy code 'running_late' succeeds."""
        ct = _make_comm_template(
            db_session, test_tenant.id, test_user.id, "running_late"
        )
        assert ct.id is not None
        assert ct.template_code == "running_late"

    def test_communication_template_fk_invalid_code(
        self, db_session: Session, test_tenant, test_user
    ):
        """INSERT communication_template with bad code raises IntegrityError."""
        with pytest.raises(IntegrityError):
            ct = CommunicationTemplate(
                tenant_id=test_tenant.id,
                template_code="bad_code_xyz_does_not_exist",
                channel="sms",
                body_template="Hello {{name}}",
                is_active=True,
                created_by=test_user.id,
                updated_by=test_user.id,
            )
            db_session.add(ct)
            db_session.commit()
        db_session.rollback()

    def test_communication_template_fk_email_with_new_code(
        self, db_session: Session, test_tenant, test_user
    ):
        """INSERT communication_template with email channel + new MVP email code succeeds."""
        ct = _make_comm_template(
            db_session,
            test_tenant.id,
            test_user.id,
            "invoice_sent",
            channel="email",
            subject="Invoice Sent",  # required by communication_template_email_subject_chk
        )
        assert ct.id is not None
        assert ct.template_code == "invoice_sent"
        assert ct.channel == "email"
