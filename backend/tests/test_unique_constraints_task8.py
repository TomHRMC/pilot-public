"""
Test unique constraints for Phase 3 Task 8.
"""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.models.auth import SsoProvider, UserSsoIdentity
from app.models.core import Tenant, User
from app.models.crm import Contact
from app.models.quoting import (
    PricebookItem,
    QuoteAcceptance,
    QuoteVersion,
)


class TestPricebookItemUnique:
    """Test UNIQUE(tenant_id, sku) constraint."""

    def test_duplicate_sku_same_tenant_rejected(
        self, db_session, test_tenant, test_user
    ):
        """Attempting to add same SKU twice to same tenant pricebook should raise IntegrityError."""
        # Create first pricebook item
        item1 = PricebookItem(
            tenant_id=test_tenant.id,
            sku="PANEL-200A",
            name="200A Main Panel",
            description="200A Main Panel",
            created_by=test_user.id,
        )
        db_session.add(item1)
        db_session.commit()

        # Attempt duplicate SKU in same tenant
        item2 = PricebookItem(
            tenant_id=test_tenant.id,
            sku="PANEL-200A",  # Same SKU
            name="Different Description",
            description="Different Description",
            created_by=test_user.id,
        )
        db_session.add(item2)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert "uq_pricebook_item_tenant_sku" in str(exc_info.value)

    def test_same_sku_different_tenants_allowed(
        self, db_session, test_tenant, test_user
    ):
        """Same SKU can exist in different tenant pricebooks."""
        # Create second tenant
        tenant2 = Tenant(name="Other Electrical Co", created_by=test_user.id)
        db_session.add(tenant2)
        db_session.commit()

        # Add same SKU to both tenants
        item1 = PricebookItem(
            tenant_id=test_tenant.id,
            sku="PANEL-200A",
            name="200A Main Panel",
            description="200A Main Panel",
            created_by=test_user.id,
        )
        item2 = PricebookItem(
            tenant_id=tenant2.id,
            sku="PANEL-200A",  # Same SKU, different tenant
            name="200A Main Panel",
            description="200A Main Panel",
            created_by=test_user.id,
        )
        db_session.add_all([item1, item2])
        db_session.commit()

        # Both should exist
        result = db_session.exec(
            select(PricebookItem).where(PricebookItem.sku == "PANEL-200A")
        ).all()
        assert len(result) == 2

    def test_different_skus_same_tenant_allowed(
        self, db_session, test_tenant, test_user
    ):
        """Different SKUs in same tenant pricebook are allowed."""
        item1 = PricebookItem(
            tenant_id=test_tenant.id,
            sku="PANEL-200A-UNIQUETEST",
            name="200A Main Panel",
            description="200A Main Panel",
            created_by=test_user.id,
        )
        item2 = PricebookItem(
            tenant_id=test_tenant.id,
            sku="PANEL-400A-UNIQUETEST",  # Different SKU — unique to this test
            name="400A Main Panel",
            description="400A Main Panel",
            created_by=test_user.id,
        )
        db_session.add_all([item1, item2])
        db_session.commit()

        # Filter by the test-specific SKUs to avoid counting pre-existing seeded items
        result = db_session.exec(
            select(PricebookItem).where(
                PricebookItem.sku.in_(
                    ["PANEL-200A-UNIQUETEST", "PANEL-400A-UNIQUETEST"]
                )
            )
        ).all()
        assert len(result) == 2


class TestUserSsoIdentityUnique:
    """Test UNIQUE(sso_provider_code, provider_user_id) constraint."""

    def test_duplicate_sso_identity_rejected(self, db_session, test_user):
        """Same external identity cannot be linked to multiple Pilot for Trades users."""
        # Ensure SSO provider exists — it may already be seeded by migration
        if not db_session.get(SsoProvider, "google"):
            db_session.add(
                SsoProvider(code="google", name="Google", created_by=test_user.id)
            )
            db_session.commit()

        # Create second user
        user2 = User(
            email="user2@test.com",
            full_name="User Two",
            password_hash="dummy_hash",
            created_by=test_user.id,
        )
        db_session.add(user2)
        db_session.commit()

        # Link Google account to first user
        identity1 = UserSsoIdentity(
            user_id=test_user.id,
            sso_provider_code="google",
            provider_user_id="google_123456",
            created_by=test_user.id,
        )
        db_session.add(identity1)
        db_session.commit()

        # Attempt to link same Google account to second user
        identity2 = UserSsoIdentity(
            user_id=user2.id,
            sso_provider_code="google",
            provider_user_id="google_123456",  # Same external identity
            created_by=test_user.id,
        )
        db_session.add(identity2)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert "uq_user_sso_identity_provider_user" in str(exc_info.value)

    def test_different_sso_providers_same_user_allowed(self, db_session, test_user):
        """User can link multiple SSO providers (Google + Microsoft)."""
        # Ensure providers exist — they may already be seeded by migration
        if not db_session.get(SsoProvider, "google"):
            db_session.add(
                SsoProvider(code="google", name="Google", created_by=test_user.id)
            )
        if not db_session.get(SsoProvider, "microsoft"):
            db_session.add(
                SsoProvider(code="microsoft", name="Microsoft", created_by=test_user.id)
            )
        db_session.commit()

        identity1 = UserSsoIdentity(
            user_id=test_user.id,
            sso_provider_code="google",
            provider_user_id="google_123456",
            created_by=test_user.id,
        )
        identity2 = UserSsoIdentity(
            user_id=test_user.id,
            sso_provider_code="microsoft",
            provider_user_id="microsoft_789012",
            created_by=test_user.id,
        )
        db_session.add_all([identity1, identity2])
        db_session.commit()

        result = db_session.exec(
            select(UserSsoIdentity).where(UserSsoIdentity.user_id == test_user.id)
        ).all()
        assert len(result) == 2

    def test_different_provider_users_same_provider_allowed(
        self, db_session, test_user
    ):
        """Different Google accounts can be in system (linked to different users)."""
        # Ensure SSO provider exists — it may already be seeded by migration
        if not db_session.get(SsoProvider, "google"):
            db_session.add(
                SsoProvider(code="google", name="Google", created_by=test_user.id)
            )
            db_session.commit()

        # Create second user
        user2 = User(
            email="user2@test.com",
            full_name="User Two",
            password_hash="dummy_hash",
            created_by=test_user.id,
        )
        db_session.add(user2)
        db_session.commit()

        identity1 = UserSsoIdentity(
            user_id=test_user.id,
            sso_provider_code="google",
            provider_user_id="google_123456",
            created_by=test_user.id,
        )
        identity2 = UserSsoIdentity(
            user_id=user2.id,
            sso_provider_code="google",
            provider_user_id="google_789012",  # Different Google account
            created_by=test_user.id,
        )
        db_session.add_all([identity1, identity2])
        db_session.commit()

        result = db_session.exec(
            select(UserSsoIdentity).where(UserSsoIdentity.sso_provider_code == "google")
        ).all()
        assert len(result) == 2


