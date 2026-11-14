import os
import sys
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, select

# Ensure backend is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from core.db import get_db

# ==================== DOMAIN MARKER AUTO-TAGGING ====================
# Maps legacy batch/phase folder names to domain markers so existing tests
# can be filtered by domain without moving any files.
# New tests go in tests/domains/<domain>/ and declare pytestmark directly.
# See: tests/README-adding-tests.md
# Maps root-level test file basenames (no directory prefix) to domain markers.
# These files live directly in tests/ and are not inside a batch_* or phase_*
# folder so they don't get picked up by _FOLDER_TO_DOMAIN_MARKER.
_FILE_TO_DOMAIN_MARKER: dict[str, str] = {
    "test_addresses.py": "domain_crm",
    "test_audit_logging.py": "domain_audit_compliance",
    "test_audit_trigger_coverage.py": "domain_audit_compliance",
    "test_auth.py": "domain_identity_access",
    "test_celery.py": "domain_platform_infrastructure",
    "test_check_constraints_task2.py": "domain_platform_infrastructure",
    "test_check_constraints_task9.py": "domain_platform_infrastructure",
    "test_citext_email.py": "domain_identity_access",
    "test_conflict_detection.py": "domain_scheduling_dispatch",
    "test_contacts.py": "domain_crm",
    "test_database_triggers.py": "domain_audit_compliance",
    "test_discount_version_task1.py": "domain_catalog_pricing",
    "test_idempotency.py": "domain_platform_infrastructure",
    "test_multi_tenancy_isolation.py": "domain_identity_access",
    "test_notification_outbox.py": "domain_notifications_comms",
    "test_partial_indexes_task11.py": "domain_platform_infrastructure",
    "test_partial_unique_indexes_task12.py": "domain_platform_infrastructure",
    "test_phase2.py": "domain_platform_infrastructure",
    "test_plpgsql_functions.py": "domain_audit_compliance",
    "test_profitability_rollup.py": "domain_platform_infrastructure",
    "test_qb_identity_constraints.py": "domain_quickbooks",
    "test_quickbooks_oauth.py": "domain_quickbooks",
    "test_quickbooks_sync.py": "domain_quickbooks",
    "test_quote_acceptance.py": "domain_sales_quoting",
    "test_quote_acceptance_varchar_alignment_task10.py": "domain_sales_quoting",
    "test_quotes.py": "domain_sales_quoting",
    "test_rate_limiting.py": "domain_platform_infrastructure",
    "test_rbac_permissions.py": "domain_identity_access",
    "test_request_id.py": "domain_platform_infrastructure",
    "test_schema_sync_v2_6h.py": "domain_platform_infrastructure",
    "test_session_cleanup.py": "domain_voice_ai",
    "test_tax_calculation.py": "domain_tax_calculation",
    "test_temporal_exclusion_constraints_task10.py": "domain_scheduling_dispatch",
    "test_test_endpoints.py": "domain_platform_infrastructure",
    "test_timezone_compliance.py": "domain_platform_infrastructure",
    "test_unique_constraints_task8.py": "domain_platform_infrastructure",
    "test_vector_indexes_task13.py": "domain_voice_ai",
    "test_voice.py": "domain_voice_ai",
    "test_voice_actions.py": "domain_voice_ai",
    "test_webhook_handler.py": "domain_platform_infrastructure",
}


