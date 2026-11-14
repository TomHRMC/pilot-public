"""
FIND-141 (S2 High) — CustomerResponse: add 5 SMS fields + NotificationPreferenceResponse.

Part 1: CustomerResponse must include 5 TCPA SMS consent fields:
  sms_opted_out, sms_opt_out_at, sms_opt_in_consent, sms_opt_in_at, sms_opt_in_source

Part 2: NotificationPreferenceResponse and NotificationPreferenceClearResponse Pydantic
schemas must exist and be wired to the 4 PUT/DELETE notification preference endpoints.

Test plan from remediation plan FIND-141:
  - CustomerResponse schema has all 5 SMS fields (schema inspection)
  - CustomerResponse can be populated from a Customer ORM with SMS data
  - NotificationPreferenceResponse has category_id, channel, enabled, scope fields
  - NotificationPreferenceClearResponse has cleared, reverted_to_scope fields
  - PUT /notifications/preferences endpoint returns typed response (not plain dict)

Test subfolder: tests/batch_b17/
"""


# ---------------------------------------------------------------------------
# Part 1: CustomerResponse SMS fields
# ---------------------------------------------------------------------------


class TestCustomerResponseSmsFields:
    """
    FIND-141: CustomerResponse must expose 5 TCPA SMS consent fields.
    """

    def test_customer_response_has_sms_opted_out(self):
        from api.schemas.schemas import CustomerResponse

        fields = CustomerResponse.model_fields
        assert "sms_opted_out" in fields, (
            "CustomerResponse missing sms_opted_out field. "
            "FIND-141 requires all 5 SMS consent fields."
        )

    def test_customer_response_has_sms_opt_out_at(self):
        from api.schemas.schemas import CustomerResponse

        fields = CustomerResponse.model_fields
        assert "sms_opt_out_at" in fields, "CustomerResponse missing sms_opt_out_at"

    def test_customer_response_has_sms_opt_in_consent(self):
        from api.schemas.schemas import CustomerResponse

        fields = CustomerResponse.model_fields
        assert "sms_opt_in_consent" in fields, (
            "CustomerResponse missing sms_opt_in_consent"
        )

    def test_customer_response_has_sms_opt_in_at(self):
        from api.schemas.schemas import CustomerResponse

        fields = CustomerResponse.model_fields
        assert "sms_opt_in_at" in fields, "CustomerResponse missing sms_opt_in_at"

    def test_customer_response_has_sms_opt_in_source(self):
        from api.schemas.schemas import CustomerResponse

        fields = CustomerResponse.model_fields
        assert "sms_opt_in_source" in fields, (
            "CustomerResponse missing sms_opt_in_source"
        )

    def test_customer_response_sms_fields_have_correct_defaults(self):
        """SMS bool fields default to False; datetime/str fields default to None."""
        import uuid

        from api.schemas.schemas import CustomerResponse

        response = CustomerResponse(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            type="person",
            display_name="Test Customer",
            first_name=None,
            last_name=None,
            company_name=None,
            email=None,
            mobile_phone=None,
            is_active=True,
        )
        assert response.sms_opted_out is False
        assert response.sms_opt_out_at is None
        assert response.sms_opt_in_consent is False
        assert response.sms_opt_in_at is None
        assert response.sms_opt_in_source is None

    def test_customer_response_populates_from_orm(self, db_session):
        """CustomerResponse.model_validate populates SMS fields from ORM Customer."""
        import uuid
        from datetime import UTC, datetime

        from sqlmodel import select

        from api.schemas.schemas import CustomerResponse
        from app.models.core import Tenant
        from app.models.crm import Customer
        from app.models.subscription import SubscriptionTier

        tier = db_session.exec(
            select(SubscriptionTier).where(SubscriptionTier.is_trial == True)
        ).first()
        assert tier is not None

        tenant = Tenant(
            id=uuid.uuid4(),
            name=f"SMS-Test-{uuid.uuid4().hex[:6]}",
            is_active=True,
            current_subscription_tier_id=tier.tier_id,
        )
        db_session.add(tenant)
        db_session.flush()

        opt_in_at = datetime.now(UTC)
        customer = Customer(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            display_name="TCPA Test Customer",
            sms_opted_out=False,
            sms_opt_in_consent=True,
            sms_opt_in_at=opt_in_at,
            sms_opt_in_source="explicit_checkbox",
        )
        db_session.add(customer)
        db_session.flush()

        response = CustomerResponse.model_validate(customer)
        assert response.sms_opted_out is False
        assert response.sms_opt_in_consent is True
        assert response.sms_opt_in_source == "explicit_checkbox"
        assert response.sms_opt_in_at is not None


# ---------------------------------------------------------------------------
# Part 2: NotificationPreferenceResponse schema
# ---------------------------------------------------------------------------


class TestNotificationPreferenceResponseSchema:
    """
    FIND-141: NotificationPreferenceResponse must have correct fields.
    """

    def test_notification_preference_response_has_category_id(self):
        from api.schemas.schemas import NotificationPreferenceResponse

        assert "category_id" in NotificationPreferenceResponse.model_fields

    def test_notification_preference_response_has_channel(self):
        from api.schemas.schemas import NotificationPreferenceResponse

        assert "channel" in NotificationPreferenceResponse.model_fields

    def test_notification_preference_response_has_enabled(self):
        from api.schemas.schemas import NotificationPreferenceResponse

        assert "enabled" in NotificationPreferenceResponse.model_fields

    def test_notification_preference_response_has_scope(self):
        from api.schemas.schemas import NotificationPreferenceResponse

        assert "scope" in NotificationPreferenceResponse.model_fields

    def test_notification_preference_response_instantiates_correctly(self):
        from api.schemas.schemas import NotificationPreferenceResponse

        resp = NotificationPreferenceResponse(
            category_id="job_assignment",
            channel="push",
            enabled=True,
            scope="user",
        )
        assert resp.category_id == "job_assignment"
        assert resp.channel == "push"
        assert resp.enabled is True
        assert resp.scope == "user"

    def test_notification_preference_clear_response_has_cleared(self):
        from api.schemas.schemas import NotificationPreferenceClearResponse

        assert "cleared" in NotificationPreferenceClearResponse.model_fields

    def test_notification_preference_clear_response_has_reverted_to_scope(self):
        from api.schemas.schemas import NotificationPreferenceClearResponse

        assert "reverted_to_scope" in NotificationPreferenceClearResponse.model_fields

    def test_notification_preference_clear_response_instantiates(self):
        from api.schemas.schemas import NotificationPreferenceClearResponse

        resp = NotificationPreferenceClearResponse(
            cleared=True, reverted_to_scope="tenant"
        )
        assert resp.cleared is True
        assert resp.reverted_to_scope == "tenant"