class TestQuoteAcceptanceUnique:
    """Test UNIQUE(quote_version_id, contact_id) constraint."""

    def test_duplicate_acceptance_rejected(
        self, db_session, test_contact, test_quote_version, test_user
    ):
        """Contact cannot accept same quote version twice."""
        # First acceptance
        acceptance1 = QuoteAcceptance(
            tenant_id=test_contact.tenant_id,
            quote_version_id=test_quote_version.id,
            contact_id=test_contact.id,
            accepted_by_name="John Doe",
            accepted_by_email="john@test.com",
            created_by=test_user.id,
        )
        db_session.add(acceptance1)
        db_session.commit()

        # Attempt duplicate acceptance
        acceptance2 = QuoteAcceptance(
            tenant_id=test_contact.tenant_id,
            quote_version_id=test_quote_version.id,
            contact_id=test_contact.id,  # Same contact, same version
            accepted_by_name="John Doe",
            accepted_by_email="john@test.com",
            created_by=test_user.id,
        )
        db_session.add(acceptance2)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert "uq_quote_acceptance_version_contact" in str(exc_info.value)

    def test_same_contact_different_versions_allowed(
        self, db_session, test_contact, test_quote_version, test_user
    ):
        """Contact can accept different versions of same quote."""
        # Create second version
        version2 = QuoteVersion(
            tenant_id=test_contact.tenant_id,
            quote_id=test_quote_version.quote_id,
            version_no=2,
            snapshot={},
            created_by=test_user.id,
        )
        db_session.add(version2)
        db_session.commit()

        # Accept both versions
        acceptance1 = QuoteAcceptance(
            tenant_id=test_contact.tenant_id,
            quote_version_id=test_quote_version.id,
            contact_id=test_contact.id,
            accepted_by_name="John Doe",
            accepted_by_email="john@test.com",
            created_by=test_user.id,
        )
        acceptance2 = QuoteAcceptance(
            tenant_id=test_contact.tenant_id,
            quote_version_id=version2.id,  # Different version
            contact_id=test_contact.id,
            accepted_by_name="John Doe",
            accepted_by_email="john@test.com",
            created_by=test_user.id,
        )
        db_session.add_all([acceptance1, acceptance2])
        db_session.commit()

        result = db_session.exec(
            select(QuoteAcceptance).where(QuoteAcceptance.contact_id == test_contact.id)
        ).all()
        assert len(result) == 2

    def test_different_contacts_same_version_allowed(
        self,
        db_session,
        test_tenant,
        test_customer,
        test_contact,
        test_quote_version,
        test_user,
    ):
        """Different contacts can accept same quote version (multi-signer scenario)."""
        # Create second contact
        contact2 = Contact(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            first_name="Jane",
            last_name="Doe",
            created_by=test_user.id,
        )
        db_session.add(contact2)
        db_session.commit()

        # Both contacts accept
        acceptance1 = QuoteAcceptance(
            tenant_id=test_contact.tenant_id,
            quote_version_id=test_quote_version.id,
            contact_id=test_contact.id,
            accepted_by_name="John Doe",
            accepted_by_email="john@test.com",
            created_by=test_user.id,
        )
        acceptance2 = QuoteAcceptance(
            tenant_id=test_contact.tenant_id,
            quote_version_id=test_quote_version.id,
            contact_id=contact2.id,  # Different contact
            accepted_by_name="Jane Doe",
            accepted_by_email="jane@test.com",
            created_by=test_user.id,
        )
        db_session.add_all([acceptance1, acceptance2])
        db_session.commit()

        result = db_session.exec(
            select(QuoteAcceptance).where(
                QuoteAcceptance.quote_version_id == test_quote_version.id
            )
        ).all()
        assert len(result) == 2