_FOLDER_TO_DOMAIN_MARKER: dict[str, str] = {
    # --- Security / RBAC / IDOR ---
    "batch_1a": "domain_catalog_pricing",
    "batch_1b": "domain_audit_compliance",
    # --- Schema sync: column/constraint additions ---
    "batch_1c": "domain_platform_infrastructure",
    # --- Quote/Job/Invoice workflow ---
    "batch_1d": "domain_sales_quoting",
    # --- Scheduling & Dispatch ---
    "batch_1e": "domain_scheduling_dispatch",
    # --- Sales & Quoting ---
    "batch_b1": "domain_sales_quoting",
    # --- Voice AI ---
    "batch_b2": "domain_voice_ai",
    # --- Profitability / Settings / Dispatch ---
    "batch_b3": "domain_scheduling_dispatch",
    # --- Customer Communications ---
    "batch_b4": "domain_notifications_comms",
    # --- Dashboard & Reports ---
    "batch_b5": "domain_platform_infrastructure",
    # --- Calendar conflicts / auto-expiry / voice ---
    "batch_b6": "domain_scheduling_dispatch",
    # --- Mobile offline: capture & sync queue ---
    "batch_b7a": "domain_mobile_offline",
    # --- Mobile offline: conflict classification & recovery ---
    "batch_b7b": "domain_mobile_offline",
    # --- Escalation, QB Conflicts, Mobile Push ---
    "batch_b8": "domain_quickbooks",
    # --- Platform settings infrastructure ---
    "batch_b9": "domain_platform_infrastructure",
    # --- Notification preference center ---
    "batch_b10": "domain_notifications_comms",
    # --- SMS / Telnyx ---
    "batch_b11": "domain_notifications_comms",
    # --- ORM / Migration / Settings Resolver ---
    "batch_b12": "domain_platform_infrastructure",
    # --- MFA & Account Security ---
    "batch_b13": "domain_identity_access",
    # --- Audit Mixin Remediation ---
    "batch_b13b": "domain_audit_compliance",
    # --- Onboarding & Subscription ---
    "batch_b14": "domain_subscriptions_usage",
    # --- Public Links, Stripe, Email Templates ---
    "batch_b15": "domain_invoicing_billing",
    # --- Help & Support AI ---
    "batch_b16": "domain_help_support",
    # --- FIND Traceability Remediations (mixed domains; tag as platform) ---
    "batch_b17": "domain_platform_infrastructure",
    "batch_b18": "domain_platform_infrastructure",
    "batch_b19": "domain_platform_infrastructure",
    # --- Feature Completions: LOTO, Markup, Labor, Invoice, Voice ---
    "batch_b20": "domain_field_operations",
    # --- B21: Telnyx rewrite, receipt OCR ---
    "batch_b21": "domain_notifications_comms",
    # --- Marketing Endpoints ---
    "batch_mkt_b1": "domain_platform_infrastructure",
    "batch_mkt_b1_5": "domain_platform_infrastructure",
    # --- Test Plan Regression Batches ---
    "batch_tp_b1": "domain_invoicing_billing",
    "batch_tp_b2": "domain_sales_quoting",
    "batch_tp_b3": "domain_sales_quoting",
    "batch_tp_b4": "domain_sales_quoting",
    "batch_tp_b5": "domain_catalog_pricing",
    "batch_tp_b6": "domain_field_operations",
    "batch_tp_b7": "domain_notifications_comms",
    "batch_tp_b8": "domain_identity_access",
    "batch_tp_b9": "domain_platform_infrastructure",
    "batch_tp_b10": "domain_platform_infrastructure",
    "batch_tp_b11": "domain_help_support",
    # --- Phase-based schema sync batches ---
    "phase_4": "domain_platform_infrastructure",
    "phase_5": "domain_platform_infrastructure",
    "phase_6": "domain_audit_compliance",
    "phase_7": "domain_identity_access",
    "phase_9": "domain_audit_compliance",
    # --- Integration / E2E ---
    "integration": "domain_platform_infrastructure",
}


def pytest_addoption(parser) -> None:
    """
    Add --e2e CLI flag so E2E tests are excluded from the default run.

    Without --e2e: E2E tests are skipped (added to skip list).
    With --e2e:    E2E tests run (against pilot_e2e_db).

    Usage:
        pytest tests/e2e/ --e2e          # Run E2E tests only
        pytest -m unit                   # Unit tests only (e2e auto-excluded via marker)
        pytest                           # All tests EXCEPT e2e (e2e skipped by default)
    """
    parser.addoption(
        "--e2e",
        action="store_true",
        default=False,
        help="Run E2E tests (requires pilot_e2e_db on port 5433 to be running and seeded)",
    )


def pytest_collection_modifyitems(config, items: list) -> None:
    """
    Auto-apply domain markers to tests in legacy batch/phase folders.

    Tests in tests/domains/<domain>/ declare their own pytestmark directly
    and are NOT affected by the domain auto-tagging (their folder name won't
    match any key in _FOLDER_TO_DOMAIN_MARKER).

    This hook enforces two marker rules:

    1. INTEGRATION NORMALISATION: Any test marked e2e, requires_sendgrid,
       requires_telnyx, or requires_twilio automatically receives the
       integration marker as well. This ensures -m "not integration"
       reliably excludes ALL external-service tests, even if a test author
       forgot to add the integration marker explicitly.

    2. UNIT AUTO-TAGGING: Any test with no integration-family marker
       receives pytest.mark.unit so that -m unit runs the full
       non-integration suite without needing to enumerate every marker.
    """
    # SD-10: Skip E2E tests by default unless --e2e is passed.
    # This keeps `pytest -m unit` and bare `pytest` fast and free of E2E dependencies.
    run_e2e = config.getoption("--e2e", default=False)
    if not run_e2e:
        skip_e2e = pytest.mark.skip(
            reason="E2E tests skipped by default — pass --e2e to run (requires pilot_e2e_db)"
        )
        for item in items:
            if "e2e" in item.nodeid:
                item.add_marker(skip_e2e)

    # Markers that imply external service usage — any of these alone = integration.
    # requires_db is included because it signals tests that bypass the rollback
    # fixture and need a persistent live DB connection (integration-level behavior).
    implies_integration = {
        "e2e",
        "requires_sendgrid",
        "requires_telnyx",
        # requires_twilio removed — Twilio deleted in DLC-B2; Pathway B uses Telnyx
        "requires_db",
        # Real AI container tests — excluded from fast unit run just like
        # external service tests. The autouse mock_ai_services fixture is
        # skipped for these; they actually hit Ollama/Whisper containers.
        "requires_ollama",
        "requires_whisper",
        # C-B14 — Stripe test-clock scenarios (real Stripe test-mode API calls)
        "requires_stripe",
    }
    # Full set used to decide whether to add the unit marker
    integration_family = {"integration"} | implies_integration

    for item in items:
        folder = item.fspath.dirpath().basename
        domain_marker_name = _FOLDER_TO_DOMAIN_MARKER.get(folder)

        # Handle root-level tests/test_*.py files — look up by filename.
        if domain_marker_name is None and folder == "tests":
            domain_marker_name = _FILE_TO_DOMAIN_MARKER.get(item.fspath.basename)

        # Handle tests/domains/<domain>/ — folder name IS the domain slug.
        # These files declare pytestmark themselves; we just ensure the marker
        # name is in the known set before adding it again (no-op if already set).
        if (
            domain_marker_name is None
            and not folder.startswith("batch")
            and not folder.startswith("phase")
            and folder != "tests"
        ):
            candidate = f"domain_{folder}"
            if candidate in {
                "domain_audit_compliance",
                "domain_catalog_pricing",
                "domain_crm",
                "domain_field_operations",
                "domain_identity_access",
                "domain_invoicing_billing",
                "domain_notifications_comms",
                "domain_platform_infrastructure",
                "domain_quickbooks",
                "domain_sales_quoting",
                "domain_subscriptions_usage",
                "domain_tax_calculation",
                "domain_voice_ai",
                "domain_scheduling_dispatch",
                "domain_mobile_offline",
                "domain_help_support",
            }:
                domain_marker_name = candidate

        if domain_marker_name:
            item.add_marker(getattr(pytest.mark, domain_marker_name))

        existing_marker_names = {m.name for m in item.iter_markers()}

        # Rule 1: Normalise — add integration to any test that implies it
        # but is missing the integration marker (e.g. marked e2e or
        # requires_sendgrid alone). This makes -m "not integration" reliable.
        if (
            existing_marker_names & implies_integration
            and "integration" not in existing_marker_names
        ):
            item.add_marker(pytest.mark.integration)
            existing_marker_names.add("integration")

        # Rule 2: Add unit marker to all tests with no integration-family marker.
        if not existing_marker_names & integration_family:
            item.add_marker(pytest.mark.unit)


def _get_trial_tier_id(session):
    """
    Return the trial tier's tier_id for use in test Tenant() factories.
    B14/A75: current_subscription_tier_id is NOT NULL on tenant table.
    All test fixtures that create Tenant rows must supply this field.
    """
    from app.models.subscription import SubscriptionTier

    tier = session.exec(
        select(SubscriptionTier).where(SubscriptionTier.is_trial == True)
    ).first()
    if tier is None:
        raise RuntimeError(
            "Trial subscription tier not seeded. Run: alembic upgrade head"
        )
    return tier.tier_id


# We can use a test database or the dev database in a transaction
# Assuming dev db is running for tests. Best practice: use a separate test db.
# For simplicity and isolation, we will just use the dev db and rollback, or an sqlite in-memory db.
# However, the app uses postgres-specific fields (JSONB, CITEXT, INET).
# So we MUST use a postgres database. We'll use the default one and rollback.
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://pilot_user:CHANGE_ME_LOCAL_DB_PW@localhost:5432/pilot_dev"
)
engine = create_engine(DATABASE_URL)


@pytest.fixture(scope="session")
def db_engine():
    # Setup step: Create all tables (if not already created by alembic in dev db)
    # SQLModel.metadata.create_all(engine)
    yield engine
    # Teardown step
    # SQLModel.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    connection = db_engine.connect()
    # Begin a non-ORM transaction
    transaction = connection.begin()

    # Bind an individual Session to the connection
    session = Session(bind=connection)
    yield session

    session.close()
    # Rollback the overall transaction, restoring the state before the test ran.
    # FIX: Only rollback if transaction is still active (prevents SAWarning when tests manually rollback)
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def mock_cognito_jwks():
    with patch("core.auth.get_jwks") as mock_jwks:
        mock_jwks.return_value = {
            "keys": [
                {
                    "alg": "RS256",
                    "e": "AQAB",
                    "kid": "test_kid",
                    "kty": "RSA",
                    "n": "test_n",
                    "use": "sig",
                }
            ]
        }
        yield mock_jwks


@pytest.fixture(autouse=True)
def mock_ai_services(request):
    """
    Autouse fixture: intercept all Ollama and Whisper HTTP calls in every test.

    Without this, any code path that reaches ai_service.generate_text_sync,
    transcribe_audio, parse_intent, or get_embedding will attempt real HTTP
    connections to the Ollama/Whisper containers with a 60-second timeout,
    making the test suite take 3500+ seconds when those containers are running.

    This fixture patches at the service layer (not the route layer) so that:
    - Tests which explicitly patch at the route layer (e.g. api.routes.voice.*)
      are unaffected — the route-layer patch shadows this one.
    - Tests that call service functions directly also get a safe mock.

    NOTE: transcribe_audio, parse_intent, and get_embedding are async functions
    and must be patched with AsyncMock. generate_text_sync is synchronous.

    To opt out and test against the real containers, mark the test with:
        @pytest.mark.requires_ollama   — skips Ollama mocks
        @pytest.mark.requires_whisper  — skips Whisper mocks

    Marker meanings:
        requires_ollama  → test intentionally calls the real LLM container
        requires_whisper → test intentionally calls the real Whisper container
    """
    from unittest.mock import AsyncMock

    skip_ollama = request.node.get_closest_marker("requires_ollama") is not None
    skip_whisper = request.node.get_closest_marker("requires_whisper") is not None

    patches = []

    if not skip_ollama:
        patches.extend(
            [
                # async def parse_intent(...) — must use AsyncMock
                patch(
                    "services.ai_service.parse_intent",
                    new_callable=AsyncMock,
                    return_value='{"intent": "unknown", "entities": {}}',
                ),
                # async def get_embedding(...) — must use AsyncMock
                patch(
                    "services.ai_service.get_embedding",
                    new_callable=AsyncMock,
                    return_value=[0.0] * 1024,
                ),
                # sync def generate_text_sync(...)
                patch(
                    "services.ai_service.generate_text_sync",
                    return_value="Mock AI response",
                ),
                # voice_action_router._apply_tone_aware_message() calls
                # voice_persona_renderer.render() which calls _call_ollama →
                # generate_text_sync. The autouse mock returns "Mock AI response"
                # (a non-empty string), so render() passes it back and
                # _apply_tone_aware_message overwrites action_result["message"].
                # This breaks voice action tests that assert on message content
                # (e.g. "customer", "quote", "coming soon").
                #
                # Fix: patch _apply_tone_aware_message to be a pass-through
                # (returns the result dict unmodified). This is the right scope:
                # - Voice action router tests see original handler messages ✓
                # - voice_persona_renderer tests test render() directly ✓
                # - voice_session_title tests use generate_session_title(), not
                #   _apply_tone_aware_message, so they are also unaffected ✓
                patch(
                    "services.voice_action_router._apply_tone_aware_message",
                    side_effect=lambda result, *args, **kwargs: result,
                ),
            ]
        )

    if not skip_whisper:
        patches.append(
            # async def transcribe_audio(...) — must use AsyncMock
            patch(
                "services.ai_service.transcribe_audio",
                new_callable=AsyncMock,
                return_value="mock transcription",
            )
        )

    started = [p.start() for p in patches]
    yield started
    for p in patches:
        p.stop()


@pytest.fixture(autouse=True)
def mock_entitlement_allowed(request):
    """
    Autouse fixture: bypass entitlement subscription checks in all tests.

    PLP-FIX-1 (2026-08-30): the quotes endpoint no longer carries a feature
    entitlement gate (quotes are unlimited on every plan per PRD §3.11; the
    ``quotes_per_month`` wiring was a phantom gate, removed). This autouse
    fixture remains for any future gated-endpoint tests (e.g. ``schedule_lanes``
    on the dispatch board) and for tests that don't seed an active subscription
    but hit endpoints whose RBAC path still consults the entitlement service.

    This fixture patches get_cached_entitlement to return is_allowed=True
    globally so non-entitlement tests are not affected by subscription state.
    Tests that specifically exercise entitlement behaviour can override this
    by re-patching or using a direct DB-level override via TenantProductFeatureOverride.

    To skip this fixture, mark the test with @pytest.mark.skip_mock_entitlement_allowed
    """
    # Check if the test has the skip marker
    if request.node.get_closest_marker("skip_mock_entitlement_allowed"):
        yield
        return

    from services.entitlement_service import EntitlementResult

    with patch(
        "services.entitlement_service.get_cached_entitlement",
        return_value=EntitlementResult(is_allowed=True, reason="test_bypass"),
    ):
        yield


@pytest.fixture
def mock_cognito_jwt_verify():
    with (
        patch("core.auth.verify_cognito_jwt") as mock_verify_core,
        patch("api.routes.auth.verify_cognito_jwt") as mock_verify_api,
    ):
        mock_verify_core.return_value = {
            "sub": "00000000-0000-0000-0000-000000000002",
            "email": "dev@pilot.local",
        }
        mock_verify_api.return_value = {
            "sub": "00000000-0000-0000-0000-000000000002",
            "email": "dev@pilot.local",
        }
        yield mock_verify_core


# ==================== DATETIME TIMEZONE-AWARE FIXTURES ====================
# These fixtures provide timezone-aware datetimes for tests


@pytest.fixture
def utc_now():
    """
    Provides a timezone-aware UTC datetime for tests.

    Usage:
        def test_user_creation(db_session, utc_now):
            user = User(
                email="test@example.com",
                created_at=utc_now,
                updated_at=utc_now
            )
    """
    return datetime.now(UTC)


@pytest.fixture
def aware_datetime():
    """
    Factory fixture for creating timezone-aware datetimes in tests.

    Usage:
        def test_token_expiry(aware_datetime):
            expires_at = aware_datetime(2026, 12, 31, 23, 59, 59)
            assert token.expires_at < expires_at
    """

    def _make_aware(year, month, day, hour=0, minute=0, second=0):
        return datetime(year, month, day, hour, minute, second, tzinfo=UTC)

    return _make_aware


# ==================== MULTI-TENANCY ISOLATION FIXTURES ====================
# These fixtures support cross-tenant security testing (Gap #38)


@pytest.fixture
def tenant_a(db_session):
    """Create test tenant A for multi-tenancy isolation tests"""
    import uuid

    from app.models.core import Tenant

    tenant = Tenant(
        id=uuid.uuid4(),
        name=f"Test Tenant A {uuid.uuid4()}",
        is_active=True,
        current_subscription_tier_id=_get_trial_tier_id(db_session),
    )
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


@pytest.fixture
def tenant_b(db_session):
    """Create test tenant B (isolated from A) for multi-tenancy isolation tests"""
    import uuid

    from app.models.core import Tenant

    tenant = Tenant(
        id=uuid.uuid4(),
        name=f"Test Tenant B {uuid.uuid4()}",
        is_active=True,
        current_subscription_tier_id=_get_trial_tier_id(db_session),
    )
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


@pytest.fixture
def user_tenant_a(db_session, tenant_a):
    """User belonging to Tenant A for multi-tenancy isolation tests"""
    import uuid

    from app.models.auth import TenantUser, TenantUserStatus
    from app.models.core import User

    # Create a tenant user status for this test
    status = TenantUserStatus(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        code="active",
        name="Active",
        is_default=True,
        is_active=True,
    )
    db_session.add(status)
    db_session.flush()

    user = User(
        id=uuid.uuid4(),
        email=f"user-a-{uuid.uuid4()}@example.com",
        first_name="User",
        last_name="A",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    # Link to tenant A
    tenant_user = TenantUser(
        tenant_id=tenant_a.id,
        user_id=user.id,
        role_code="owner",
        status_id=status.id,
        is_active=True,
    )
    db_session.add(tenant_user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def user_tenant_b(db_session, tenant_b):
    """User belonging to Tenant B for multi-tenancy isolation tests"""
    import uuid

    from app.models.auth import TenantUser, TenantUserStatus
    from app.models.core import User

    # Create a tenant user status for this test
    status = TenantUserStatus(
        id=uuid.uuid4(),
        tenant_id=tenant_b.id,
        code="active",
        name="Active",
        is_default=True,
        is_active=True,
    )
    db_session.add(status)
    db_session.flush()

    user = User(
        id=uuid.uuid4(),
        email=f"user-b-{uuid.uuid4()}@example.com",
        first_name="User",
        last_name="B",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    # Link to tenant B
    tenant_user = TenantUser(
        tenant_id=tenant_b.id,
        user_id=user.id,
        role_code="owner",
        status_id=status.id,
        is_active=True,
    )
    db_session.add(tenant_user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def mock_jwt_for_user(mock_cognito_jwt_verify):
    """
    Helper to mock JWT for specific user email.

    Usage:
        token = mock_jwt_for_user(user.email)
        headers = {"Authorization": token}
        response = client.get("/api/v1/customers", headers=headers)
    """
    import uuid

    def _mock_for_email(email: str):
        mock_cognito_jwt_verify.return_value = {
            "sub": str(uuid.uuid4()),
            "email": email,
        }
        return f"Bearer mock_token_{uuid.uuid4()}"

    return _mock_for_email


# ==================== POLYMORPHIC RELATIONSHIPS TEST FIXTURES ====================
# These fixtures support Contact and Address polymorphic relationship tests (Gap #6, #7, #8)


@pytest.fixture
def test_tenant(db_session):
    """
    Get or create the standard test tenant for unauthenticated test endpoints.

    This fixture returns the seeded test tenant with ID:
    00000000-0000-0000-0000-000000000001

    Also ensures a TenantSettings row exists for the tenant so tests that
    query tenant_settings (e.g. test_a44 offline-hard-limit tests) do not
    self-skip with "test_tenant has no tenant_settings row".

    NOTE: tenant_settings is inserted via raw SQL to bypass the audit trigger
    (audit.log_changes references NEW.id which doesn't exist on this table —
    its PK is tenant_id, not id).

    Used by test endpoints that rely on get_test_context().
    """
    import uuid

    from app.models.core import Tenant

    test_tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    tenant = db_session.get(Tenant, test_tenant_id)
    if not tenant:
        # Create if doesn't exist (should be seeded though)
        tenant = Tenant(
            id=test_tenant_id,
            name="[TEST] Pilot for Trades Test Tenant",
            is_active=True,
            current_subscription_tier_id=_get_trial_tier_id(db_session),
        )
        db_session.add(tenant)
        db_session.commit()
        db_session.refresh(tenant)

    # FIND-086: tenant_settings table is dropped. Platform defaults are now in
    # platform_setting (NULL tenant_id rows seeded by the migration). No per-tenant
    # row is needed for the test tenant — NULL rows provide all defaults automatically.

    return tenant


@pytest.fixture
def test_user(db_session, test_tenant):
    """
    Get or create the standard test user for unauthenticated test endpoints.

    This fixture returns a test user belonging to the test tenant.
    Used by tests that need a basic user context.

    NOTE: Also creates a primary email endpoint for the user to satisfy
    database triggers that sync user.email from user_endpoint.
    """
    import uuid

    from app.models.core import User, UserEndpoint

    test_user_id = uuid.UUID("00000000-0000-0000-0000-000000000002")

    user = db_session.get(User, test_user_id)
    if not user:
        # Create if doesn't exist
        user = User(
            id=test_user_id,
            email="dev@pilot.local",
            first_name="Dev",
            last_name="Owner",
            is_active=True,
        )
        db_session.add(user)
        db_session.flush()

        # Create a primary email endpoint to keep triggers happy
        # This prevents sync_user_email_from_endpoint_fn from setting email to NULL
        endpoint = UserEndpoint(
            user_id=user.id,
            channel="email",
            value="dev@pilot.local",
            is_primary=True,
            verification_status="verified",
            consent_status="opted_in",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db_session.add(endpoint)
        db_session.commit()
        db_session.refresh(user)

    return user


@pytest.fixture
def second_tenant(db_session):
    """
    Create a second test tenant for cross-tenant isolation tests.

    Used to verify that users cannot access data from other tenants.
    """
    import uuid

    from app.models.core import Tenant

    tenant = Tenant(
        id=uuid.uuid4(),
        name=f"[TEST] Second Tenant {uuid.uuid4()}",
        is_active=True,
        current_subscription_tier_id=_get_trial_tier_id(db_session),
    )
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


# ==================== RBAC TEST FIXTURES ====================
# These fixtures support RBAC permission tests


@pytest.fixture
def mock_cognito_jwt(mock_cognito_jwt_verify, client):
    """
    Callable fixture to mock JWT authentication for a specific user.

    Usage:
        mock_cognito_jwt(owner_user)
        response = client.post("/api/v1/quotes", ...)

    This sets up the mock AND injects a default Authorization header into the test client.
    """
    import uuid

    def _mock_jwt(user):
        # Mock the JWT verification
        mock_cognito_jwt_verify.return_value = {
            "sub": user.cognito_user_id
            if hasattr(user, "cognito_user_id")
            else str(user.id),
            "email": user.email,
        }

        # Set default headers on the client so all requests include auth
        token = f"Bearer mock_token_{uuid.uuid4()}"
        if not hasattr(client, "_original_request"):
            client._original_request = client.request

        def authenticated_request(*args, **kwargs):
            if "headers" not in kwargs or kwargs["headers"] is None:
                kwargs["headers"] = {}
            if "Authorization" not in kwargs["headers"]:
                kwargs["headers"]["Authorization"] = token
            return client._original_request(*args, **kwargs)

        client.request = authenticated_request
        return token

    return _mock_jwt


@pytest.fixture
def test_customer(db_session, test_tenant):
    """
    Create a test customer for schema sync tests.

    Returns a Customer instance belonging to test_tenant.
    """
    import uuid

    from app.models.crm import Customer, CustomerType

    customer = Customer(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        display_name=f"Test Customer {uuid.uuid4()}",
        type=CustomerType.person,
        is_active=True,
    )
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)
    return customer


@pytest.fixture
def test_site(db_session, test_tenant, test_customer):
    """
    Create a test site for schema sync tests.

    Returns a Site instance belonging to test_tenant and test_customer.
    """
    import uuid

    from app.models.crm import Site

    site = Site(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        customer_id=test_customer.id,
        site_name="Test Site",
        is_active=True,
    )
    db_session.add(site)
    db_session.commit()
    db_session.refresh(site)
    return site


@pytest.fixture
def test_job(db_session, tenant_a, test_customer, test_site):
    """
    Create a test job for RBAC permission tests.

    Returns a Job instance belonging to tenant_a.
    """
    import uuid

    # Get a job status (we need this for FK constraint)
    from app.models.fulfillment import Job, JobStatus

    job_status = db_session.exec(
        select(JobStatus).where(JobStatus.code == "draft")
    ).first()

    if not job_status:
        job_status = JobStatus(
            id=uuid.uuid4(),
            code="draft",
            name="Draft",
            description="Job is in draft status",
            is_active=True,
        )
        db_session.add(job_status)
        db_session.flush()

    job = Job(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        customer_id=test_customer.id,
        site_id=test_site.id,
        status_id=job_status.id,
        job_number=f"JOB-{uuid.uuid4().hex[:8].upper()}",
        is_active=True,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


# ==================== SCHEMA SYNC V2.6H TEST FIXTURES ====================
# These fixtures support Golden Master schema synchronization tests


@pytest.fixture
def test_contact(db_session, test_tenant, test_customer):
    """
    Create a test contact for schema sync tests.

    Returns a Contact instance.
    """
    import uuid

    from app.models.crm import Contact

    contact = Contact(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        customer_id=test_customer.id,
        email=f"contact-{uuid.uuid4()}@example.com",
        first_name="Test",
        last_name="Contact",
        is_active=True,
    )
    db_session.add(contact)
    db_session.commit()
    db_session.refresh(contact)
    return contact


@pytest.fixture
def test_quote_status(db_session, test_tenant):
    """
    Create a test quote status for schema sync tests.

    Returns a QuoteStatus instance.
    """
    import uuid

    from app.models.quoting import QuoteStatus

    status = QuoteStatus(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        code="draft",
        name="Draft",
        is_default=True,
        is_active=True,
    )
    db_session.add(status)
    db_session.commit()
    db_session.refresh(status)
    return status


@pytest.fixture
def test_invoice_status(db_session, test_tenant):
    """
    Create a test invoice status for schema sync tests.

    Returns an InvoiceStatus instance.
    """
    import uuid

    from app.models.billing import InvoiceStatus

    status = InvoiceStatus(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        code="draft",
        name="Draft",
        is_default=True,
        is_active=True,
    )
    db_session.add(status)
    db_session.commit()
    db_session.refresh(status)
    return status


@pytest.fixture
def test_notification_outbox(db_session, test_tenant, test_user):
    """
    Create a test notification outbox entry for schema sync tests.

    Returns a NotificationOutbox instance.
    """
    import uuid
    from datetime import UTC, datetime

    from app.models.core import EntityType
    from app.models.system import (
        NotificationEvent,
        NotificationOutbox,
        NotificationType,
    )

    # Ensure entity_type "user" exists
    entity_type = db_session.exec(
        select(EntityType).where(EntityType.code == "user")
    ).first()
    if not entity_type:
        entity_type = EntityType(
            code="user",
            name="User",
            is_active=True,
        )
        db_session.add(entity_type)
        db_session.flush()

    # Ensure entity_type "invoice" exists
    invoice_entity_type = db_session.exec(
        select(EntityType).where(EntityType.code == "invoice")
    ).first()
    if not invoice_entity_type:
        invoice_entity_type = EntityType(
            code="invoice",
            name="Invoice",
            is_active=True,
        )
        db_session.add(invoice_entity_type)
        db_session.flush()

    # Ensure notification_type "test_notification" exists
    notif_type = db_session.exec(
        select(NotificationType).where(NotificationType.code == "test_notification")
    ).first()
    if not notif_type:
        notif_type = NotificationType(
            code="test_notification",
            audience="tenant",  # Required field
            name="Test Notification",
            description="Test notification for fixtures",
            is_active=True,
        )
        db_session.add(notif_type)
        db_session.flush()

    # Ensure notification_type "dunning_reminder" exists
    dunning_type = db_session.exec(
        select(NotificationType).where(NotificationType.code == "dunning_reminder")
    ).first()
    if not dunning_type:
        dunning_type = NotificationType(
            code="dunning_reminder",
            audience="tenant",  # Required field
            name="Dunning Reminder",
            description="Overdue invoice reminder notification",
            is_active=True,
        )
        db_session.add(dunning_type)
        db_session.flush()

    # Create a notification event first (required FK)
    notification_event = NotificationEvent(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        notification_type_code="test_notification",
        entity_type_code="user",
        entity_id=str(test_user.id),
        occurred_at=datetime.now(UTC),
    )
    db_session.add(notification_event)
    db_session.flush()

    notification = NotificationOutbox(
        id=uuid.uuid4(),
        notification_event_id=notification_event.id,  # Required FK
        tenant_id=test_tenant.id,
        recipient_user_id=test_user.id,
        channel="email",
        subject="Test Notification",
        body="Test body",
        status="pending",
        category_id="system_announcements",  # B10/A56: required NOT NULL
    )
    db_session.add(notification)
    db_session.commit()
    db_session.refresh(notification)
    return notification


@pytest.fixture
def test_quote_version(
    db_session, test_tenant, test_customer, test_site, test_quote_status
):
    """
    Create a test quote version for schema sync tests.

    Returns a QuoteVersion instance with parent Quote.
    """
    import uuid
    from datetime import UTC, datetime

    from app.models.quoting import Quote, QuoteVersion

    # Create parent quote
    quote = Quote(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        customer_id=test_customer.id,
        site_id=test_site.id,
        status_id=test_quote_status.id,
        currency="USD",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(quote)
    db_session.commit()
    db_session.refresh(quote)

    # Create quote version
    version = QuoteVersion(
        tenant_id=test_tenant.id,
        id=uuid.uuid4(),
        quote_id=quote.id,
        version_no=1,
        snapshot={},  # Required JSONB field
        subtotal_cents=0,
        tax_cents=0,
        total_cents=0,
        created_at=datetime.now(UTC),
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(version)
    return version


@pytest.fixture
def test_qco_line_type(db_session, test_tenant):
    """
    Create a test QCO line type for schema sync tests.

    Returns a QcoLineType instance.
    """
    import uuid

    from app.models.quoting import QcoLineType

    line_type = QcoLineType(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        code="material",
        name="Material",
        is_default=True,
        is_active=True,
    )
    db_session.add(line_type)
    db_session.commit()
    db_session.refresh(line_type)
    return line_type


@pytest.fixture
def test_notification_event(db_session, test_tenant):
    """Create a test notification event."""
    import uuid

    from app.models.system import NotificationEvent, NotificationType

    # Create notification type if it doesn't exist
    notif_type = db_session.exec(
        select(NotificationType).where(NotificationType.code == "quote_ready")
    ).first()
    if not notif_type:
        notif_type = NotificationType(
            code="quote_ready",
            name="Quote Ready",
            audience="tenant",
            is_active=True,
        )
        db_session.add(notif_type)
        db_session.commit()

    event = NotificationEvent(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        notification_type_code="quote_ready",
        entity_type_code="quote",
        entity_id="test-entity-123",
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)
    return event


@pytest.fixture
def test_webhook_endpoint(db_session, test_tenant):
    """Create a test webhook endpoint."""
    import uuid

    from app.models.system import WebhookEndpoint

    endpoint = WebhookEndpoint(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        url="https://example.com/webhook",
        is_active=True,
    )
    db_session.add(endpoint)
    db_session.commit()
    db_session.refresh(endpoint)
    return endpoint


@pytest.fixture
def test_webhook_event(db_session, test_tenant):
    """Create a test webhook event."""
    import uuid

    from app.models.system import WebhookEvent

    event = WebhookEvent(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        payload={"test": "data"},
        signature_valid=True,
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)
    return event


@pytest.fixture
def test_app_service(db_session, test_tenant):
    """Create a test app service."""
    import uuid

    from app.models.system import AppService

    service = AppService(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        name="Test QuickBooks",
        category_code="accounting",
        provider_code="quickbooks",
        is_active=True,
    )
    db_session.add(service)
    db_session.commit()
    db_session.refresh(service)
    return service


@pytest.fixture
def test_supplier(db_session, test_tenant):
    """Create a test supplier."""
    import uuid

    from app.models.catalog import Supplier

    supplier = Supplier(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        name="Test Supplier",
        is_active=True,
    )
    db_session.add(supplier)
    db_session.commit()
    db_session.refresh(supplier)
    return supplier


@pytest.fixture
def test_platform_role_staff(db_session):
    """Create staff platform role."""
    from app.models.core import PlatformRole

    role = db_session.exec(
        select(PlatformRole).where(PlatformRole.code == "staff")
    ).first()
    if not role:
        role = PlatformRole(
            code="staff",
            name="Staff",
            is_active=True,
        )
        db_session.add(role)
        db_session.commit()
        db_session.refresh(role)
    return role


@pytest.fixture
def test_platform_role_superadmin(db_session):
    """Create superadmin platform role."""
    from app.models.core import PlatformRole

    role = db_session.exec(
        select(PlatformRole).where(PlatformRole.code == "superadmin")
    ).first()
    if not role:
        role = PlatformRole(
            code="superadmin",
            name="Super Admin",
            is_active=True,
        )
        db_session.add(role)
        db_session.commit()
        db_session.refresh(role)
    return role
